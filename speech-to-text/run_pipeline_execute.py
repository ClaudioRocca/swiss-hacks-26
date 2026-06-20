"""Full pipeline E2E: conversation -> concept segmentation -> intent/plan
extraction -> QUERY EXECUTION against the data layer.

Unlike demo_text.py (which only *emits* the retrieval plan), this script also
RUNS each planned DataRequest against src/data/db.py and collects the retrieved
rows. It writes a JSON file with, for every concept, every executed query and
its returned data, plus a human-readable console summary.

Usage:
    python run_pipeline_execute.py                                  # default call_4
    python run_pipeline_execute.py client_calls/call_2_bank_support.txt
    python run_pipeline_execute.py call.txt --out results.json --now 2025-05-26

--now pins the date the extractor resolves spoken/relative dates against
(e.g. "last month", "June 18"). It defaults to 2025-05-26 so relative dates in
the scripted calls land inside the seeded data window (data is May 2025).
"""

import argparse
import asyncio
import dataclasses
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from dotenv import load_dotenv

    load_dotenv()  # speech-to-text/.env
except ImportError:
    pass

from src.agent.segmenter import ConceptChunk, ConceptSegmenter
from src.data import DataLayerError, db
from src.orchestrator import split_utterances

# "all" sentinel + null both mean "no filter". Drop them before calling db.py:
# passing "all" to a free-string field LIKE-matches literally -> 0 rows.
_SENTINEL = "all"

# Date-typed filter keys + a leading YYYY-MM-DD matcher. The LLM occasionally
# leaks junk into a date string (e.g. "2025-05-26}}]}]},"); clip to the valid
# ISO prefix so db.py's date guard + SQL compare aren't at the mercy of garbage.
_DATE_KEYS = {"since", "until"}
_ISO_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def _sanitize_date(value):
    """Clip a planned date to its leading YYYY-MM-DD; None if no valid prefix."""
    if not isinstance(value, str):
        return value
    m = _ISO_DATE_RE.match(value.strip())
    return m.group(1) if m else None

# Which db.py function backs each source, and which planned-filter keys it accepts.
# (The plan uses a union schema; we keep only the keys each source understands.)
_SOURCES = {
    "portfolio": {
        "func": db.get_portfolio,
        "keys": {"ticker", "sector", "min_profit_loss", "max_profit_loss"},
    },
    "trades": {
        "func": db.get_trades,
        "keys": {"ticker", "operation_type", "since", "until", "min_value"},
    },
    "customer_profile": {
        "func": db.get_customer_profile,
        "keys": set(),
    },
    "real_estate": {
        "func": db.get_real_estate,
        "keys": {"property_type", "status", "location", "min_value", "max_value"},
    },
    "market_movements": {
        "func": db.get_market_movements,
        "keys": {"ticker", "min_change_percent", "direction", "since", "sector"},
    },
    "news": {
        "func": db.search_news,
        # plan emits "news_query"; db.search_news expects "query"
        "keys": {"news_query", "top_k", "category", "ticker"},
    },
}


def _build_kwargs(source: str, planned_filters: dict) -> dict:
    """Translate a planned filter dict into kwargs for the source's db function.

    - keeps only keys the function accepts
    - drops the "all" sentinel (and any null) -> omit filter / return everything
    - renames news_query -> query for the news source
    """
    allowed = _SOURCES[source]["keys"]
    kwargs = {}
    for k, v in planned_filters.items():
        if k not in allowed:
            continue
        if v is None or (isinstance(v, str) and v.strip().lower() == _SENTINEL):
            continue
        if k in _DATE_KEYS:
            v = _sanitize_date(v)
            if v is None:  # unrecoverable date -> drop filter
                continue
        kwargs[k] = v
    if source == "news":
        # query is a required positional for search_news
        kwargs["query"] = kwargs.pop("news_query", "") or ""
    return kwargs


