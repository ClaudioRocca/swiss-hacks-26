"""Post-call analysis engine.

Accepts the full call context (transcript, concepts with executed queries,
customer profile) and returns a structured report via OpenAI structured outputs.

IMPORTANT: This module does NOT produce financial advice. It presents
factual observations from the call data to help the relationship manager
understand the client's situation and detect risk profile shifts.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
from openai import AsyncOpenAI

_MODEL = os.getenv("POSTCALL_MODEL") or os.getenv("AGENT_MODEL") or "gpt-4.1"

# ---------------------------------------------------------------------------
# Structured output schema — defines the exact JSON the LLM must return.
# ---------------------------------------------------------------------------

POST_CALL_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {
            "type": "string",
            "description": (
                "3-4 sentence executive summary of the call. Focus on key client "
                "requests, discussed topics, and decisions made. Do NOT include "
                "financial advice or recommendations."
            ),
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "3-6 topic hashtags summarizing the call themes (e.g. #Gold, #RealEstate).",
        },
        "sentiment": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "overall_score": {
                    "type": "integer",
                    "description": "0-100 score of overall client sentiment. 100 = very positive, 0 = very negative.",
                },
                "overall_label": {
                    "type": "string",
                    "description": "One-word label: Positive, Neutral, or Concerned.",
                },
                "bands": {
                    "type": "array",
                    "description": (
                        "Sentiment curve data points across the call duration. "
                        "Provide 8-12 evenly spaced points. Each score MUST be a "
                        "multiple of 10 (0, 10, 20, ... 90, 100). "
                        "0 = very negative/guarded, 50 = neutral, 100 = very positive/receptive."
                    ),
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "at_percent": {
                                "type": "number",
                                "description": "Position as percentage of call duration (0-100).",
                            },
                            "score": {
                                "type": "integer",
                                "description": (
                                    "Sentiment score at this point. MUST be a multiple of 10 "
                                    "(0, 10, 20, 30, 40, 50, 60, 70, 80, 90, or 100). "
                                    "50 = neutral, above = positive/receptive, below = guarded/concerned."
                                ),
                            },
                        },
                        "required": ["at_percent", "score"],
                    },
                },
                "peaks": {
                    "type": "array",
                    "description": "Notable sentiment moments during the call (3-5 peaks).",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "at_percent": {
                                "type": "number",
                                "description": "Position as percentage of total call duration.",
                            },
                            "label": {
                                "type": "string",
                                "description": "Short description of what caused this sentiment shift.",
                            },
                            "tone": {
                                "type": "string",
                                "enum": ["positive", "neutral", "concerned"],
                            },
                        },
                        "required": ["at_percent", "label", "tone"],
                    },
                },
            },
            "required": ["overall_score", "overall_label", "bands", "peaks"],
        },
        "emotional_topics": {
            "type": "array",
            "description": (
                "Topics that evoked strong emotions from the client. Include exact "
                "or near-exact quotes from the transcript. Do NOT add interpretive "
                "financial advice — just report what the client expressed."
            ),
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "emotion": {
                        "type": "string",
                        "enum": ["fear", "joy", "concern", "confidence", "frustration"],
                    },
                    "topic": {
                        "type": "string",
                        "description": "The topic that triggered the emotion (2-5 words).",
                    },
                    "quote": {
                        "type": "string",
                        "description": "Exact or near-exact quote from the client in the transcript.",
                    },
                    "explanation": {
                        "type": "string",
                        "description": (
                            "Brief factual explanation of context. Do NOT advise — "
                            "only describe what was observed."
                        ),
                    },
                },
                "required": ["emotion", "topic", "quote", "explanation"],
            },
        },
        "risk_tolerance": {
            "type": "object",
            "additionalProperties": False,
            "description": (
                "Comparison between the client's known risk profile (from KYC/records) "
                "and the risk appetite detected in this conversation. This helps the RM "
                "spot shifts — it is NOT a recommendation to change anything."
            ),
            "properties": {
                "known_profile": {
                    "type": "string",
                    "enum": ["conservative", "moderate", "aggressive"],
                    "description": "The client's risk profile as recorded in bank systems.",
                },
                "detected_appetite": {
                    "type": "string",
                    "enum": ["conservative", "moderate", "aggressive"],
                    "description": "Risk appetite inferred from the conversation tone and requests.",
                },
                "shift_detected": {
                    "type": "boolean",
                    "description": "True if detected appetite differs from known profile.",
                },
                "evidence": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Factual evidence from the call supporting the detected appetite. "
                        "Quote the client or reference specific requests. 2-4 items."
                    ),
                },
                "comparison_notes": {
                    "type": "string",
                    "description": (
                        "Objective comparison between known profile and detected appetite. "
                        "State facts only — no advice, no recommendations."
                    ),
                },
            },
            "required": [
                "known_profile",
                "detected_appetite",
                "shift_detected",
                "evidence",
                "comparison_notes",
            ],
        },
        "action_items": {
            "type": "array",
            "description": "Follow-up actions identified from the call. Factual next steps only.",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "priority": {
                        "type": "string",
                        "enum": ["HIGH", "MED", "LOW"],
                    },
                    "text": {"type": "string"},
                    "due_suggestion": {
                        "type": "string",
                        "description": "Suggested timeframe (e.g. 'Within 1 week', 'End of month').",
                    },
                },
                "required": ["priority", "text", "due_suggestion"],
            },
        },
    },
    "required": [
        "summary",
        "tags",
        "sentiment",
        "emotional_topics",
        "risk_tolerance",
        "action_items",
    ],
}

# ---------------------------------------------------------------------------
# System prompt — anchors the AI to factual reporting, no advice.
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a post-call analysis engine for a private banking relationship manager (RM) tool.

YOUR ROLE: Extract and present factual observations from a client phone call. You help the RM quickly digest what was discussed and spot changes in client behavior.

CRITICAL RULES:
- You MUST NOT provide financial advice, investment recommendations, or suggest actions the client should take.
- You MUST NOT interpret market conditions or predict outcomes.
- You present DATA. You report OBSERVATIONS. You quote the CLIENT.
- Sentiment analysis must reflect what the client expressed, not what you think they should feel.
- Risk tolerance detection compares the client's STATED preferences and requests in the call against their KNOWN profile from bank records. Report the gap factually.
- Quotes must be exact or near-exact from the transcript — never fabricate.
- Action items are things the RM mentioned they would do, or the client explicitly requested. Not your suggestions.

CONTEXT PROVIDED:
1. Customer Profile — the client's known risk profile, investment horizon, and preferences from bank records.
2. Portfolio & Market Data — structured data retrieved during the call about the client's positions and market movements.
3. News Context — relevant market news that was surfaced during the call.
4. Full Transcript — the complete speaker-labeled conversation.
5. Concept Summaries — AI-extracted topics with their associated data.

Use ALL of this context to produce a comprehensive, factual post-call report.\
"""


