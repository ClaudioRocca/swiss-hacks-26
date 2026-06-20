"""Streaming speech-to-text over OpenAI's Realtime transcription WebSocket.

Connects with ``intent=transcription``, streams PCM16 audio chunks, and
surfaces two kinds of events via callbacks:

  on_partial(text)  -> growing, not-yet-final text for the current utterance
  on_final(text)    -> a finalized utterance (server VAD detected end of speech)

Latency to first partial is typically a few hundred ms.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
from typing import AsyncIterator, Awaitable, Callable, Optional

import websockets

REALTIME_URL = "wss://api.openai.com/v1/realtime?intent=transcription"

# realtime transcription model: gpt-4o-transcribe (VAD-segmented utterances) or
# gpt-4o-mini-transcribe. gpt-realtime-whisper also works but self-segments.
DEFAULT_RT_MODEL = os.getenv("RT_STT_MODEL", "gpt-4o-transcribe")

PartialCb = Callable[[str], Optional[Awaitable[None]]]
FinalCb = Callable[[str], Optional[Awaitable[None]]]


async def _maybe_await(value) -> None:
    if asyncio.iscoroutine(value):
        await value


class RealtimeTranscriber:
    def __init__(
        self,
        *,
        model: str = DEFAULT_RT_MODEL,
        language: str | None = None,
        api_key: str | None = None,
    ):
        self.model = model
        self.language = language
        self.api_key = api_key or os.environ["OPENAI_API_KEY"]

    def _session_config(self) -> dict:
        # GA Realtime API shape: a transcription-type session with audio config
        # nested under session.audio.input.
        transcription: dict = {"model": self.model}
        if self.language:
            transcription["language"] = self.language
        return {
            "type": "session.update",
            "session": {
                "type": "transcription",
                "audio": {
                    "input": {
                        "format": {"type": "audio/pcm", "rate": 24000},
                        "transcription": transcription,
                        "turn_detection": {
                            "type": "server_vad",
                            "threshold": 0.5,
                            "prefix_padding_ms": 300,
                            "silence_duration_ms": 500,
                        },
                    }
                },
            },
        }

    async def run(
        self,
        audio_chunks: AsyncIterator[bytes],
        *,
        on_partial: PartialCb | None = None,
        on_final: FinalCb | None = None,
    ) -> None:
        """Stream audio through the socket until the audio iterator is exhausted."""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with websockets.connect(
            REALTIME_URL, additional_headers=headers, max_size=None
        ) as ws:
            await ws.send(json.dumps(self._session_config()))

            sender = asyncio.create_task(self._send_audio(ws, audio_chunks))
            try:
                await self._receive(ws, sender, on_partial, on_final)
            finally:
                if not sender.done():
                    sender.cancel()

    async def _send_audio(self, ws, audio_chunks: AsyncIterator[bytes]) -> None:
        async for chunk in audio_chunks:
            await ws.send(
                json.dumps(
                    {
                        "type": "input_audio_buffer.append",
                        "audio": base64.b64encode(chunk).decode("ascii"),
                    }
                )
            )
        # let trailing audio settle so the last utterance gets finalized
        await asyncio.sleep(1.0)

    async def _receive(
        self,
        ws,
        sender: asyncio.Task,
        on_partial: PartialCb | None,
        on_final: FinalCb | None,
    ) -> None:
        # Poll with a finite timeout so the loop keeps re-checking sender state.
        # While audio is still streaming, a timeout just means "nothing yet" and
        # we loop again. Once the audio is fully sent, a gap of idle_timeout with
        # no events means the stream is finished.
        poll_timeout = 0.5
        idle_timeout = 3.0
        idle_elapsed = 0.0
        while True:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=poll_timeout)
                idle_elapsed = 0.0
            except asyncio.TimeoutError:
                if sender.done():
                    idle_elapsed += poll_timeout
                    if idle_elapsed >= idle_timeout:
                        break  # audio done + quiet -> finished
                continue
            except websockets.ConnectionClosed:
                break

            event = json.loads(raw)
            etype = event.get("type", "")

            if etype == "conversation.item.input_audio_transcription.delta":
                if on_partial:
                    await _maybe_await(on_partial(event.get("delta", "")))

            elif etype == "conversation.item.input_audio_transcription.completed":
                if on_final:
                    await _maybe_await(on_final(event.get("transcript", "")))

            elif etype == "error":
                raise RuntimeError(f"realtime error: {event.get('error')}")