def _execute(source: str, planned_filters: dict) -> dict:
    """Run one planned query. Returns an executable record (never raises)."""
    record = {
        "source": source,
        "filters_planned": planned_filters,
    }
    if source not in _SOURCES:
        record["error"] = f"unknown source: {source}"
        record["results"] = None
        return record

    kwargs = _build_kwargs(source, planned_filters)
    record["call"] = {"function": _SOURCES[source]["func"].__name__, "kwargs": kwargs}

    if source == "news" and not kwargs.get("query"):
        record["error"] = "news query missing — skipped"
        record["results"] = None
        record["result_count"] = 0
        return record

    try:
        results = _SOURCES[source]["func"](**kwargs)
    except DataLayerError as e:
        record["error"] = f"DataLayerError: {e}"
        record["results"] = None
        return record
    except Exception as e:  # defensive: bad kwargs etc.
        record["error"] = f"{type(e).__name__}: {e}"
        record["results"] = None
        return record

    record["error"] = None
    if isinstance(results, list):
        record["result_count"] = len(results)
        record["results"] = results
    else:  # customer_profile -> dict
        record["result_count"] = 1 if results else 0
        record["results"] = results
    return record


async def run(conversation: str, now: date) -> list[dict]:
    """Segment the conversation, extract plans, execute every query.

    Returns a list of concept records (semantics + executed queries).
    Built directly on ConceptSegmenter so we control the `now` date the
    extractor resolves relative dates against.
    """
    concepts: list[dict] = []

    def on_trigger(chunk: ConceptChunk) -> None:
        executed = [_execute(r.source, r.filters) for r in chunk.data_requests]
        concepts.append(
            {
                "index": chunk.index,
                "topic": chunk.topic,
                "summary": chunk.summary,
                "intent": chunk.intent,
                "entities": chunk.entities,
                "text": chunk.text,
                "data_requests": [
                    {"source": r.source, "rationale": r.rationale} for r in chunk.data_requests
                ],
                "executed_queries": executed,
            }
        )

    segmenter = ConceptSegmenter(on_trigger, now=now)
    for utt in split_utterances(conversation):
        try:
            await segmenter.add_final(utt)
        except Exception as e:  # one flaky LLM concept shouldn't sink the run
            print(f"  ! skipped a concept (extract failed): {e}", file=sys.stderr)
    try:
        await segmenter.close()
    except Exception as e:
        print(f"  ! trailing concept flush failed: {e}", file=sys.stderr)
    return concepts


def _print_summary(concepts: list[dict]) -> None:
    print("\n" + "=" * 70)
    print(f"PIPELINE RESULT — {len(concepts)} concept(s) emitted")
    print("=" * 70)
    for c in concepts:
        print(f"\n[{c['index']}] {c['topic']}")
        print(f"    intent : {c['intent']}")
        print(f"    summary: {c['summary']}")
        if not c["executed_queries"]:
            print("    (no data queries)")
        for q in c["executed_queries"]:
            kw = q.get("call", {}).get("kwargs", {})
            if q.get("error"):
                print(f"    ! {q['source']}({kw}) -> ERROR: {q['error']}")
            else:
                print(f"    + {q['source']}({kw}) -> {q['result_count']} row(s)")


async def main() -> int:
    p = argparse.ArgumentParser(description="Run full pipeline + execute queries.")
    p.add_argument(
        "path",
        nargs="?",
        default="client_calls/call_4_wealth_management.txt",
        help="conversation .txt file (default: call_4)",
    )
    p.add_argument("--out", default="results/pipeline_results.json", help="JSON output path")
    p.add_argument(
        "--now",
        default="2025-05-26",
        help="date the extractor resolves relative dates against (YYYY-MM-DD)",
    )
    args = p.parse_args()

    if not Path(args.path).is_file():
        print(f"error: file not found: {args.path}", file=sys.stderr)
        return 1

    conversation = Path(args.path).read_text()
    now = date.fromisoformat(args.now)

    print(f"conversation: {args.path}")
    print(f"resolving dates against: {now.isoformat()}")
    print("running segmentation + extraction + query execution...")

    concepts = await run(conversation, now)

    payload = {
        "conversation_file": args.path,
        "resolved_date": now.isoformat(),
        "concept_count": len(concepts),
        "query_count": sum(len(c["executed_queries"]) for c in concepts),
        "concepts": concepts,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str))

    _print_summary(concepts)
    print("\n" + "=" * 70)
    print(f"wrote {payload['query_count']} executed queries across "
          f"{payload['concept_count']} concepts -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
