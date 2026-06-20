"""
================================================================================
RM INTELLIGENCE PLATFORM  -  POST-CALL EXTRACTION LAYER
SwissHack / Julius Bär Challenge
================================================================================

This module is the EXTRACTION layer of the post-call pipeline. It takes the
*last* conversation transcript (the most recent call, the one that still has no
risk assessment / sentiment / summary) and uses the LLM to extract a compact
set of structured features that power the post-call dashboard widgets.

Features extracted from the transcript (and only the transcript):
    1. summary            - a short ~3-line summary of the most important facts.
    2. sentiment          - a mood timeline: for each fact the client reacts to,
                            where it occurs in the conversation, whether it is a
                            concern or excitement, and which category it belongs
                            to (personal / market / opinion on Julius Bär).
    3. risk               - an inferred risk score (1-10) measuring KYC drift vs
                            the client's declared/last-known risk profile.
    4. important_facts /  - the salient facts, turned into prioritised action
       action_items         items for the Relationship Manager.
    5. relevant_market_news - market news connected to the financial facts the
                            client mentioned (retrieved from the news store, NOT
                            invented by the model).

DESIGN NOTE:
    the LLM never touches the database. It reasons only on the transcript
    text we hand it (plus the client's declared risk profile, for drift). The
    market-news step is deterministic retrieval over the financial topics the
    model surfaced.
================================================================================
"""

import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

from src.data import db

# Load OPENAI_API_KEY (and any other settings) from the project-root .env so the
# client below works whether or not the caller already exported the variable.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env")

# Single shared client; key comes from the environment (never hardcode it).
_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# The extraction is judgment-heavy (drift detection, salience, convergent inference),
# so it runs on a strong general model rather than a mini tier.
EXTRACTION_MODEL = "gpt-4.1"


class ExtractionError(Exception):
    """Raised when GPT extraction fails or returns no usable structured output."""
    pass


# =============================================================================
# PYDANTIC SCHEMA - the contract the LLM MUST fill
# =============================================================================
# These models are handed to the OpenAI structured-outputs API. The model is
# constrained to emit JSON that validates against this schema, so we never parse
# free-form text or guess at missing keys.

# A fact is always one of three kinds: about the client's life, about markets,
# or the client's opinion of Julius Baer.
Category = Literal["personal", "market", "julius_baer"]


class MoodPoint(BaseModel):
    """One point on the sentiment timeline: a fact the client reacted to."""
    position: float = Field(description="Relative location in the call, 0.0 (start) to 1.0 (end).")
    fact: str = Field(description="The fact the client is reacting to.")
    reaction: Literal["concern", "excitement", "neutral"]
    intensity: Literal["high", "medium", "low"]
    category: Category
    related_holdings: list[str] = Field(
        description="Held tickers FROM THE PROVIDED PORTFOLIO this reaction concerns; empty list if none."
    )
    quote: str = Field(description="Exact client sentence (or the closest supporting span if inferred).")


class MoodTrajectory(BaseModel):
    """How the client's mood moved across the call (start vs end)."""
    start: Literal["negative", "neutral", "positive"]
    end: Literal["negative", "neutral", "positive"]
    note: str = Field(description="What shifted the mood between start and end.")


class EmotionalSignificance(BaseModel):
    """Whether this was an emotionally significant call, and why — the human read."""
    significant: bool = Field(description="True if the call carried real emotional weight.")
    reasons: list[str] = Field(
        description="Short reasons, e.g. 'grief over a friend', 'market anxiety', 'relationship grievance'."
    )
    dominant_emotions: list[str] = Field(description="The strongest emotions present, e.g. ['grief','anxiety'].")


class Sentiment(BaseModel):
    overall_label: Literal["negative", "neutral", "positive"]
    overall_score: float = Field(
        description="Concern-weighted mood in [-1.0, 1.0]: unresolved anxiety outweighs a polite close. Internal/trend use only."
    )
    emotional_significance: EmotionalSignificance
    trajectory: MoodTrajectory
    mood_timeline: list[MoodPoint] = Field(description="Mood points ordered by position.")


class DriftSignal(BaseModel):
    """A single piece of evidence for (or against) risk-appetite drift."""
    signal: str = Field(description="The drift signal observed, e.g. 'demand for uncorrelated assets'.")
    quote: str = Field(description="The exact client words evidencing it.")


