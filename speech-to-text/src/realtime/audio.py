"""Decode an audio file to PCM16 and yield it in real-time-paced chunks.

OpenAI's realtime API wants mono, 16-bit little-endian PCM at 24 kHz.
We shell out to ffmpeg to decode any input (mp3/wav/m4a/...) to that format,
then emit fixed-duration chunks with a matching sleep so a recorded file
plays back at "wall-clock" speed — i.e. simulates a live microphone.
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

SAMPLE_RATE = 24_000  # Hz, required by realtime pcm16
BYTES_PER_SAMPLE = 2  # 16-bit mono


async def stream_file_as_pcm(
    path: str,
    *,
    chunk_ms: int = 100,
    realtime: bool = True,
) -> AsyncIterator[bytes]:
    """Yield PCM16 (24kHz mono) chunks from an audio file.

    Args:
        path: input audio file (any ffmpeg-readable format).
        chunk_ms: size of each emitted chunk in milliseconds.
        realtime: if True, sleep chunk_ms between chunks to mimic live audio.
                  Set False to push as fast as possible (e.g. offline tests).
    """
    chunk_bytes = int(SAMPLE_RATE * BYTES_PER_SAMPLE * chunk_ms / 1000)

    proc = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-i", path,
        "-f", "s16le",
        "-acodec", "pcm_s16le",
        "-ac", "1",
        "-ar", str(SAMPLE_RATE),
        "-loglevel", "error",
        "pipe:1",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    assert proc.stdout is not None
    try:
        while True:
            chunk = await proc.stdout.readexactly(chunk_bytes)
            yield chunk
            if realtime:
                await asyncio.sleep(chunk_ms / 1000)
    except asyncio.IncompleteReadError as e:
        # final partial chunk at end of stream
        if e.partial:
            yield e.partial
    finally:
        if proc.returncode is None:
            proc.terminate()
        await proc.wait()
