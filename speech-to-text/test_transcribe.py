"""Quick manual test: feed an audio file, print the transcript.

Usage:
    python test_transcribe.py path/to/audio.mp3
    python test_transcribe.py path/to/audio.wav --language it

Needs OPENAI_API_KEY in the environment (or a .env file).
"""

import argparse
import sys
import time
from pathlib import Path

# allow running from anywhere: make src importable
sys.path.insert(0, str(Path(__file__).parent))

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # dotenv optional; env vars may already be set

from src import transcribe


def main() -> int:
    parser = argparse.ArgumentParser(description="Transcribe an audio file.")
    parser.add_argument("audio", help="path to the audio file")
    parser.add_argument("--language", help="ISO-639-1 hint, e.g. en, it")
    parser.add_argument("--model", help="override the transcription model")
    parser.add_argument("--prompt", help="vocab/context hint")
    args = parser.parse_args()

    path = Path(args.audio)
    if not path.is_file():
        print(f"error: file not found: {path}", file=sys.stderr)
        return 1

    kwargs = {}
    if args.language:
        kwargs["language"] = args.language
    if args.model:
        kwargs["model"] = args.model
    if args.prompt:
        kwargs["prompt"] = args.prompt

    print(f"transcribing {path} ...", file=sys.stderr)
    start = time.perf_counter()
    text = transcribe(str(path), **kwargs)
    elapsed = time.perf_counter() - start

    print(f"\n--- transcript ({elapsed:.1f}s) ---")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
