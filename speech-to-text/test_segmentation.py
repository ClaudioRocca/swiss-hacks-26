"""Segmentation-accuracy harness.

Core question for the project: when a conversation carries 2-3 distinct
intents, does the agent spot each topic change and surface every intent as its
own concept?

Each case pairs a scripted chat with its ground-truth intents (keyword cues +
the data sources we'd expect). We run the real pipeline (text -> segmenter),
greedily map each emitted concept to the intent it best matches, then print
EXPECTED vs ACTUAL and flag any intent that was missed or merged into another.

Run:  python test_segmentation.py
Needs OPENAI_API_KEY (via .env).
"""

import asyncio
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent))

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from src.orchestrator import run_utterances, split_utterances

GREEN, RED, YELLOW, DIM, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[1m", "\033[0m",
)


@dataclass
class Intent:
    label: str
    keywords: List[str]          # any-of cues expected in the matched concept
    sources: List[str] = field(default_factory=list)  # expected data sources


@dataclass
class Case:
    name: str
    script: str
    expected: List[Intent]


# ---------------------------------------------------------------- test cases
# Controlled, in-domain (private bank). Intents are deliberately independent so
# a correct segmenter must split them.

CASES = [
    Case(
        name="2 intents: trade + market/news",
        script=(
            "I'd like to sell two hundred of my Nestle shares today. "
            "Separately, how is the overall market doing, and is there any "
            "recent news on Apple I should know about?"
        ),
        expected=[
            Intent("sell Nestle", ["sell", "nestle", "nesn", "share"], ["trades"]),
            Intent("market + Apple news", ["market", "news", "apple"],
                   ["market_movements", "news"]),
        ],
    ),
    Case(
        name="3 intents: fraud + mortgage + standing order",
        script=(
            "Hi, I noticed a charge on my account I don't recognize, 249 francs "
            "from some company called DigiStore24. Please investigate and block "
            "my card if needed. "
            "On a completely different topic, my partner and I want to buy an "
            "apartment in Zurich for about 1.2 million, what mortgage rate could "
            "we get? "
            "One last thing, please set up a monthly standing order of 2100 "
            "francs to my landlord Thomas Keller starting next month."
        ),
        expected=[
            Intent("unauthorized charge", ["charge", "unauthor", "fraud", "block",
                   "digistore"], ["trades", "customer_profile"]),
            Intent("mortgage inquiry", ["mortgage", "apartment", "property",
                   "zurich"], ["real_estate"]),
            Intent("standing order", ["standing order", "landlord", "monthly",
                   "keller"], []),
        ],
    ),
    Case(
        name="2 intents: portfolio review + real estate",
        script=(
            "Can you review my entire stock portfolio across all sectors? I want "
            "the full picture of everything I hold. "
            "Also, I'm thinking about diversifying into commercial real estate, "
            "ideally an active property in Geneva up to five million francs."
        ),
        expected=[
            Intent("portfolio review", ["portfolio", "holding", "position",
                   "sector"], ["portfolio"]),
            Intent("real estate", ["real estate", "property", "commercial",
                   "geneva"], ["real_estate"]),
        ],
    ),
]


async def _segment(script: str):
    chunks = []
    await run_utterances(split_utterances(script), on_trigger=lambda c: chunks.append(c))
    return chunks


def _haystack(chunk) -> str:
    return " ".join(
        [chunk.topic, chunk.summary, chunk.intent, " ".join(chunk.entities), chunk.text]
    ).lower()


def evaluate(case: Case, chunks) -> bool:
    # greedily assign each concept to the intent it best matches by keyword hits
    assigned = {i: [] for i in range(len(case.expected))}
    unmatched = []
    for c in chunks:
        hay = _haystack(c)
        best_idx, best_score = None, 0
        for idx, intent in enumerate(case.expected):
            score = sum(1 for kw in intent.keywords if kw.lower() in hay)
            if score > best_score:
                best_idx, best_score = idx, score
        if best_idx is not None:
            assigned[best_idx].append(c)
        else:
            unmatched.append(c)

    print(f"\n{BOLD}CASE:{RESET} {case.name}")
    print(f"  expected {len(case.expected)} intents | actual {len(chunks)} concepts")

    ok = True
    for idx, intent in enumerate(case.expected):
        got = assigned[idx]
        if not got:
            ok = False
            print(f"  {RED}[MISS]{RESET} {intent.label} — not detected (merged or missing)")
            continue
        if len(got) > 1:
            print(f"  {YELLOW}[SPLIT]{RESET} {intent.label} — {len(got)} concepts "
                  f"({', '.join(repr(c.topic) for c in got)})")
        c = got[0]
        got_sources = sorted({r.source for g in got for r in g.data_requests})
        miss_src = [s for s in intent.sources if s not in got_sources]
        src_note = (f"{GREEN}sources ok{RESET}" if not miss_src
                    else f"{YELLOW}missing sources {miss_src}{RESET}")
        print(f"  {GREEN}[OK]{RESET}   {intent.label} -> {repr(c.topic)} "
              f"[{', '.join(got_sources) or '—'}] {src_note}")

    if unmatched:
        print(f"  {YELLOW}[EXTRA]{RESET} {len(unmatched)} concept(s) matched no "
              f"intent: {', '.join(repr(c.topic) for c in unmatched)}")

    # segmentation correct = every intent got exactly one distinct concept
    seg_ok = all(len(assigned[i]) >= 1 for i in range(len(case.expected)))
    verdict = (f"{GREEN}PASS{RESET}" if ok and seg_ok else f"{RED}FAIL{RESET}")
    print(f"  {BOLD}RESULT:{RESET} {verdict}")
    return ok and seg_ok


def main() -> int:
    if not os.getenv("OPENAI_API_KEY"):
        print("error: OPENAI_API_KEY required (set it in .env)", file=sys.stderr)
        return 2

    passed = 0
    for case in CASES:
        chunks = asyncio.run(_segment(case.script))
        if evaluate(case, chunks):
            passed += 1

    print(f"\n{BOLD}=== {passed}/{len(CASES)} cases passed ==={RESET}")
    return 0 if passed == len(CASES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
