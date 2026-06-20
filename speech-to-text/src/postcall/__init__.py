"""Post-call pipeline.

  - retrieval — deterministic: build the client's risk-profile trend (retrieval.py)
  - synthesis — LLM: turn the evidence packet into an RM pre-brief (synthesis.py, WIP)

The live, frontend-facing call analysis lives in src/post_call_analysis.py.
"""

from .retrieval import build_risk_trend

__all__ = [
    "build_risk_trend",
]
