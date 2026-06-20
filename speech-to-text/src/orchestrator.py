"""Wire streaming STT -> concept segmenter into one call.

    await run_file("clip.mp3", on_trigger=print_chunk)   # audio
    await run_text(script, on_trigger=print_chunk)        # text only (no STT)

Audio is decoded and paced to simulate a live mic, transcribed in real time,
and finalized utterances are fed to the segmenting agent which emits a trigger
(ConceptChunk) every time it detects a concept boundary.

run_text/run_utterances skip audio+STT entirely: they feed text straight into
the segmenter as if STT had finalized those utterances — for fast stress tests.
"""

from __future__ import annotations

import asyncio
import re
from datetime import date
from typing import Iterable, List, Optional, Tuple, Union

# An utterance is either a plain string (speaker unknown -> treated as client)
# or a (speaker, text) tuple where speaker is "client" or "rm".
Utterance = Union[str, Tuple[str, str]]

from .agent.segmenter import ConceptSegmenter, TriggerCb
from .realtime.audio import stream_file_as_pcm
from .realtime.transcriber import PartialCb, RealtimeTranscriber


async def run_file(
    path: str,
    *,
    on_trigger: TriggerCb,
    on_partial: PartialCb | None = None,
    on_final: Optional[PartialCb] = None,
    language: str | None = None,
    realtime: bool = True,
    now: date | None = None,
) -> None:
    """Run the full live pipeline over an audio file.

    Args:
        path: audio file to stream.
        on_trigger: called with a ConceptChunk at each concept boundary.
        on_partial: optional, called with growing partial transcript text.
        on_final: optional, called with each finalized utterance (raw STT).
        language: optional ISO-639-1 hint.
        realtime: pace audio like a live mic (True) or push as fast as possible.
        now: date the extractor resolves spoken/relative dates against
            (default today); pin it to align with a fixed data window.
    """
    segmenter = ConceptSegmenter(on_trigger, now=now)

    async def handle_final(text: str) -> None:
        # Live audio is the client side of the call.
        if on_final:
            await _maybe_await(on_final(text, "client"))
        await segmenter.add_final(text, "client")

    transcriber = RealtimeTranscriber(language=language)
    audio = stream_file_as_pcm(path, realtime=realtime)

    await transcriber.run(audio, on_partial=on_partial, on_final=handle_final)
    await segmenter.close()  # flush the trailing concept


async def run_utterances(
    utterances: Iterable[Utterance],
    *,
    on_trigger: TriggerCb,
    on_final: Optional[PartialCb] = None,
    now: date | None = None,
    pace: float = 0.0,
) -> None:
    """Feed pre-split utterances straight into the segmenter (no audio, no STT).

    Each item is either a plain string (treated as a client utterance) or a
    (speaker, text) tuple. Every utterance — client AND relationship manager —
    is fed to the segmenter WITH its speaker, so the agent reads the full
    two-way exchange (the RM's confirmations/clarifications sharpen what data to
    pull). `on_final` mirrors each line to the transcript with its speaker.

    `now` pins the date the extractor resolves relative dates against.
    `pace` is seconds-per-word: when > 0, sleep after each utterance for roughly
    its spoken duration so the transcript streams at a natural speaking rhythm.
    """
    segmenter = ConceptSegmenter(on_trigger, now=now)
    for utt in utterances:
        if isinstance(utt, tuple):
            speaker, text = utt
        else:
            speaker, text = "client", utt
        text = text.strip()
        if not text:
            continue
        if on_final:
            await _maybe_await(on_final(text, speaker))
        if pace > 0:
            # ~spoken duration of this line, clamped so very short/long lines
            # still feel natural (min half a second, cap at 9s).
            words = len(text.split())
            await asyncio.sleep(min(max(words * pace, 0.5), 9.0))
        await segmenter.add_final(text, speaker)
    await segmenter.close()


async def run_text(
    text: str,
    *,
    on_trigger: TriggerCb,
    on_final: Optional[PartialCb] = None,
    now: date | None = None,
    pace: float = 0.0,
) -> None:
    """Same as run_utterances but splits raw text into sentence-ish utterances."""
    await run_utterances(
        split_utterances(text), on_trigger=on_trigger, on_final=on_final, now=now, pace=pace
    )


_MARKER_RE = re.compile(r"\[[^\]]*\]")           # [TOPIC SHIFT — ...]
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")        # split after . ! ?
# Speaker prefix at the start of a line, e.g. "Client:" / "RM:" / "Relationship Manager:".
_SPEAKER_RE = re.compile(r"^\s*(client|customer|rm|relationship manager|advisor)\s*:\s*", re.IGNORECASE)


def _normalize_speaker(label: str) -> str:
    """Map a spoken label to a canonical speaker id ('client' or 'rm')."""
    l = label.strip().lower()
    if l in {"client", "customer"}:
        return "client"
    return "rm"


def split_utterances(text: str) -> List[Tuple[str, str]]:
    """Turn a scripted call into (speaker, utterance) chunks, mimicking STT finals.

    - keeps only the spoken body (drops a metadata header before the first '---')
    - reads per-line speaker markers like 'Client:' / 'RM:'; lines without a
      marker inherit the previous speaker (continuation)
    - strips bracket cue markers like '[TOPIC SHIFT]' so the agent segments blind
    - splits on sentence boundaries, tagging every sentence with its speaker

    Scripts with no speaker markers fall back to all-client (legacy behaviour).
    """
    # drop metadata header: take everything after the first '---' divider, if any
    if "---" in text:
        text = text.split("---", 1)[1]

    out: List[Tuple[str, str]] = []
    speaker = "client"  # default until a marker says otherwise
    for line in text.splitlines():
        m = _SPEAKER_RE.match(line)
        if m:
            speaker = _normalize_speaker(m.group(1))
            line = line[m.end():]
        line = _MARKER_RE.sub(" ", line)            # remove cue markers
        line = re.sub(r"=+", " ", line)             # drop '====' rules
        flat = re.sub(r"\s+", " ", line).strip()
        if not flat:
            continue
        # protect titles so "Dr. Keller" isn't split into two utterances
        flat = re.sub(r"\b(Dr|Mr|Mrs|Ms|St|Prof)\.", r"\1∯", flat)
        for s in _SENTENCE_RE.split(flat):
            s = s.replace("∯", ".").strip()
            if s:
                out.append((speaker, s))
    return out


async def _maybe_await(value) -> None:
    import asyncio

    if asyncio.iscoroutine(value):
        await value
