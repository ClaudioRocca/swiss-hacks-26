"""Live demo: stream an audio file, transcribe in real time, and watch the
orchestrating agent emit concept triggers as topics shift.

Usage:
    python demo_realtime.py /path/to/audio.mp3
    python demo_realtime.py /path/to/audio.mp3 --language en --no-partials

Needs OPENAI_API_KEY (via .env or env).
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from src.agent.segmenter import ConceptChunk
from src.orchestrator import run_file

# ANSI for readable live output
DIM = "\033[2m"
BOLD = "\033[1m"
CYAN = "\033[36m"
GREEN = "\033[32m"
RESET = "\033[0m"


def make_handlers(show_partials: bool):
    state = {"line": ""}

    def on_partial(delta: str) -> None:
        if not show_partials:
            return
        state["line"] += delta
        sys.stdout.write(f"\r{DIM}… {state['line']}{RESET}")
        sys.stdout.flush()

    def on_final(text: str, speaker: str = "client") -> None:
        state["line"] = ""
        sys.stdout.write("\r\033[K")  # clear partial line
        print(f"{DIM}final ▸ [{speaker}] {text}{RESET}")

    def on_trigger(chunk: ConceptChunk) -> None:
        print()
        print(f"{BOLD}{GREEN}● TRIGGER #{chunk.index} — concept boundary{RESET}")
        print(f"  {BOLD}topic{RESET}    {CYAN}{chunk.topic}{RESET}")
        print(f"  {BOLD}summary{RESET}  {chunk.summary}")
        print(f"  {BOLD}intent{RESET}   {chunk.intent}")
        if chunk.entities:
            print(f"  {BOLD}entities{RESET} {', '.join(chunk.entities)}")
        if chunk.data_requests:
            print(f"  {BOLD}data plan{RESET}")
            for r in chunk.data_requests:
                flt = ", ".join(f"{k}={v}" for k, v in r.filters.items()) or "—"
                print(f"    {CYAN}{r.source}{RESET}  [{flt}]")
                print(f"      {DIM}{r.rationale}{RESET}")
        print(f"  {DIM}text     “{chunk.text}”{RESET}")
        print()

    return on_partial, on_final, on_trigger


async def main() -> int:
    parser = argparse.ArgumentParser(description="Live STT + concept segmentation.")
    parser.add_argument("audio", help="path to the audio file")
    parser.add_argument("--language", help="ISO-639-1 hint, e.g. en, it")
    parser.add_argument(
        "--no-partials", action="store_true", help="hide growing partial text"
    )
    parser.add_argument(
        "--fast", action="store_true", help="don't pace audio in real time"
    )
    args = parser.parse_args()

    if not Path(args.audio).is_file():
        print(f"error: file not found: {args.audio}", file=sys.stderr)
        return 1

    on_partial, on_final, on_trigger = make_handlers(not args.no_partials)

    print(f"{BOLD}streaming{RESET} {args.audio}\n")
    await run_file(
        args.audio,
        on_trigger=on_trigger,
        on_partial=on_partial,
        on_final=on_final,
        language=args.language,
        realtime=not args.fast,
    )
    print(f"\n{BOLD}done.{RESET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
