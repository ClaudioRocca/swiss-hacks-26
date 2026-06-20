"""Post-call pipeline.

Three layers, in order:
  1. extraction  — LLM: transcript -> structured facts (this package's extraction.py)
  2. retrieval   — deterministic: gather + join the client's grounded data
  3. synthesis   — LLM, bounded: write the brief from the retrieved packet only
"""

from .extraction import extract_facts, extract_and_store

__all__ = ["extract_facts", "extract_and_store"]
