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

import re
from typing import Iterable, List, Optional

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
) -> None:
    """Run the full live pipeline over an audio file.

    Args:
        path: audio file to stream.
        on_trigger: called with a ConceptChunk at each concept boundary.
        on_partial: optional, called with growing partial transcript text.
        on_final: optional, called with each finalized utterance (raw STT).
        language: optional ISO-639-1 hint.
        realtime: pace audio like a live mic (True) or push as fast as possible.
    """
    segmenter = ConceptSegmenter(on_trigger)

    async def handle_final(text: str) -> None:
        if on_final:
            await _maybe_await(on_final(text))
        await segmenter.add_final(text)

    transcriber = RealtimeTranscriber(language=language)
    audio = stream_file_as_pcm(path, realtime=realtime)

    await transcriber.run(audio, on_partial=on_partial, on_final=handle_final)
    await segmenter.close()  # flush the trailing concept


async def run_utterances(
    utterances: Iterable[str],
    *,
    on_trigger: TriggerCb,
    on_final: Optional[PartialCb] = None,
) -> None:
    """Feed pre-split utterances straight into the segmenter (no audio, no STT).

    Each string is treated as one finalized STT utterance. Use this to stress
    test segmentation + the structured-output plan on scripted text.
    """
    segmenter = ConceptSegmenter(on_trigger)
    for utt in utterances:
        utt = utt.strip()
        if not utt:
            continue
        if on_final:
            await _maybe_await(on_final(utt))
        await segmenter.add_final(utt)
    await segmenter.close()


async def run_text(
    text: str,
    *,
    on_trigger: TriggerCb,
    on_final: Optional[PartialCb] = None,
) -> None:
    """Same as run_utterances but splits raw text into sentence-ish utterances."""
    await run_utterances(
        split_utterances(text), on_trigger=on_trigger, on_final=on_final
    )


_MARKER_RE = re.compile(r"\[[^\]]*\]")           # [TOPIC SHIFT — ...]
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")        # split after . ! ?


def split_utterances(text: str) -> List[str]:
    """Turn a scripted call into utterance-sized chunks, mimicking STT finals.

    - keeps only the spoken body (drops a metadata header before the first '---')
    - strips bracket cue markers like '[TOPIC SHIFT]' so the agent segments blind
    - splits on sentence boundaries
    """
    # drop metadata header: take everything after the first '---' divider, if any
    if "---" in text:
        text = text.split("---", 1)[1]
    text = _MARKER_RE.sub(" ", text)               # remove cue markers
    text = re.sub(r"=+", " ", text)                 # drop '====' rules
    # collapse paragraph breaks into spaces, then sentence-split
    flat = re.sub(r"\s+", " ", text).strip()
    return [s.strip() for s in _SENTENCE_RE.split(flat) if s.strip()]


async def _maybe_await(value) -> None:
    import asyncio

    if asyncio.iscoroutine(value):
        await value
