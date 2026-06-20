"""Data layer for the portfolio manager transcription application.

Provides structured storage (SQLite) and semantic search (ChromaDB)
for customer portfolio, trades, real estate, market movements, and news.
"""


class DataLayerError(Exception):
    """Base exception for data layer failures."""
    pass
