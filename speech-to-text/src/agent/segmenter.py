"""Concept segmenter: the orchestrating agent.

Listens to finalized utterances as they stream in. After each one it asks a
cheap LLM whether the new utterance *continues the current concept* or *starts
a new one*. On a boundary it flushes the accumulated text as a ConceptChunk —
extracting structured semantics (topic, summary, intent, entities) — and emits
a trigger. This chunks an open-ended transcript by meaning, in real time.
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, field
from typing import Awaitable, Callable, List, Optional

from openai import AsyncOpenAI

JUDGE_MODEL = os.getenv("AGENT_MODEL", "gpt-4o-mini")


@dataclass
class ConceptChunk:
    """A semantically-coherent slice of the transcript."""

    text: str
    topic: str
    summary: str
    intent: str
    entities: List[str] = field(default_factory=list)
    index: int = 0


TriggerCb = Callable[[ConceptChunk], Optional[Awaitable[None]]]


_JUDGE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "is_new_topic": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["is_new_topic", "reason"],
}

_EXTRACT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "is_filler": {
            "type": "boolean",
            "description": (
                "true if this slice should be DISCARDED: either a pure "
                "greeting/pleasantry/acknowledgement (e.g. 'hello, how are you', "
                "'thanks, bye'), OR off-topic small talk unrelated to financial/"
                "banking/investment work (e.g. weather, sports, personal chit-chat). "
                "false ONLY if it carries a substantive work/financial concept."
            ),
        },
        "topic": {"type": "string", "description": "2-5 word concept label"},
        "summary": {"type": "string", "description": "one-sentence summary"},
        "intent": {"type": "string", "description": "what the speaker wants/means"},
        "entities": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["is_filler", "topic", "summary", "intent", "entities"],
}

# fixed seed + temperature 0 => near-reproducible judge/extract calls
DEFAULT_SEED = int(os.getenv("AGENT_SEED", "7"))


class ConceptSegmenter:
    def __init__(
        self,
        on_trigger: TriggerCb,
        *,
        model: str = JUDGE_MODEL,
        seed: int = DEFAULT_SEED,
    ):
        self.on_trigger = on_trigger
        self.model = model
        self.seed = seed
        self.client = AsyncOpenAI()
        self._buffer: List[str] = []
        self._emitted = 0

    @property
    def current_text(self) -> str:
        return " ".join(self._buffer).strip()

    async def add_final(self, utterance: str) -> None:
        """Feed one finalized utterance. May emit a trigger for the prior concept."""
        utterance = utterance.strip()
        if not utterance:
            return

        if not self._buffer:
            self._buffer.append(utterance)
            return

        if await self._is_new_topic(self.current_text, utterance):
            await self._flush()

        self._buffer.append(utterance)

    async def close(self) -> None:
        """Flush whatever concept is still buffered at end of stream."""
        await self._flush()

    async def _flush(self) -> None:
        text = self.current_text
        self._buffer = []
        if not text:
            return
        chunk, is_filler = await self._extract(text)
        if is_filler:
            return  # drop greetings/pleasantries — no trigger
        chunk.index = self._emitted
        self._emitted += 1
        await _maybe_await(self.on_trigger(chunk))

    async def _is_new_topic(self, current: str, candidate: str) -> bool:
        resp = await self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            seed=self.seed,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "boundary",
                    "strict": True,
                    "schema": _JUDGE_SCHEMA,
                },
            },
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are the assistant of a relationship manager in a private "
                        "bank. You segment a live transcript of a conversation between a "
                        "wealthy client and their relationship manager into distinct "
                        "concepts. The concepts that matter are financial, investment, "
                        "and banking-related work topics (e.g. transactions, fraud, "
                        "mortgages, payments, portfolio, accounts).\n"
                        "Given the CURRENT concept so far and the NEXT utterance, decide "
                        "if the next utterance starts a clearly different topic/concept. "
                        "Minor elaboration or follow-up is NOT a new topic.\n"
                        "RULE: a greeting/pleasantry (e.g. 'hello, how are you', "
                        "'thanks, bye') is ALWAYS its own segment — if CURRENT is only "
                        "a greeting/pleasantry and NEXT carries any real content, that "
                        "IS a new topic. Likewise NEXT being a greeting is a boundary.\n"
                        "RULE: a shift from a work/financial topic to off-topic small "
                        "talk (or vice versa) is also a boundary — segment them apart so "
                        "the off-topic part can be discarded downstream."
                    ),
                },
                {
                    "role": "user",
                    "content": f"CURRENT:\n{current}\n\nNEXT:\n{candidate}",
                },
            ],
        )
        data = json.loads(resp.choices[0].message.content)
        return bool(data["is_new_topic"])

    async def _extract(self, text: str) -> tuple[ConceptChunk, bool]:
        resp = await self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            seed=self.seed,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "concept",
                    "strict": True,
                    "schema": _EXTRACT_SCHEMA,
                },
            },
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You support a private-bank relationship manager. Extract the "
                        "core concept from this transcript slice of a client conversation. "
                        "Set is_filler=true if the slice is a greeting/pleasantry OR "
                        "off-topic small talk unrelated to financial/banking/investment "
                        "work; such slices are discarded. Otherwise capture the "
                        "work/financial concept."
                    ),
                },
                {"role": "user", "content": text},
            ],
        )
        data = json.loads(resp.choices[0].message.content)
        chunk = ConceptChunk(
            text=text,
            topic=data["topic"],
            summary=data["summary"],
            intent=data["intent"],
            entities=data["entities"],
        )
        return chunk, bool(data["is_filler"])


async def _maybe_await(value) -> None:
    if asyncio.iscoroutine(value):
        await value