class Risk(BaseModel):
    declared_risk_appetite: str = Field(description="Echo of the declared profile provided.")
    inferred_risk_appetite: Literal["conservative", "moderate", "aggressive"]
    inferred_risk_score: float = Field(description="Float in [1.0, 10.0]; higher = more risk-seeking.")
    kyc_drift: Literal["increasing", "stable", "decreasing"]
    drift_signals: list[DriftSignal] = Field(
        description="Evidence behind the drift judgement; empty list only if genuinely none."
    )
    drift_explanation: str = Field(
        description="Always justify the drift verdict, including why it is 'stable' when it is."
    )


class ImportantFact(BaseModel):
    fact: str = Field(description="A salient fact the RM must act on.")
    category: Category
    priority: Literal["high", "medium", "low"]
    related_holdings: list[str] = Field(
        description="Tickers FROM THE PROVIDED PORTFOLIO this fact concerns (e.g. a tech worry -> "
                    "['AAPL','MSFT','ASML']). Only real held tickers; empty list if none."
    )


class InferredInsight(BaseModel):
    """A clearly-marked inference drawn from CONVERGENT signals, not any single line."""
    insight: str = Field(description="The inference, e.g. 'a mortality/legacy reframing of his priorities'.")
    category: Category
    supporting_quotes: list[str] = Field(
        description="Two or more exact quotes whose convergence supports the inference."
    )
    confidence: Literal["high", "medium", "low"]


class ActionItem(BaseModel):
    action: str = Field(description="Concrete next step for the RM.")
    urgency: Literal["high", "medium", "low"]
    based_on: str = Field(description="The important fact this action follows from.")


class RMProposal(BaseModel):
    """Something the RM offered or committed to during the call."""
    proposal: str = Field(description="What the RM proposed or promised to prepare/do.")
    financial_topics: list[str] = Field(
        description="Clean financial concepts/assets/sectors this proposal concerns, for news retrieval."
    )


class CallExtraction(BaseModel):
    """The full structured feature set extracted from one call transcript."""
    summary: str = Field(description="~3 short sentences covering the most important facts.")
    sentiment: Sentiment
    risk: Risk
    important_facts: list[ImportantFact]
    inferred_insights: list[InferredInsight] = Field(
        description="Convergent-signal inferences no single line states; clearly marked, with quotes."
    )
    action_items: list[ActionItem]
    rm_proposals: list[RMProposal] = Field(
        description="What the RM offered/committed to; news is also tailored to these."
    )
    financial_topics: list[str] = Field(
        description="Clean financial concepts/assets/sectors the client raised, for news retrieval."
    )


# =============================================================================
# STEP 1 - THE EXTRACTION PROMPT
# =============================================================================
# Every key in the JSON maps to a dashboard widget. The model only ever sees the
# transcript and the client's declared risk profile, so it cannot leak history
# it was not given.

SYSTEM_PROMPT = """
You are a financial relationship manager assistant at Julius Baer, a Swiss private
wealth bank serving High Net Worth Individuals.

You receive the transcript of a single call between a Relationship Manager (RM)
and a client, the client's declared (last-known) risk profile, the client's recent
risk-score trajectory, and the client's CURRENT PORTFOLIO HOLDINGS. Extract the
structured features below from the TRANSCRIPT. For sentiment and facts, reason about
the CLIENT's words; for rm_proposals, capture what the RM offered. Never invent facts
not in the text.

CATEGORIES — classify every fact into exactly one:
  - "personal"     : the client's life, family, legacy, liquidity needs, health, plans.
  - "market"       : markets, assets, sectors, the economy, geopolitics, returns.
  - "julius_baer"  : the client's opinion about Julius Baer, the RM, or the service.

RISK & DRIFT — this is the highest-value output. Actively hunt for signals that the
client's true risk appetite is drifting from the declared profile, especially toward
capital preservation / defensiveness:
  - preservation / defensive language ("stability", "preserve capital", "sleep at night");
  - hedging or downside protection (e.g. wanting gold as a hedge);
  - anxiety about losses, drawdowns, or uncertainty;
  - demand for uncorrelated, low-volatility, stable, or liquid assets;
  - de-risking requests or reducing exposure;
  - life-stage cues (ageing, legacy, slowing down).
  Populate drift_signals with each signal and its quote. Set kyc_drift accordingly
  (toward conservative => "decreasing" risk). ALWAYS write drift_explanation with the
  evidence — including a brief justification when you conclude "stable".

SENTIMENT — overall_score is CONCERN-WEIGHTED (internal only): weight unresolved worries
and anxiety ABOVE polite or upbeat closings. Use trajectory (start/end + note) for the
mood arc. mood_timeline has one entry per fact the client reacts to, ordered by position
(0.0 = call start .. 1.0 = call end). Also fill emotional_significance: flag whether the
call carried real emotional weight and WHY (e.g. grief, market anxiety, a relationship
grievance) — this is the human read, and it matters even when the call ended warmly.

HOLDINGS GROUNDING — for each important_fact AND each mood_timeline point, set
related_holdings to the tickers FROM THE PROVIDED PORTFOLIO it concerns (e.g. a worry
about "tech concentration" or "the Dutch chip company" -> the held tech tickers). Use
ONLY tickers that appear in the provided holdings; never invent one. Empty list when it
concerns no holding.

INFERRED INSIGHTS — beyond per-fact tagging, surface inferred_insights: conclusions drawn
from the CONVERGENCE of multiple signals that no single line states (e.g. a new grandchild
+ recovering from surgery + losing a close friend + "a year that makes a man take stock"
=> a mortality/legacy reframing of his priorities). Each needs two or more supporting
quotes and a confidence. These are valuable; surface them when genuinely supported.

RM_PROPOSALS — capture what the RM offered or committed to prepare/do, each with the
financial_topics it concerns, so news can be tailored to the RM's follow-ups.

Other fields:
  - summary          : ~3 short sentences covering the most important facts.
  - important_facts  : the salient facts the RM must act on, with priority.
  - action_items     : concrete next steps for the RM, each tied to a fact.
  - financial_topics : clean financial concepts/assets/sectors the CLIENT raised.

Rules:
- "inferred_risk_score" is a float in [1.0, 10.0]; calibrate it against the supplied
  risk trajectory (continue the trend unless the call clearly breaks it).
- If a section has no data, return an empty list. Never invent facts. Keep quotes exact.
"""


