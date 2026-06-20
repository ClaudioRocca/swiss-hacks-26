"""Post-call pipeline demo (client2).

End-to-end (synthesis is out of scope for now):
  1. extract  the LAST (unanalysed) call with the LLM   -> stored insights + JSON
  2. retrieve the deterministic RISK-PROFILE TREND        -> onboarding -> past calls
                                                             -> inferred last point

Past calls carry only a mocked, as-if-LLM-extracted risk point (score + tag) seeded
at DB-build time, so the LLM only ever runs on the last call.

Run (from speech-to-text/, with the project venv):
    ./venv/bin/python demo_postcall.py            # full pipeline (extract + trend)
    ./venv/bin/python demo_postcall.py --no-extract   # reuse stored insights, just trend

Prereqs: client2 DB built (python -m src.data.init_db_client2) and OPENAI_API_KEY set.
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_SPEECH = Path(__file__).resolve().parent
_ROOT = _SPEECH.parent
load_dotenv(_SPEECH / ".env")
load_dotenv(_ROOT / ".env")

# Point the data layer at client2 BEFORE importing db.
os.environ["DATA_SQLITE_PATH"] = str(_SPEECH / "data" / "client2" / "portfolio.db")
os.environ["DATA_CHROMA_PATH"] = str(_SPEECH / "data" / "client2" / "chroma")

# Route every OpenAI client through verify=False (corporate proxy), before imports.
import httpx
import openai

_HTTP = httpx.Client(verify=False)
_ORIG = openai.OpenAI
openai.OpenAI = lambda *a, **k: (k.setdefault("http_client", _HTTP), _ORIG(*a, **k))[1]

sys.path.insert(0, str(_SPEECH))

from src.data import db                          # noqa: E402
from src.postcall import extraction, retrieval    # noqa: E402

CUSTOMER_ID = 1
_OUT_DIR = _SPEECH / "data" / "client2"


def _save(obj: dict, name: str) -> Path:
    """Write a pipeline artifact to data/client2/ and return its path."""
    path = _OUT_DIR / name
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str))
    return path


def _rule(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def _latest_call_id() -> int:
    calls = db.get_calls(customer_id=CUSTOMER_ID, limit=50)  # newest first
    calls_sorted = sorted(calls, key=lambda c: c.get("call_date", ""))
    return calls_sorted[-1]["id"]


def run_extraction() -> int:
    """Analyse ONLY the latest call with the LLM and store its insights.

    Past calls already carry their mocked risk point in the seed data, so the LLM
    never re-processes history. Returns the latest call id.
    """
    latest_id = _latest_call_id()
    print(f"Analysing latest call (id {latest_id}) — LLM runs here only…")
    extraction.extract_and_store(latest_id, customer_id=CUSTOMER_ID, store_trend_columns=True)
    return latest_id


def print_trend(trend: dict) -> None:
    _rule("RISK-PROFILE TREND")
    print(f"  declared (stated) appetite : {trend.get('declared_risk_appetite')}")
    ob = trend.get("onboarding") or {}
    print(f"  onboarding start           : {ob.get('date')}  {ob.get('score')} ({ob.get('appetite')})")
    print("\n  series (onboarding -> past calls -> inferred last point):")
    for s in trend.get("series", []):
        print(f"    {s.get('date')}  {s.get('score'):>4}  {s.get('appetite'):<13} [{s.get('source')}]")
    t = trend.get("trend") or {}
    if t:
        print(f"\n  trend: {t.get('from_score')} ({t.get('from_date')}) -> "
              f"{t.get('to_score')} ({t.get('to_date')}) | "
              f"delta {t.get('total_delta')} — {t.get('direction')}")


def main() -> None:
    do_extract = "--no-extract" not in sys.argv

    try:
        if do_extract:
            _rule("STEP 1 · EXTRACTION (latest call only — LLM)")
            latest_id = run_extraction()
        else:
            print("Skipping extraction (--no-extract): using stored insights.")
            latest_id = _latest_call_id()

        _rule("STEP 2 · RISK-PROFILE TREND (deterministic)")
        trend = retrieval.build_risk_trend(customer_id=CUSTOMER_ID)
        print_trend(trend)

        # Save an artifact per stage.
        saved = [
            _save(db.get_call(latest_id).get("insights") or {}, f"extraction_call{latest_id}.json"),
            _save(trend, "risk_trend.json"),
        ]
        _rule("SAVED ARTIFACTS")
        for p in saved:
            print(f"  {p.relative_to(_SPEECH)}")

    except extraction.ExtractionError as e:
        print(f"\nLLM ERROR: {e}")
        sys.exit(1)
    except db.DataLayerError as e:
        print(f"\nDATA ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