# ---------------------------------------------------------------------------
# Core analysis function
# ---------------------------------------------------------------------------


def _format_transcript(transcript_lines: list[dict]) -> str:
    """Format transcript lines into a readable speaker-labeled string."""
    lines = []
    for line in transcript_lines:
        speaker = "RM" if line.get("speaker") == "rm" else "Client"
        lines.append(f"{speaker}: {line['text']}")
    return "\n".join(lines)


def _format_concepts(concepts: list[dict]) -> str:
    """Format concepts with their executed query results."""
    parts = []
    for c in concepts:
        part = f"### Topic: {c.get('topic', 'Unknown')}\n"
        part += f"Intent: {c.get('intent', '')}\n"
        part += f"Entities: {', '.join(c.get('entities', []))}\n"

        # Include executed query results
        for eq in c.get("executed_queries", []):
            if eq.get("error"):
                continue
            source = eq.get("source", "")
            results = eq.get("results")
            if results:
                part += f"\n[Data from {source}]:\n"
                if isinstance(results, list):
                    # Truncate large result sets
                    display = results[:10]
                    part += json.dumps(display, indent=2, default=str)
                    if len(results) > 10:
                        part += f"\n... ({len(results)} total rows)"
                elif isinstance(results, dict):
                    part += json.dumps(results, indent=2, default=str)
                part += "\n"
        parts.append(part)
    return "\n---\n".join(parts)


def _build_user_message(
    transcript_lines: list[dict],
    concepts: list[dict],
    customer_profile: dict,
) -> str:
    """Compose the user message with all call context."""
    sections = []

    # Customer profile
    sections.append("## Customer Profile (from bank records)")
    profile_display = {
        k: v
        for k, v in customer_profile.items()
        if k != "id"
    }
    sections.append(json.dumps(profile_display, indent=2))

    # Concepts with data
    sections.append("\n## Topics Discussed & Retrieved Data")
    sections.append(_format_concepts(concepts))

    # Full transcript
    sections.append("\n## Full Call Transcript")
    sections.append(_format_transcript(transcript_lines))

    sections.append(
        "\n## Instructions\n"
        "Produce the structured post-call report based on all the above context. "
        "Remember: factual observations only, no advice."
    )

    return "\n".join(sections)


async def generate_post_call_analysis(
    transcript_lines: list[dict],
    concepts: list[dict],
    customer_profile: dict,
) -> dict[str, Any]:
    """Generate the post-call analysis using OpenAI structured outputs.

    Returns the parsed JSON matching POST_CALL_SCHEMA.
    Raises on API errors.
    """
    client = AsyncOpenAI(http_client=httpx.AsyncClient(verify=False))

    user_message = _build_user_message(transcript_lines, concepts, customer_profile)

    response = await client.chat.completions.create(
        model=_MODEL,
        temperature=0,
        seed=42,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "post_call_analysis",
                "strict": True,
                "schema": POST_CALL_SCHEMA,
            },
        },
    )

    content = response.choices[0].message.content
    return json.loads(content)
