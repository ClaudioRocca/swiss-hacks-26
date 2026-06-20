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
from typing import Awaitable, Callable, List, Optional

from openai import AsyncOpenAI

JUDGE_MODEL = os.getenv("AGENT_MODEL", "gpt-4o-mini")


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


def _nullable_enum(values: list[str], description: str) -> dict:
    """Nullable enum field for strict structured outputs (null is a valid value)."""
    return {"type": ["string", "null"], "enum": [*values, None], "description": description}


# Enum values mirror db.py validation sets exactly — keep in sync with src/data/db.py.
_FILTERS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "ticker": {**_STR, "description": "stock ticker symbol, e.g. NESN, AAPL"},
        "sector": _STR,
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
        "location": _STR,
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
                "false => DISCARD this slice (no trigger): a pure greeting/"
                "pleasantry, or off-topic small talk unrelated to financial/banking/"
                "investment work. true ONLY if it carries a substantive work concept."
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
        model: str = JUDGE_MODEL,
        seed: int = DEFAULT_SEED,
    ):
        self.on_trigger = on_trigger
        self.model = model
        self.seed = seed
        self.client = AsyncOpenAI()
        self._buffer: List[str] = []
        self._emitted = 0

    @property
    def current_text(self) -> str:
        return " ".join(self._buffer).strip()

    async def add_final(self, utterance: str) -> None:
        """Feed one finalized utterance. May emit a trigger for the prior concept."""
        utterance = utterance.strip()
        if not utterance:
            return

        if not self._buffer:
            self._buffer.append(utterance)
            return

        if await self._is_new_topic(self.current_text, utterance):
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
        chunk, is_relevant = await self._extract(text)
        if not is_relevant:
            return  # greeting/pleasantry or off-topic — no trigger
        chunk.index = self._emitted
        self._emitted += 1
        await _maybe_await(self.on_trigger(chunk))

    async def _is_new_topic(self, current: str, candidate: str) -> bool:
        resp = await self.client.chat.completions.create(
            model=self.model,
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
                        "bank. You segment a live transcript of a conversation between a "
                        "wealthy client and their relationship manager into distinct "
                        "concepts. The concepts that matter are financial, investment, "
                        "and banking-related work topics (e.g. transactions, fraud, "
                        "mortgages, payments, portfolio, accounts).\n"
                        "Given the CURRENT concept so far and the NEXT utterance, decide "
                        "if the next utterance starts a clearly different topic/concept. "
                        "Minor elaboration or follow-up is NOT a new topic.\n"
                        "RULE: a greeting/pleasantry (e.g. 'hello, how are you', "
                        "'thanks, bye') is ALWAYS its own segment — if CURRENT is only "
                        "a greeting/pleasantry and NEXT carries any real content, that "
                        "IS a new topic. Likewise NEXT being a greeting is a boundary.\n"
                        "RULE: a shift from a work/financial topic to off-topic small "
                        "talk (or vice versa) is also a boundary — segment them apart so "
                        "the off-topic part can be discarded downstream."
                    ),
                },
                {
                    "role": "user",
                    "content": f"CURRENT:\n{current}\n\nNEXT:\n{candidate}",
                },
            ],
        )
        data = json.loads(resp.choices[0].message.content)
        return bool(data["is_new_topic"])

    async def _extract(self, text: str) -> tuple[ConceptChunk, bool]:
        # NOTE: returns (chunk, is_relevant). chunk carries semantics + a
        # retrieval plan (data_requests) — the plan is NOT executed here.
        resp = await self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            seed=self.seed,
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
                        "You support a private-bank relationship manager during a live "
                        "client call. For this transcript slice, do TWO things:\n"
                        "1) Extract the core concept (topic, summary, the client's "
                        "intent, entities). Set is_relevant=false if it is a "
                        "greeting/pleasantry or off-topic small talk unrelated to "
                        "financial/banking/investment work (it will be discarded).\n"
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
                        "null. Map spoken references to concrete values (company name -> "
                        "ticker, e.g. 'Nestle' -> NESN). Use multiple sources when "
                        "useful. Leave data_requests empty if no lookup is needed. If "
                        "is_relevant is false, data_requests must be empty."
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
