"""Manual test for the post-call EXTRACTION layer against the CLIENT2 database.

Runs GPT-4o-mini extraction on the *last* conversation in the client2 scenario
(Dr. Keller, niche-markets call at t = 2026-06-19 whose analysis fields are still
NULL) and prints the structured result.

Prerequisites (see the printed checklist if something is missing):
  1. OPENAI_API_KEY available (in speech-to-text/.env or the repo-root .env).
  2. The client2 database must be built first:
         cd speech-to-text
         python -m src.data.init_db_client2
     This creates data/client2/portfolio.db + data/client2/chroma.

Run it:
    cd speech-to-text
    python test_extraction.py            # read-only: extract + retrieve news, print
    python test_extraction.py --store    # also persist results onto the call row

The data layer resolves its DB paths from DATA_SQLITE_PATH / DATA_CHROMA_PATH at
import time, so we set those to the client2 files BEFORE importing the modules.
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_SPEECH_TO_TEXT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SPEECH_TO_TEXT_DIR.parent

# --- env: load the API key from either common .env location -------------------
load_dotenv(_SPEECH_TO_TEXT_DIR / ".env")
load_dotenv(_PROJECT_ROOT / ".env")

# --- point the data layer at the CLIENT2 scenario BEFORE importing db ----------
_CLIENT2_SQLITE = _SPEECH_TO_TEXT_DIR / "data" / "client2" / "portfolio.db"
_CLIENT2_CHROMA = _SPEECH_TO_TEXT_DIR / "data" / "client2" / "chroma"
os.environ["DATA_SQLITE_PATH"] = str(_CLIENT2_SQLITE)
os.environ["DATA_CHROMA_PATH"] = str(_CLIENT2_CHROMA)

# --- mirror init_db_client2's SSL workaround: route every OpenAI client through
#     a verify=False httpx client so corporate proxy SSL interception doesn't
#     break the extraction / embedding calls. Patch BEFORE importing the modules
#     (they do `from openai import OpenAI` at import time). ----------------------
import httpx
import openai

_HTTP_CLIENT = httpx.Client(verify=False)
_ORIG_OPENAI = openai.OpenAI


def _patched_openai(*args, **kwargs):
    kwargs.setdefault("http_client", _HTTP_CLIENT)
    return _ORIG_OPENAI(*args, **kwargs)


openai.OpenAI = _patched_openai

# Make `from src...` importable when run as a plain script.
sys.path.insert(0, str(_SPEECH_TO_TEXT_DIR))

from src.data import DataLayerError, db          # noqa: E402
from src.postcall import extraction              # noqa: E402
from src.postcall.extraction import ExtractionError  # noqa: E402

CUSTOMER_ID = 1  # client2 recycles Dr. Keller as customer_id 1


def _check_prerequisites() -> None:
    """Fail fast with a clear message if the key or DB isn't ready."""
    problems = []
    if not os.environ.get("OPENAI_API_KEY"):
        problems.append(
            "OPENAI_API_KEY is not set. Put it in speech-to-text/.env "
            "(copy .env.example) or the repo-root .env."
        )
    if not _CLIENT2_SQLITE.exists():
        problems.append(
            f"client2 SQLite DB not found at {_CLIENT2_SQLITE}.\n"
            "      Build it first:  python -m src.data.init_db_client2"
        )
    if not _CLIENT2_CHROMA.exists():
        problems.append(
            f"client2 ChromaDB not found at {_CLIENT2_CHROMA}.\n"
            "      Build it first:  python -m src.data.init_db_client2"
        )
    if problems:
        print("Cannot run extraction test — fix the following first:\n")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)


def main() -> None:
    store = "--store" in sys.argv
    _check_prerequisites()

    # Identify the last call (most recent => the one with NULL analysis fields).
    calls = db.get_calls(customer_id=CUSTOMER_ID, limit=1)
    if not calls:
        print(f"No calls found for customer {CUSTOMER_ID}.")
        sys.exit(1)
    last = calls[0]
    call_id = last["id"]

    full = db.get_call(call_id)
    profile = db.get_customer_profile()

    print("=" * 70)
    print("LAST CALL UNDER TEST")
    print("=" * 70)
    print(f"  call_id        : {call_id}")
    print(f"  call_date      : {last.get('call_date')}")
    print(f"  channel        : {last.get('channel')}")
    print(f"  declared risk  : {profile.get('risk_appetite')} (official KYC profile)")
    analysed = any(last.get(k) is not None for k in
                   ("summary", "sentiment_score", "sentiment_label", "risk_signal"))
    print(f"  already analysed? {analysed}  "
          f"(expected False — the last call's fields should be NULL)")
    print("\n  transcript:")
    print("  " + (full.get("transcript", "").strip().replace("\n", "\n  ")))
    print()

    print("=" * 70)
    print(f"RUNNING EXTRACTION  (model: {extraction.EXTRACTION_MODEL})")
    print("=" * 70)

    try:
        if store:
            bundle = extraction.extract_and_store(call_id, customer_id=CUSTOMER_ID)
            print("(persisted to the call row via save_call_insights)\n")
        else:
            bundle = extraction.extract_facts(
                full.get("transcript", ""),
                declared_risk_appetite=profile.get("risk_appetite"),
            )
    except ExtractionError as e:
        print(f"EXTRACTION ERROR: {e}")
        sys.exit(1)
    except DataLayerError as e:
        print(f"DATA LAYER ERROR: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"UNEXPECTED FAILURE: {type(e).__name__}: {e}")
        sys.exit(1)

    print(json.dumps(bundle, indent=2, ensure_ascii=False))

    # Quick human-readable digest of the five features.
    print("\n" + "=" * 70)
    print("DIGEST")
    print("=" * 70)
    print(f"summary: {bundle.get('summary')}")
    sent = bundle.get("sentiment", {})
    traj = sent.get("trajectory", {}) or {}
    print(f"overall mood: {sent.get('overall_label')} ({sent.get('overall_score')}), "
          f"{len(sent.get('mood_timeline', []))} timeline points")
    print(f"trajectory: {traj.get('start')} -> {traj.get('end')}  ({traj.get('note')})")
    risk = bundle.get("risk", {})
    print(f"risk: declared={risk.get('declared_risk_appetite')} -> "
          f"inferred={risk.get('inferred_risk_appetite')} "
          f"(score {risk.get('inferred_risk_score')}), drift={risk.get('kyc_drift')}")
    print(f"  drift_explanation: {risk.get('drift_explanation')}")
    for sig in risk.get("drift_signals", []):
        print(f"  - {sig.get('signal')}  «{sig.get('quote')}»")
    facts = bundle.get("important_facts", [])
    print(f"important facts: {len(facts)}, "
          f"action items: {len(bundle.get('action_items', []))}, "
          f"rm proposals: {len(bundle.get('rm_proposals', []))}, "
          f"news matched: {len(bundle.get('relevant_market_news', []))}")


if __name__ == "__main__":
    main()
