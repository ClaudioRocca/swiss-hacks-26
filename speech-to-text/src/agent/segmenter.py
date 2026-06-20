"""Concept segmenter: the orchestrating agent.

Listens to finalized utterances as they stream in. After each one it asks a
cheap LLM whether the new utterance *continues the current concept* or *starts
a new one*. On a boundary it flushes the accumulated text as a ConceptChunk —
extracting structured semantics (topic, summary, intent, entities) — and emits
a trigger. This chunks an open-ended transcript by meaning, in real time.
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, field
from datetime import date
from typing import Awaitable, Callable, List, Optional

from openai import AsyncOpenAI

# Two LLM jobs, two models:
#   - boundary judge: runs PER UTTERANCE -> latency-sensitive -> small/fast model.
#   - extractor: runs PER CONCEPT -> quality-sensitive (intent, ticker mapping,
#     structured plan) -> a stronger model.
# AGENT_MODEL stays the back-compat knob for the extractor; each job can also be
# pinned independently via AGENT_JUDGE_MODEL / AGENT_EXTRACT_MODEL.
JUDGE_MODEL = os.getenv("AGENT_JUDGE_MODEL") or "gpt-4.1-mini"
EXTRACT_MODEL = (
    os.getenv("AGENT_EXTRACT_MODEL") or os.getenv("AGENT_MODEL") or "gpt-4.1"
)

# Spoken company name -> the ticker symbol actually stored in the data layer.
# The DB uses SIX Swiss Exchange tickers (UBSG, NOVN, ROG…), NOT the US/ADR or
# generic forms a model defaults to (UBS, NVS…). Inject this so the extractor
# grounds tickers in OUR data, not its priors.
TICKER_MAP = {
    "Nestlé": "NESN", "Nestle": "NESN",
    "Novartis": "NOVN",
    "Roche": "ROG",
    "UBS": "UBSG",
    "Credit Suisse": "CSGN",
    "Zurich Insurance": "ZURN", "Zurich Insurance Group": "ZURN",
    "Swiss Re": "SREN",
    "ABB": "ABBN",
    "Givaudan": "GIVN",
    "Apple": "AAPL",
    "Microsoft": "MSFT",
    "ASML": "ASML",
}
_TICKER_MAP_HINT = ", ".join(f"{k} -> {v}" for k, v in TICKER_MAP.items())


@dataclass
class DataRequest:
    """A planned (not executed) query against the data layer.

    `source` names a db.py table/collection; `filters` holds only the params
    relevant to that source (others are None). Downstream code runs these to
    build front-end widgets — the agent only emits the plan.
    """

    source: str
    rationale: str
    filters: dict = field(default_factory=dict)


@dataclass
class ConceptChunk:
    """A semantically-coherent slice of the transcript plus its retrieval plan."""

    text: str
    topic: str
    summary: str
    intent: str
    entities: List[str] = field(default_factory=list)
    data_requests: List[DataRequest] = field(default_factory=list)
    index: int = 0


TriggerCb = Callable[[ConceptChunk], Optional[Awaitable[None]]]


_JUDGE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "is_new_topic": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["is_new_topic", "reason"],
}

# Data sources = db.py query targets. Each maps to a function downstream.
DATA_SOURCES = [
    "portfolio",          # get_portfolio(ticker, sector, min/max_profit_loss)
    "trades",             # get_trades(ticker, operation_type, since, until, min_value)
    "customer_profile",   # get_customer_profile()  -- no filters
    "real_estate",        # get_real_estate(property_type, status, location, min/max_value)
    "market_movements",   # get_market_movements(ticker, min_change_percent, direction, since, sector)
    "news",               # search_news(query, top_k, category, ticker)
]

# Union of every filter param across all sources; the model fills only the ones
# relevant to each chosen source and leaves the rest null. All required+nullable
# to satisfy OpenAI strict structured outputs.
_STR = {"type": ["string", "null"]}
_NUM = {"type": ["number", "null"]}

# Explicit "return everything for this field" sentinel. Both ALL_VALUE and null
# mean no restriction; the sentinel lets the LLM state that intent first-class.
ALL_VALUE = "all"


def _nullable_enum(values: list[str], description: str) -> dict:
    """Nullable enum for strict structured outputs.

    Includes the ALL_VALUE sentinel and null — both mean 'no filter, return
    every row'. The model picks ALL_VALUE when the client wants all of them.
    """
    return {
        "type": ["string", "null"],
        "enum": [*values, ALL_VALUE, None],
        "description": f"{description}. Use '{ALL_VALUE}' (or null) to return every value.",
    }


# Enum values mirror db.py validation sets exactly — keep in sync with src/data/db.py.
_FILTERS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "ticker": {
            **_STR,
            "description": (
                "stock ticker symbol, e.g. NESN, AAPL. Use 'all' (or null) for every "
                "holding/ticker."
            ),
        },
        "sector": {
            **_STR,
            "description": "sector name. Use 'all' (or null) for every sector.",
        },
        "operation_type": _nullable_enum(
            ["buy", "sell", "short_sell", "short_cover"],
            "trades: type of trade operation",
        ),
        "direction": _nullable_enum(
            ["up", "down"], "market_movements: price move direction"
        ),
        "property_type": _nullable_enum(
            ["residential", "commercial", "industrial", "land"],
            "real_estate: property type",
        ),
        "status": _nullable_enum(
            ["active", "sold", "under_contract"], "real_estate: investment status"
        ),
        "location": {
            **_STR,
            "description": "property location. Use 'all' (or null) for every location.",
        },
        "category": _nullable_enum(
            ["macro", "equity", "geopolitical", "real_estate"],
            "news: article category",
        ),
        "min_profit_loss": _NUM,
        "max_profit_loss": _NUM,
        "min_value": _NUM,
        "max_value": _NUM,
        "min_change_percent": _NUM,
        "since": {**_STR, "description": "ISO date lower bound, YYYY-MM-DD"},
        "until": {**_STR, "description": "ISO date upper bound, YYYY-MM-DD"},
        "news_query": {**_STR, "description": "semantic search text for the news source"},
        "top_k": {"type": ["integer", "null"], "description": "news: number of results (1-20)"},
    },
    "required": [
        "ticker", "sector", "operation_type", "direction", "property_type",
        "status", "location", "category", "min_profit_loss", "max_profit_loss",
        "min_value", "max_value", "min_change_percent", "since", "until",
        "news_query", "top_k",
    ],
}

_DATA_REQUEST_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "source": {"type": "string", "enum": DATA_SOURCES},
        "rationale": {
            "type": "string",
            "description": "why this source answers the concept (one short phrase)",
        },
        "filters": _FILTERS_SCHEMA,
    },
    "required": ["source", "rationale", "filters"],
}

# ConceptCard: semantics + a retrieval plan over the data layer.
_EXTRACT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "is_relevant": {
            "type": "boolean",
            "description": (
                "true if this slice carries ANY substantive financial/banking concept "
                "or client request — investments, portfolio, trades, fraud, payments, "
                "standing orders, transfers, mortgages, accounts, real estate, market/"
                "news. This is independent of whether a data source applies: a valid "
                "request with NO matching data source is still relevant (data_requests "
                "may be empty). false ONLY for pure greetings/pleasantries or personal "
                "small talk (weather, sports, family chit-chat)."
            ),
        },
        "topic": {"type": "string", "description": "2-5 word concept label"},
        "summary": {"type": "string", "description": "one-sentence summary"},
        "intent": {"type": "string", "description": "what the client wants/means"},
        "entities": {"type": "array", "items": {"type": "string"}},
        "data_requests": {
            "type": "array",
            "description": (
                "retrieval plan: which data sources the relationship manager should "
                "pull to address this concept, with the filters to apply. Empty if "
                "the concept needs no data lookup. Map spoken references to real "
                "values (e.g. 'Nestle' -> ticker NESN)."
            ),
            "items": _DATA_REQUEST_SCHEMA,
        },
    },
    "required": ["is_relevant", "topic", "summary", "intent", "entities", "data_requests"],
}

# fixed seed + temperature 0 => near-reproducible judge/extract calls
DEFAULT_SEED = int(os.getenv("AGENT_SEED", "7"))


class ConceptSegmenter:
    def __init__(
        self,
        on_trigger: TriggerCb,
        *,
        judge_model: str = JUDGE_MODEL,
        extract_model: str = EXTRACT_MODEL,
        seed: int = DEFAULT_SEED,
        now: "date | None" = None,
    ):
        self.on_trigger = on_trigger
        self.judge_model = judge_model      # per-utterance boundary judge (fast)
        self.extract_model = extract_model  # per-concept extractor (strong)
        self.seed = seed
        # date the extractor resolves spoken/relative dates against (default today);
        # pin it in tests for reproducible since/until filters.
        self.today = (now or date.today()).isoformat()
        self.client = AsyncOpenAI()
        self._buffer: List[str] = []
        self._emitted = 0

    @property
    def current_text(self) -> str:
        return " ".join(self._buffer).strip()

    @property
    def recent_text(self) -> str:
        """The tail of the current concept — what the new utterance most likely
        continues or pivots from. Avoids a long buffer drowning a clear shift."""
        return " ".join(self._buffer[-2:]).strip()

    async def add_final(self, utterance: str) -> None:
        """Feed one finalized utterance. May emit a trigger for the prior concept."""
        utterance = utterance.strip()
        if not utterance:
            return

        if not self._buffer:
            self._buffer.append(utterance)
            return

        if await self._is_new_topic(self.current_text, self.recent_text, utterance):
            await self._flush()

        self._buffer.append(utterance)

    async def close(self) -> None:
        """Flush whatever concept is still buffered at end of stream."""
        await self._flush()

    async def _flush(self) -> None:
        text = self.current_text
        self._buffer = []
        if not text:
            return
        try:
            chunk, is_relevant = await self._extract(text)
        except Exception as e:
            # A flaky/truncated LLM extract must not kill a live audio stream;
            # drop this one concept and keep going. (Retried inside _extract.)
            import sys

            print(f"[segmenter] extract failed, concept dropped: {e}", file=sys.stderr)
            return
        if not is_relevant:
            return  # greeting/pleasantry or off-topic — no trigger
        chunk.index = self._emitted
        self._emitted += 1
        await _maybe_await(self.on_trigger(chunk))

    async def _is_new_topic(self, current: str, recent: str, candidate: str) -> bool:
        resp = await self.client.chat.completions.create(
            model=self.judge_model,
            temperature=0,
            seed=self.seed,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "boundary",
                    "strict": True,
                    "schema": _JUDGE_SCHEMA,
                },
            },
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are the assistant of a relationship manager in a private "
                        "bank. You segment a live transcript between a wealthy client and "
                        "their relationship manager into distinct concepts. Concepts that "
                        "matter are financial/banking work topics (transactions, fraud, "
                        "mortgages, payments, portfolio, accounts, real estate, news).\n"
                        "You receive the CONCEPT so far, its most RECENT lines, and the "
                        "NEXT utterance. Decide if NEXT starts a different concept.\n"
                        "Each distinct client request, question, or instruction is its "
                        "OWN concept — a portfolio review, a fraud report, a mortgage "
                        "question, and a payment/standing-order setup are FOUR separate "
                        "concepts even in one breath, even if all are 'banking'. Two "
                        "requests are the same concept ONLY when the second is genuine "
                        "elaboration of the first (more detail or a clarifying follow-up "
                        "about the very same subject). Different subject or a new action "
                        "verb (set up, arrange, transfer, open, close, file, review, buy, "
                        "sell) => new concept.\n"
                        "DECISIVE boundary signal: explicit discourse markers that "
                        "announce a shift — 'also', 'separately', 'another thing', 'one "
                        "last thing', 'on a different topic', 'next', 'finally', 'by the "
                        "way', 'while I have you'. If NEXT opens with any such marker, "
                        "treat it as a NEW concept unless it is plainly still about the "
                        "exact same subject.\n"
                        "RULE: a greeting/pleasantry ('hello, how are you', 'thanks, "
                        "bye') is ALWAYS its own segment.\n"
                        "RULE: a shift between a work topic and off-topic small talk is "
                        "also a boundary.\n"
                        "When genuinely unsure, prefer is_new_topic=true — missing a "
                        "distinct intent is worse than over-splitting."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"CONCEPT SO FAR:\n{current}\n\n"
                        f"RECENT LINES:\n{recent}\n\n"
                        f"NEXT:\n{candidate}"
                    ),
                },
            ],
        )
        data = json.loads(resp.choices[0].message.content)
        return bool(data["is_new_topic"])

    async def _extract(self, text: str) -> tuple[ConceptChunk, bool]:
        # NOTE: returns (chunk, is_relevant). chunk carries semantics + a
        # retrieval plan (data_requests) — the plan is NOT executed here.
        # The model occasionally returns a truncated/invalid JSON body; retry a
        # couple of times before giving up rather than crash the whole stream.
        last_err: Exception | None = None
        for _attempt in range(3):
            try:
                return await self._extract_once(text)
            except (json.JSONDecodeError, KeyError) as e:
                last_err = e
        raise last_err  # type: ignore[misc]

    async def _extract_once(self, text: str) -> tuple[ConceptChunk, bool]:
        resp = await self.client.chat.completions.create(
            model=self.extract_model,
            temperature=0,
            seed=self.seed,
            max_tokens=4096,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "concept",
                    "strict": True,
                    "schema": _EXTRACT_SCHEMA,
                },
            },
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"Today's date is {self.today}. Resolve all spoken/relative "
                        "dates against it (e.g. 'June 18' -> this year unless context "
                        "says otherwise; 'last month', '3 days ago'). Output since/until "
                        "as YYYY-MM-DD.\n"
                        "You support a private-bank relationship manager during a live "
                        "client call. For this transcript slice, do TWO things:\n"
                        "1) Extract the core concept (topic, summary, the client's "
                        "intent, entities). Set is_relevant=false ONLY for a pure "
                        "greeting/pleasantry or personal small talk (weather, sports, "
                        "family). ANY financial/banking request is relevant — including "
                        "payments, standing orders, and transfers — even if no data "
                        "source below applies (leave data_requests empty in that case). "
                        "Relevance does NOT depend on a data source being available.\n"
                        "2) Build data_requests: a plan of which back-office data "
                        "sources the RM should pull to address this concept, and the "
                        "filters to apply. Available sources and their filters:\n"
                        "  - portfolio: ticker, sector, min/max_profit_loss\n"
                        "  - trades: ticker, operation_type, since, until, min_value\n"
                        "  - customer_profile: (no filters)\n"
                        "  - real_estate: property_type, status, location, min/max_value\n"
                        "  - market_movements: ticker, min_change_percent, direction, "
                        "since, sector\n"
                        "  - news: news_query (required), top_k, category, ticker\n"
                        "Only set filters relevant to each chosen source; leave the rest "
                        "null.\n"
                        "TICKERS: the data layer stores SIX Swiss Exchange tickers. You "
                        "MUST map every company to its EXACT ticker below — never use US/"
                        "ADR or generic forms (e.g. 'UBS' and 'NVS' are WRONG; use 'UBSG', "
                        f"'NOVN'). Mapping: {_TICKER_MAP_HINT}. If a company is not in "
                        "this list, leave ticker null rather than guessing.\n"
                        "NEWS: keep news searches loose. Put the topic in news_query and "
                        "set ticker when a specific company is named. Leave category NULL "
                        "unless the client explicitly asks for one kind of news — a wrong "
                        "category silently drops valid hits. Prefer a top_k of about 5.\n"
                        "When the client wants everything in a category (e.g. 'show me all "
                        "my properties', 'my whole portfolio'), set that filter to 'all' "
                        "to return every row. Use multiple sources when useful. Leave "
                        "data_requests empty if no lookup is needed. If is_relevant is "
                        "false, data_requests must be empty."
                    ),
                },
                {"role": "user", "content": text},
            ],
        )
        data = json.loads(resp.choices[0].message.content)
        requests = [
            DataRequest(
                source=r["source"],
                rationale=r["rationale"],
                # drop null filters so downstream gets only what was set
                filters={k: v for k, v in r["filters"].items() if v is not None},
            )
            for r in data.get("data_requests", [])
        ]
        chunk = ConceptChunk(
            text=text,
            topic=data["topic"],
            summary=data["summary"],
            intent=data["intent"],
            entities=data["entities"],
            data_requests=requests,
        )
        return chunk, bool(data["is_relevant"])


async def _maybe_await(value) -> None:
    if asyncio.iscoroutine(value):
        await value