def extract_features(
    transcript: str,
    declared_risk_appetite: str | None = None,
    risk_trajectory: str | None = None,
    holdings: str | None = None,
) -> CallExtraction:
    """Single LLM call: transcript -> validated CallExtraction.

    Uses OpenAI structured outputs with the Pydantic schema, so the response is
    guaranteed to validate against CallExtraction (no manual JSON parsing).

    transcript             : the last call's transcript text.
    declared_risk_appetite : the client's declared (KYC) risk profile, the baseline
                             drift is measured against. Optional.
    risk_trajectory        : compact recent risk-score history (e.g. dates ->
                             score/appetite) used to calibrate the inferred score.
                             Optional.
    holdings               : compact current portfolio (ticker/sector lines) so the
                             model can ground related_holdings to real positions.
                             Optional.
    """
    user_content = f"""
=== CLIENT DECLARED RISK PROFILE (KYC baseline) ===
{declared_risk_appetite or "unknown"}

=== RECENT RISK TRAJECTORY ===
{risk_trajectory or "not provided"}

=== CURRENT PORTFOLIO HOLDINGS ===
{holdings or "not provided"}

=== CALL TRANSCRIPT ===
{transcript}
"""

    if not (transcript or "").strip():
        raise ExtractionError("Empty transcript: nothing to extract.")

    try:
        completion = _client.beta.chat.completions.parse(
            model=EXTRACTION_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0,
            response_format=CallExtraction,
        )
    except Exception as e:
        # Network / auth / rate-limit / SSL failures from the API call.
        raise ExtractionError(f"GPT extraction request failed: {e}") from e

    choice = completion.choices[0]
    message = choice.message

    # Model declined to answer.
    if getattr(message, "refusal", None):
        raise ExtractionError(f"GPT refused to extract: {message.refusal}")

    # Output was cut off before a complete object could be produced.
    if choice.finish_reason == "length":
        raise ExtractionError(
            "GPT extraction was truncated (hit the token limit) before producing "
            "a complete result."
        )

    # Parsing/validation against the schema yielded nothing usable.
    if message.parsed is None:
        raise ExtractionError(
            f"GPT returned no parseable structured output (finish_reason="
            f"{choice.finish_reason})."
        )

    return message.parsed


# =============================================================================
# STEP 2 - CONNECT TOPICS TO REAL MARKET NEWS (deterministic retrieval)
# =============================================================================
# The model surfaces the financial topics (client-raised + RM-proposal); we ground
# them by retrieving real articles from the news store. Relevance is decided
# deterministically by the embedding search, never invented by the LLM.
#
# NOTE: this topic-keyed retrieval feeds the per-call `relevant_market_news`. The
# higher-value PORTFOLIO-keyed matching (holdings x news x call-worry collisions)
# lives in retrieval.py, which keys off db.get_news_by_ticker() against real holdings.


