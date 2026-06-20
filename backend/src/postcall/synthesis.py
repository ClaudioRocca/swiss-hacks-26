"""
================================================================================
RM INTELLIGENCE PLATFORM  -  POST-CALL SYNTHESIS LAYER
SwissHack / Julius Bär Challenge
================================================================================

The product. Single-call extraction is good; the VALUE is the connections no
single source contains. This layer takes the deterministic evidence packet from
retrieval.py (collisions, open commitments, drift, the latest call's insights,
the portfolio) and writes a PRESENTATION-READY pre-brief, organised BY INSIGHT
and recommended action — never "profile section / portfolio section / news
section" (four summaries stapled together = the failure mode).

Division of labour:
  - retrieval.py (code) DECIDES the connections (which holding x which news x
    which call-worry; which commitment is open). Deterministic, provable.
  - synthesis.py (LLM)  EXPLAINS them: headline, talking point, recommended
    action — and must NOT invent a match the packet doesn't contain.

Every synthesised claim carries provenance (call id + quote, holding ticker,
news source/date) so the eventual UI can show why. The output schema is shaped
as self-contained cards ready to become dashboard components.
================================================================================
"""

import json
import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

from src.postcall import retrieval
from src.postcall.extraction import ExtractionError

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env")

_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SYNTHESIS_MODEL = "gpt-4.1"


# =============================================================================
# PRESENTATION-READY SCHEMA  — each card becomes a dashboard component
# =============================================================================

class CallRef(BaseModel):
    call_id: int = Field(description="The call this evidence comes from.")
    date: str = Field(description="The call date.")
    quote: str = Field(description="Verbatim words from that call supporting the claim.")


class HoldingRef(BaseModel):
    ticker: str
    note: str = Field(description="Why this holding matters here, e.g. weight / exposure.")


class NewsRef(BaseModel):
    source: str
    date: str
    headline: str = Field(description="A short headline summarising the matched article.")


class Provenance(BaseModel):
    """Where every claim on a card traces to. Empty lists where not applicable."""
    calls: list[CallRef]
    holdings: list[HoldingRef]
    news: list[NewsRef]


class InsightCard(BaseModel):
    """One self-contained insight + recommended action, with full provenance."""
    type: Literal[
        "collision", "risk_drift", "open_commitment", "inferred_insight",
        "emotional_read", "opportunity",
    ]
    headline: str = Field(description="One punchy line an RM reads at a glance.")
    narrative: str = Field(description="2-4 sentences: the connection and why it matters now.")
    recommended_action: str = Field(description="The concrete next step for the RM.")
    urgency: Literal["high", "medium", "low"]
    provenance: Provenance


class TopicWithReason(BaseModel):
    topic: str
    why: str = Field(description="Why this will/should come up, grounded in the evidence.")


class OpenCommitmentCard(BaseModel):
    commitment: str = Field(description="What the RM promised.")
    made_on_date: str
    call_id: int
    status: str = Field(description="e.g. 'still open — re-raised by the client this call'.")
    evidence: str = Field(description="The client/RM words showing it is unresolved.")


class Conflict(BaseModel):
    description: str = Field(description="e.g. declared 'moderate' vs conservative behaviour.")
    evidence: str


class EmotionalRead(BaseModel):
    significant: bool
    one_line: str = Field(description="The human read in one sentence, hedged appropriately.")
    reasons: list[str]
    dominant_emotions: list[str]


class PostCallBrief(BaseModel):
    """The RM-facing pre-brief, organised by insight — what the UI renders."""
    client_name: str
    generated_for_call_id: int
    headline_insights: list[InsightCard] = Field(
        description="The hero cards, most important first: collisions, drift, open commitments, inferred insights."
    )
    open_commitments: list[OpenCommitmentCard]
    predicted_client_topics: list[TopicWithReason] = Field(
        description="What the client is likely to raise next, grounded in the evidence."
    )
    rm_should_raise: list[TopicWithReason] = Field(
        description="What the RM should proactively raise (incl. holdings/news the client did NOT mention)."
    )
    conflicts: list[Conflict]
    emotional_read: EmotionalRead


SYSTEM_PROMPT = """
You are the senior intelligence analyst behind a Julius Baer relationship manager's
pre-call brief. You receive a deterministic EVIDENCE PACKET that has ALREADY made the
hard connections: portfolio weights, holding x news x call-worry COLLISIONS, OPEN
COMMITMENTS from prior calls, the risk-drift story, and the latest call's insights.

Your job is to turn it into a presentation-ready brief, ORGANISED BY INSIGHT AND
ACTION — never by data source. Do NOT produce "portfolio summary / news summary /
call summary"; produce connected insights, each with a recommended action.

HARD RULES:
- Use ONLY connections present in the packet. NEVER invent a holding, a news item, or
  a collision. The packet's `collisions` and `open_commitments` are ground truth.
- Every card's provenance MUST cite real ids/quotes from the packet: call_id + a
  verbatim quote, holding tickers, news source+date. If you can't ground it, drop it.
- Hedge inferred material: for the packet's `inferred_insights`, write "the client
  appears to / signals" — not hard fact. State stated facts plainly.
- The risk-drift card is a hero: name the declared profile, then quantify the drift
  using risk.shift_from_onboarding (onboarding score -> inferred score, the delta) and
  risk.trend (the trajectory direction over the conversation series), with the strongest
  quoted drift signal.
- Lead headline_insights with the strongest collision, the risk drift, and any open
  commitment — these are the moments a human RM could not easily assemble.
- emotional_read proves the system reads the human; keep one_line tactful.
- predicted_client_topics = what the CLIENT will likely raise next; rm_should_raise =
  what the RM should proactively bring (including holdings/news the client did NOT
  mention this call, e.g. a flagged collision).

Be specific, concrete, and confident where the evidence is hard; hedged where it is
inferred. This brief is the product.
"""


def synthesize(packet: dict) -> dict:
    """Turn the deterministic evidence packet into a presentation-ready brief.

    The LLM explains the precomputed connections; it cannot invent matches. Returns
    the validated PostCallBrief as a dict.
    """
    user_content = (
        "EVIDENCE PACKET (ground truth — explain it, do not add to it):\n\n"
        + json.dumps(packet, indent=2, ensure_ascii=False, default=str)
    )

    try:
        completion = _client.beta.chat.completions.parse(
            model=SYNTHESIS_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0,
            response_format=PostCallBrief,
        )
    except Exception as e:
        raise ExtractionError(f"Synthesis request failed: {e}") from e

    choice = completion.choices[0]
    message = choice.message
    if getattr(message, "refusal", None):
        raise ExtractionError(f"Synthesis refused: {message.refusal}")
    if choice.finish_reason == "length":
        raise ExtractionError("Synthesis was truncated (hit the token limit).")
    if message.parsed is None:
        raise ExtractionError(
            f"Synthesis returned no parseable output (finish_reason={choice.finish_reason})."
        )

    return message.parsed.model_dump()


def build_brief(customer_id: int = 1) -> dict:
    """Convenience: assemble the deterministic packet, then synthesise the brief.

    Assumes the latest call (and past calls, for open-commitment detection) already
    have stored insights — run extraction/backfill first.
    """
    packet = retrieval.build_evidence_packet(customer_id=customer_id)
    return synthesize(packet)
