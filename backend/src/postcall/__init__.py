"""Post-call pipeline.

Two layers, in order (synthesis is out of scope for now):
  1. extraction  — LLM: last call transcript -> structured facts (extraction.py)
  2. retrieval   — deterministic: build the client's risk-profile trend (retrieval.py)
"""

from .extraction import extract_facts, extract_and_store
from .retrieval import build_risk_trend

__all__ = [
    "extract_facts",
    "extract_and_store",
    "build_risk_trend",
]
