"""Speech-to-text via OpenAI's audio transcription API."""

from __future__ import annotations

import os
from pathlib import Path
from typing import BinaryIO, Union

from openai import OpenAI

# gpt-4o-mini-transcribe: cheap, accurate, multilingual. Override with STT_MODEL.
# Alternatives: "gpt-4o-transcribe" (best quality), "whisper-1" (legacy).
DEFAULT_MODEL = os.getenv("STT_MODEL", "gpt-4o-mini-transcribe")

AudioSource = Union[str, Path, bytes, BinaryIO]

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """Lazy singleton so importing this module doesn't require a key."""
    global _client
    if _client is None:
        _client = OpenAI()  # reads OPENAI_API_KEY from env
    return _client


def transcribe(
    audio: AudioSource,
    *,
    model: str = DEFAULT_MODEL,
    language: str | None = None,
    prompt: str | None = None,
) -> str:
    """Transcribe an audio source and return the plain-text transcript.

    Args:
        audio: file path, raw bytes, or an open binary file-like object.
        model: transcription model id.
        language: optional ISO-639-1 hint (e.g. "en", "it") for accuracy/speed.
        prompt: optional context/vocab hint to steer the transcription.

    Returns:
        The transcript text.
    """
    file_arg, close_after = _as_file(audio)
    try:
        kwargs: dict = {"model": model, "file": file_arg, "response_format": "text"}
        if language:
            kwargs["language"] = language
        if prompt:
            kwargs["prompt"] = prompt

        result = _get_client().audio.transcriptions.create(**kwargs)
        # response_format="text" returns a str; objects expose .text
        return result if isinstance(result, str) else result.text
    finally:
        if close_after:
            file_arg.close()


def _as_file(audio: AudioSource) -> tuple[object, bool]:
    """Normalize an audio source to something the SDK accepts.

    Returns (file_object_or_tuple, should_close).
    """
    if isinstance(audio, (str, Path)):
        return open(audio, "rb"), True
    if isinstance(audio, bytes):
        # SDK accepts a (filename, bytes) tuple; name only drives format sniffing.
        return ("audio.wav", audio), False
    # Assume an already-open binary file-like object.
    return audio, False