def _expand_query(topic: str) -> str:
    """Expand a bare topic into a fuller query phrase.

    Short keywords ("gold") embed poorly against full news sentences (the low
    0.3-0.4 cosine scores we saw). A descriptive phrase aligns the query with the
    document style and lifts similarity.
    """
    topic = topic.strip()
    return f"Market news and outlook relevant to a private wealth client regarding {topic}."


def fetch_related_news(topics: list[str], per_topic: int = 2) -> list[dict]:
    """Retrieve market news connected to the given financial topics.

    `topics` is the union of client-raised topics and RM-proposal topics. Each is
    expanded into a descriptive query, searched semantically, and deduped by
    article text. Returns a flat list of {topic, document, metadata,
    similarity_score}. Degrades to an empty list if the news store is unavailable
    (never blocks extraction).
    """
    seen: set[str] = set()
    results: list[dict] = []

    for topic in topics or []:
        topic = (topic or "").strip()
        if not topic:
            continue
        try:
            hits = db.search_news(_expand_query(topic), top_k=per_topic)
        except Exception:
            # News retrieval is best-effort; a failure must not break the call.
            continue
        for hit in hits:
            doc = hit.get("document", "")
            if doc in seen:
                continue
            seen.add(doc)
            results.append({
                "topic": topic,
                "document": doc,
                "metadata": hit.get("metadata", {}),
                "similarity_score": hit.get("similarity_score"),
            })

    return results


# =============================================================================
# STEP 3 - PUBLIC ENTRY POINTS
# =============================================================================

def _format_risk_trajectory(history: list[dict]) -> str:
    """Render risk-history snapshots as a compact line series for the prompt.

    e.g. "2019-03-15: 6.0 (moderate); 2025-11-10: 4.5 (conservative)". Returns a
    'no history' note if empty so the model knows the baseline is missing.
    """
    if not history:
        return "no prior risk history available"
    parts = []
    for snap in history:
        date = snap.get("assessed_date", "?")
        score = snap.get("risk_score")
        appetite = snap.get("risk_appetite", "?")
        score_str = f"{score}" if score is not None else "n/a"
        parts.append(f"{date}: {score_str} ({appetite})")
    return "; ".join(parts)


def _shift_from_onboarding(history: list[dict], inferred_score: float | None) -> dict:
    """Risk shift vs the ONBOARDING baseline: a signed delta + direction.

    Deterministic point-in-time metric (this call vs onboarding). Returns an empty
    dict if either endpoint is missing.
    """
    onboarding = next((h for h in history if h.get("source") == "onboarding"),
                      history[0] if history else None)
    if not onboarding or onboarding.get("risk_score") is None or inferred_score is None:
        return {}
    ob = onboarding["risk_score"]
    delta = round(inferred_score - ob, 2)
    direction = "more conservative" if delta < 0 else "more aggressive" if delta > 0 else "unchanged"
    return {
        "onboarding_score": ob,
        "onboarding_date": onboarding.get("assessed_date"),
        "current_inferred_score": inferred_score,
        "delta": delta,
        "direction": direction,
    }


def _news_topics(features: CallExtraction) -> list[str]:
    """Union of client-raised topics and RM-proposal topics (deduped, ordered)."""
    topics: list[str] = list(features.financial_topics or [])
    for proposal in features.rm_proposals or []:
        topics.extend(proposal.financial_topics or [])
    # Dedup case-insensitively while preserving first-seen order.
    seen: set[str] = set()
    ordered: list[str] = []
    for t in topics:
        key = (t or "").strip().lower()
        if key and key not in seen:
            seen.add(key)
            ordered.append(t.strip())
    return ordered


def _format_holdings(portfolio: list[dict]) -> str:
    """Render portfolio rows as compact ticker/sector lines for the prompt."""
    if not portfolio:
        return "no holdings provided"
    return "; ".join(
        f"{p.get('ticker')} ({p.get('sector', 'n/a')})" for p in portfolio if p.get("ticker")
    )


def extract_facts(
    transcript: str,
    declared_risk_appetite: str | None = None,
    risk_trajectory: str | None = None,
    holdings: str | None = None,
) -> dict:
    """Full extraction bundle for one transcript.

    Combines the LLM feature extraction with the retrieved market news (matched to
    both client-raised topics and the RM's proposals), returning the complete
    bundle that feeds the dashboard.
    """
    features = extract_features(transcript, declared_risk_appetite, risk_trajectory, holdings)
    bundle = features.model_dump()
    bundle["relevant_market_news"] = fetch_related_news(_news_topics(features))
    return bundle


