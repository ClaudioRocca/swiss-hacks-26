"""Tests for the 'all' filter sentinel (return-everything signal).

Run:  python test_all_filter.py

- Static checks (no API): the schema exposes 'all' on every suitable field.
- Live check (needs OPENAI_API_KEY): a script that asks for the *entire*
  portfolio must produce at least one data_request whose filter == 'all'.
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from src.agent.segmenter import ALL_VALUE, _FILTERS_SCHEMA
from src.orchestrator import run_utterances, split_utterances

# ---------------------------------------------------------------- static checks

ENUM_FIELDS = ["operation_type", "direction", "property_type", "status", "category"]
STRING_FIELDS = ["ticker", "sector", "location"]


def test_schema_exposes_all():
    props = _FILTERS_SCHEMA["properties"]
    for f in ENUM_FIELDS:
        assert ALL_VALUE in props[f]["enum"], f"{f} enum missing '{ALL_VALUE}'"
        assert None in props[f]["enum"], f"{f} enum missing null"
    for f in STRING_FIELDS:
        assert ALL_VALUE in props[f]["description"], f"{f} desc missing '{ALL_VALUE}'"
    print(f"[ok] schema exposes '{ALL_VALUE}' on {ENUM_FIELDS + STRING_FIELDS}")


# ------------------------------------------------------------------ live check

ALL_PORTFOLIO_SCRIPT = (
    "Can you review my entire stock portfolio for me — every single position, "
    "across all sectors, no exceptions? I want the full picture of everything."
)


async def _collect(utterances):
    chunks = []
    await run_utterances(utterances, on_trigger=lambda c: chunks.append(c))
    return chunks


def _all_filters(chunks):
    return [
        (r.source, k, v)
        for c in chunks
        for r in c.data_requests
        for k, v in r.filters.items()
    ]


def test_live_emits_all():
    if not os.getenv("OPENAI_API_KEY"):
        print("[skip] live test — no OPENAI_API_KEY")
        return
    chunks = asyncio.run(_collect([ALL_PORTFOLIO_SCRIPT]))
    filters = _all_filters(chunks)
    all_uses = [(s, k, v) for (s, k, v) in filters if v == ALL_VALUE]
    assert all_uses, f"expected an '{ALL_VALUE}' filter, got: {filters}"
    print(f"[ok] live emitted '{ALL_VALUE}': {all_uses}")


def test_live_call_5():
    """End-to-end on the geopolitical/US-stocks script — should surface the
    'all' sentinel on the 'entire portfolio' concept."""
    if not os.getenv("OPENAI_API_KEY"):
        print("[skip] live call_5 — no OPENAI_API_KEY")
        return
    text = Path("client_calls/call_5_geopolitical_us_stocks.txt").read_text()
    chunks = asyncio.run(_collect(split_utterances(text)))
    print(f"[info] call_5 -> {len(chunks)} concepts:")
    for c in chunks:
        plan = [f"{r.source}{r.filters}" for r in c.data_requests]
        print(f"   - {c.topic}: {plan}")
    filters = _all_filters(chunks)
    assert any(v == ALL_VALUE for (_, _, v) in filters), (
        f"expected at least one '{ALL_VALUE}' across call_5, got: {filters}"
    )
    print(f"[ok] call_5 used '{ALL_VALUE}'")


if __name__ == "__main__":
    test_schema_exposes_all()
    test_live_emits_all()
    test_live_call_5()
    print("\nall tests passed.")
