"""Text-only pipeline test: skip audio + STT, feed scripted text straight into
the segmenter. Fast way to stress test segmentation + the structured-output plan.

Usage:
    python demo_text.py client_calls/call_1_insurance_claim.txt
    python demo_text.py client_calls/call_2_bank_support.txt --json
    echo "I want to sell my Nestle shares. Also how is the market today?" | python demo_text.py -
    python demo_text.py script.txt --show-utterances

Reuses the same ConceptSegmenter the audio pipeline uses — only the input
source differs. --json prints each emitted ConceptChunk (incl. data_requests)
as raw JSON, i.e. exactly the structured output your front-end will consume.
"""

import argparse
import asyncio
import dataclasses
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from src.agent.segmenter import ConceptChunk
from src.orchestrator import run_utterances, split_utterances

# reuse the pretty printer from the audio demo
from demo_realtime import make_handlers


def read_input(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text()


async def main() -> int:
    parser = argparse.ArgumentParser(description="Text-only segmentation test.")
    parser.add_argument("path", help="script .txt file, or '-' for stdin")
    parser.add_argument(
        "--json", action="store_true", help="emit each ConceptChunk as raw JSON"
    )
    parser.add_argument(
        "--show-utterances",
        action="store_true",
        help="print the split utterances before running",
    )
    args = parser.parse_args()

    if args.path != "-" and not Path(args.path).is_file():
        print(f"error: file not found: {args.path}", file=sys.stderr)
        return 1

    text = read_input(args.path)
    utterances = split_utterances(text)

    if args.show_utterances:
        print(f"# {len(utterances)} utterances:", file=sys.stderr)
        for i, u in enumerate(utterances):
            print(f"  [{i}] {u}", file=sys.stderr)
        print(file=sys.stderr)

    if args.json:
        def on_trigger(chunk: ConceptChunk) -> None:
            print(json.dumps(dataclasses.asdict(chunk), ensure_ascii=False))
        await run_utterances(utterances, on_trigger=on_trigger)
    else:
        _, _, on_trigger = make_handlers(show_partials=False)
        await run_utterances(utterances, on_trigger=on_trigger)
        print("\ndone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