def extract_and_store(
    call_id: int | None = None,
    customer_id: int = 1,
    store_trend_columns: bool = True,
) -> dict:
    """Run extraction on a client's last (unanalysed) call and persist the result.

    Pulls the most recent call for the customer, reads the official declared risk
    profile from the customer record (the KYC baseline drift is measured against)
    plus the recent risk-score trajectory (to calibrate the inferred point),
    extracts the features + news, and caches everything onto the call row via
    save_call_insights (also filling the derived trend columns).

    Returns the extraction bundle.
    """
    # Resolve the target call: explicit id, else the most recent one.
    if call_id is None:
        calls = db.get_calls(customer_id=customer_id, limit=1)
        if not calls:
            raise db.DataLayerError(f"No calls found for customer {customer_id}")
        call_id = calls[0]["id"]

    call = db.get_call(call_id)
    if not call:
        raise db.DataLayerError(f"No call with id {call_id}")
    transcript = call.get("transcript") or ""

    # Official declared (KYC) risk profile — the baseline drift is measured
    # against. This is the stated profile on the customer record, not the
    # behavioural risk-history trend.
    profile = db.get_customer_profile()
    declared_risk = profile.get("risk_appetite")

    # Recent risk-score trajectory (onboarding -> t-1) calibrates the inferred
    # point and gives the drift judgement a baseline trend to continue or break.
    history = db.get_risk_history(customer_id=customer_id)
    risk_trajectory = _format_risk_trajectory(history)

    # Current holdings ground related_holdings to real positions.
    holdings = _format_holdings(db.get_portfolio())

    bundle = extract_facts(transcript, declared_risk, risk_trajectory, holdings)

    # Derived trend columns from the extraction.
    sentiment = bundle.get("sentiment") or {}
    risk = bundle.get("risk") or {}
    # Deduped topics actually matched to news (fall back to all client topics).
    matched = [t.get("topic") for t in bundle.get("relevant_market_news", []) if t.get("topic")]
    topics = list(dict.fromkeys(matched)) or bundle.get("financial_topics", [])

    # METRIC (extraction-side): how far the client's inferred risk has shifted from
    # the ONBOARDING baseline. Computed deterministically so it is exact, and stored
    # inside the bundle so it travels with the call's insights.
    bundle["risk"]["shift_from_onboarding"] = _shift_from_onboarding(
        history, risk.get("inferred_risk_score")
    )

    if store_trend_columns:
        # The "last call" the pipeline is analysing: fill the NULL trend columns,
        # AND write the inferred risk point into the canonical series so the risk
        # time-series is complete in one place (risk_profile_history).
        db.save_call_insights(
            call_id,
            bundle,
            summary=bundle.get("summary"),
            sentiment_score=sentiment.get("overall_score"),
            sentiment_label=sentiment.get("overall_label"),
            risk_signal=risk.get("inferred_risk_appetite"),
            topics=topics,
        )
        if risk.get("inferred_risk_score") is not None and risk.get("inferred_risk_appetite"):
            db.upsert_risk_snapshot(
                customer_id,
                (call.get("call_date") or "")[:10],
                risk["inferred_risk_appetite"],
                risk["inferred_risk_score"],
                source="call",
                note="Pipeline-inferred from the last call.",
            )
    else:
        # Backfilling a PAST call: add insights_json only, preserve the curated
        # summary/sentiment/risk_signal/topics that drive the trend charts.
        db.save_call_insights(call_id, bundle)

    return bundle


# =============================================================================
# EXAMPLE / MANUAL TEST
# =============================================================================

if __name__ == "__main__":

    test_transcript = """
    Client: I have to be honest, I'm quite worried about my portfolio after
    last quarter. The returns were disappointing and I expected more from
    Julius Bär. I also keep reading about tensions in Asia and it makes me
    nervous about my exposure there. By the way, I really should start thinking
    about how to pass some of this on to my daughter one day.
    RM: I understand your concerns, let me walk you through what happened...
    Client: Okay, that actually makes me feel a bit better about the bond side.
    """

    # Pure extraction (no DB/news needed):
    result = extract_features(
        test_transcript,
        declared_risk_appetite="moderate",
        risk_trajectory="2019-03-15: 6.0 (moderate); 2025-11-10: 4.5 (conservative)",
    )
    print(result.model_dump_json(indent=2))
