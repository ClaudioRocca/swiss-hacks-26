"""Wire streaming STT -> concept segmenter into one call.

    await run_file("clip.mp3", on_trigger=print_chunk)

Audio is decoded and paced to simulate a live mic, transcribed in real time,
and finalized utterances are fed to the segmenting agent which emits a trigger
(ConceptChunk) every time it detects a concept boundary.
"""

from __future__ import annotations

from typing import Optional

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


async def _maybe_await(value) -> None:
    import asyncio

    if asyncio.iscoroutine(value):
        await value
