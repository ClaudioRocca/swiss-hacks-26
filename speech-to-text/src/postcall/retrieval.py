"""
================================================================================
RM INTELLIGENCE PLATFORM  -  POST-CALL RETRIEVAL LAYER (deterministic)
SwissHack / Julius Bär Challenge
================================================================================

This layer is PURE, DETERMINISTIC CODE — no LLM. For now it assembles ONE thing:
the client's RISK-PROFILE TREND over the relationship.

The trend is the chartable risk-score series:
  - the ONBOARDING starting point, plus
  - one mocked, as-if-LLM-extracted risk point per PAST conversation, plus
  - the LAST call's risk point, which the extraction layer infers live and writes
    into risk_profile_history (so the series is complete in one place).

All of these live in risk_profile_history; this layer just reads that canonical
series and computes the first->last trend metric over it. The synthesis layer is
intentionally out of scope right now.
================================================================================
"""

from src.data import db


# =============================================================================
# RISK TREND  — the chartable series + a first->last trend metric
# =============================================================================

def _risk_trend(series: list[dict]) -> dict:
    """METRIC: the risk shift as a TREND over the whole conversation series.

    Computed deterministically from the chartable series (onboarding -> past calls
    -> inferred last point). Reports first->last delta, direction, and per-step
    deltas. Empty dict if fewer than two scored points.
    """
    pts = [(s["date"], s["score"]) for s in series if s.get("score") is not None]
    if len(pts) < 2:
        return {}
    first, last = pts[0][1], pts[-1][1]
    delta = round(last - first, 2)
    direction = (
        "decreasing (more conservative)" if delta < 0
        else "increasing (more risk-seeking)" if delta > 0
        else "flat"
    )
    return {
        "from_date": pts[0][0], "from_score": first,
        "to_date": pts[-1][0], "to_score": last,
        "total_delta": delta,
        "direction": direction,
        "n_points": len(pts),
        "per_step_deltas": [round(pts[i + 1][1] - pts[i][1], 2) for i in range(len(pts) - 1)],
    }


def build_risk_trend(customer_id: int = 1) -> dict:
    """Assemble the client's risk-profile trend.

    Reads the canonical risk_profile_history series (onboarding -> past calls ->
    inferred last point) and computes the trend over it. Run extraction on the last
    call FIRST so the inferred t point is already merged into the series.

    Returns the single risk object the UI/chart consumes — no stitching needed.
    """
    profile = db.get_customer_profile()
    history = db.get_risk_history(customer_id=customer_id)

    series = [
        {"date": h.get("assessed_date"), "score": h.get("risk_score"),
         "appetite": h.get("risk_appetite"), "source": h.get("source"), "note": h.get("note")}
        for h in history
    ]

    onboarding = next((s for s in series if s.get("source") == "onboarding"),
                      series[0] if series else None)
    last_point = series[-1] if series else None

    return {
        "declared_risk_appetite": profile.get("risk_appetite"),
        "onboarding": onboarding,                 # the trend's starting point
        "series": series,                          # the chartable time-series
        "trend": _risk_trend(series),              # shift as a trend over conversations
        "latest_point": last_point,                # most recent point (inferred at t)
    }
