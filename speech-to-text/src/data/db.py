"""Database access module for the portfolio manager data layer.

Provides query functions for SQLite (structured data) and ChromaDB (semantic search).
All filter parameters are optional. Multiple filters combine with AND logic.
Invalid filter values are silently ignored.
"""

import json
import os
import sqlite3
from pathlib import Path

import chromadb
from openai import OpenAI

from src.data import DataLayerError

# Resolve database paths from environment or defaults
_SPEECH_TO_TEXT_DIR = Path(__file__).resolve().parent.parent.parent
_SQLITE_PATH = os.environ.get("DATA_SQLITE_PATH", str(_SPEECH_TO_TEXT_DIR / "data" / "portfolio.db"))
_CHROMA_PATH = os.environ.get("DATA_CHROMA_PATH", str(_SPEECH_TO_TEXT_DIR / "data" / "chroma"))

# Valid enum values for filter validation
_VALID_OPERATION_TYPES = {"buy", "sell", "short_sell", "short_cover"}
_VALID_PROPERTY_TYPES = {"residential", "commercial", "industrial", "land"}
_VALID_STATUSES = {"active", "sold", "under_contract"}
_VALID_DIRECTIONS = {"up", "down"}

# ChromaDB collection name
_COLLECTION_NAME = "market_news"

# Cosine similarity threshold for news search
_SIMILARITY_THRESHOLD = 0.3


def _get_sqlite_connection() -> sqlite3.Connection:
    """Get a SQLite connection. Raises DataLayerError if unreachable."""
    try:
        conn = sqlite3.connect(_SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except (sqlite3.OperationalError, sqlite3.DatabaseError) as e:
        raise DataLayerError(f"SQLite database unavailable: {e}")


def _get_chroma_collection():
    """Get ChromaDB collection. Raises DataLayerError if unreachable."""
    try:
        client = chromadb.PersistentClient(path=_CHROMA_PATH)
        collection = client.get_collection(name=_COLLECTION_NAME)
        return collection
    except Exception as e:
        raise DataLayerError(f"ChromaDB collection unavailable: {e}")


def _is_valid_datetime(value: str) -> bool:
    """Check if a string looks like a valid ISO 8601 datetime."""
    if not isinstance(value, str) or len(value) < 10:
        return False
    try:
        # Basic validation - check it starts with YYYY-MM-DD
        parts = value[:10].split("-")
        if len(parts) != 3:
            return False
        int(parts[0])
        int(parts[1])
        int(parts[2])
        return True
    except (ValueError, IndexError):
        return False


def get_portfolio(
    ticker: str | None = None,
    sector: str | None = None,
    min_profit_loss: float | None = None,
    max_profit_loss: float | None = None,
) -> list[dict]:
    """Return stock positions with optional filters.

    - ticker: exact match on stock ticker (case-insensitive)
    - sector: exact match on sector (case-insensitive)
    - min_profit_loss: only positions with profit_loss >= this value
    - max_profit_loss: only positions with profit_loss <= this value
    """
    conn = _get_sqlite_connection()
    try:
        query = "SELECT * FROM portfolio WHERE 1=1"
        params = []

        if ticker is not None and isinstance(ticker, str) and ticker.strip():
            query += " AND LOWER(ticker) = LOWER(?)"
            params.append(ticker.strip())

        if sector is not None and isinstance(sector, str) and sector.strip():
            query += " AND LOWER(sector) = LOWER(?)"
            params.append(sector.strip())

        if min_profit_loss is not None:
            try:
                val = float(min_profit_loss)
                query += " AND profit_loss >= ?"
                params.append(val)
            except (ValueError, TypeError):
                pass

        if max_profit_loss is not None:
            try:
                val = float(max_profit_loss)
                query += " AND profit_loss <= ?"
                params.append(val)
            except (ValueError, TypeError):
                pass

        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.OperationalError as e:
        raise DataLayerError(f"SQLite database unavailable: {e}")
    finally:
        conn.close()


def get_trades(
    ticker: str | None = None,
    operation_type: str | None = None,
    since: str | None = None,
    until: str | None = None,
    min_value: float | None = None,
    limit: int = 50,
) -> list[dict]:
    """Return trades with optional filters, ordered by timestamp desc.

    - ticker: exact match (case-insensitive)
    - operation_type: one of 'buy', 'sell', 'short_sell', 'short_cover'
    - since: ISO 8601 datetime string, return only trades after this date
    - until: ISO 8601 datetime string, return only trades before this date
    - min_value: only trades with value >= this amount
    - limit: max results (default 50, clamped 1-200)
    """
    conn = _get_sqlite_connection()
    try:
        # Clamp limit
        try:
            limit = int(limit)
        except (ValueError, TypeError):
            limit = 50
        limit = max(1, min(200, limit))

        query = "SELECT * FROM trade_operations WHERE 1=1"
        params = []

        if ticker is not None and isinstance(ticker, str) and ticker.strip():
            query += " AND LOWER(ticker) = LOWER(?)"
            params.append(ticker.strip())

        if operation_type is not None and isinstance(operation_type, str):
            if operation_type.lower() in _VALID_OPERATION_TYPES:
                query += " AND operation_type = ?"
                params.append(operation_type.lower())

        if since is not None and _is_valid_datetime(since):
            query += " AND timestamp > ?"
            params.append(since)

        if until is not None and _is_valid_datetime(until):
            query += " AND timestamp < ?"
            params.append(until)

        if min_value is not None:
            try:
                val = float(min_value)
                query += " AND value >= ?"
                params.append(val)
            except (ValueError, TypeError):
                pass

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.OperationalError as e:
        raise DataLayerError(f"SQLite database unavailable: {e}")
    finally:
        conn.close()


def get_customer_profile() -> dict:
    """Return the single customer profile."""
    conn = _get_sqlite_connection()
    try:
        cursor = conn.execute("SELECT * FROM customer_profile LIMIT 1")
        row = cursor.fetchone()
        if row is None:
            return {}
        return dict(row)
    except sqlite3.OperationalError as e:
        raise DataLayerError(f"SQLite database unavailable: {e}")
    finally:
        conn.close()


def get_real_estate(
    property_type: str | None = None,
    status: str | None = None,
    location: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
) -> list[dict]:
    """Return real estate investments with optional filters, ordered by acquisition_date desc.

    - property_type: one of 'residential', 'commercial', 'industrial', 'land'
    - status: one of 'active', 'sold', 'under_contract'
    - location: partial match (SQL LIKE '%location%')
    - min_value: only properties with current_value >= this amount
    - max_value: only properties with current_value <= this amount
    """
    conn = _get_sqlite_connection()
    try:
        query = "SELECT * FROM real_estate_investments WHERE 1=1"
        params = []

        if property_type is not None and isinstance(property_type, str):
            if property_type.lower() in _VALID_PROPERTY_TYPES:
                query += " AND property_type = ?"
                params.append(property_type.lower())

        if status is not None and isinstance(status, str):
            if status.lower() in _VALID_STATUSES:
                query += " AND status = ?"
                params.append(status.lower())

        if location is not None and isinstance(location, str) and location.strip():
            query += " AND LOWER(location) LIKE LOWER(?)"
            params.append(f"%{location.strip()}%")

        if min_value is not None:
            try:
                val = float(min_value)
                query += " AND current_value >= ?"
                params.append(val)
            except (ValueError, TypeError):
                pass

        if max_value is not None:
            try:
                val = float(max_value)
                query += " AND current_value <= ?"
                params.append(val)
            except (ValueError, TypeError):
                pass

        query += " ORDER BY acquisition_date DESC"

        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.OperationalError as e:
        raise DataLayerError(f"SQLite database unavailable: {e}")
    finally:
        conn.close()


def get_market_movements(
    ticker: str | None = None,
    min_change_percent: float | None = None,
    direction: str | None = None,
    since: str | None = None,
    sector: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """Return market movements with optional filters, ordered by timestamp desc.

    - ticker: exact match (case-insensitive)
    - min_change_percent: only movements with abs(percentage_change) >= this value
    - direction: 'up' (price_change > 0) or 'down' (price_change < 0)
    - since: ISO 8601 datetime string, return only movements after this date
    - sector: exact match (case-insensitive)
    - limit: max results (default 50, clamped 1-200)
    """
    conn = _get_sqlite_connection()
    try:
        # Clamp limit
        try:
            limit = int(limit)
        except (ValueError, TypeError):
            limit = 50
        limit = max(1, min(200, limit))

        query = "SELECT * FROM market_movements WHERE 1=1"
        params = []

        if ticker is not None and isinstance(ticker, str) and ticker.strip():
            query += " AND LOWER(ticker) = LOWER(?)"
            params.append(ticker.strip())

        if min_change_percent is not None:
            try:
                val = float(min_change_percent)
                query += " AND ABS(percentage_change) >= ?"
                params.append(val)
            except (ValueError, TypeError):
                pass

        if direction is not None and isinstance(direction, str):
            if direction.lower() == "up":
                query += " AND price_change > 0"
            elif direction.lower() == "down":
                query += " AND price_change < 0"

        if since is not None and _is_valid_datetime(since):
            query += " AND timestamp > ?"
            params.append(since)

        if sector is not None and isinstance(sector, str) and sector.strip():
            query += " AND LOWER(sector) = LOWER(?)"
            params.append(sector.strip())

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.OperationalError as e:
        raise DataLayerError(f"SQLite database unavailable: {e}")
    finally:
        conn.close()


def search_news(
    query: str,
    top_k: int = 5,
    category: str | None = None,
    ticker: str | None = None,
) -> list[dict]:
    """Semantic search over news collection.

    Returns top_k results above similarity threshold (0.3).

    - query: text to search for semantically
    - top_k: number of results to return (default 5, clamped 1-20)
    - category: filter by exact match on category metadata
    - ticker: filter by tickers_mentioned containing this ticker

    Raises DataLayerError if ChromaDB unreachable or OpenAI embedding API fails.
    """
    # Clamp top_k to 1-20
    try:
        top_k = int(top_k)
    except (ValueError, TypeError):
        top_k = 5
    top_k = max(1, min(20, top_k))

    # Generate query embedding using OpenAI
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise DataLayerError("OpenAI API key not configured (OPENAI_API_KEY)")

        client = OpenAI(api_key=api_key)
        response = client.embeddings.create(
            input=query,
            model="text-embedding-3-small",
        )
        query_embedding = response.data[0].embedding
    except DataLayerError:
        raise
    except Exception as e:
        raise DataLayerError(f"Embedding generation failed: {e}")

    # Build metadata filters for ChromaDB
    where_clause = None
    if category is not None and ticker is not None:
        where_clause = {
            "$and": [
                {"category": category},
                {"tickers_mentioned": {"$contains": ticker}},
            ]
        }
    elif category is not None:
        where_clause = {"category": category}
    elif ticker is not None:
        where_clause = {"tickers_mentioned": {"$contains": ticker}}

    # Query ChromaDB
    try:
        collection = _get_chroma_collection()

        query_params = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if where_clause is not None:
            query_params["where"] = where_clause

        results = collection.query(**query_params)
    except DataLayerError:
        raise
    except Exception as e:
        raise DataLayerError(f"ChromaDB query failed: {e}")

    # Process results - ChromaDB returns cosine distance, convert to similarity
    # Cosine distance = 1 - cosine_similarity, so similarity = 1 - distance
    output = []
    if results and results["documents"] and results["documents"][0]:
        documents = results["documents"][0]
        metadatas = results["metadatas"][0] if results["metadatas"] else [{}] * len(documents)
        distances = results["distances"][0] if results["distances"] else [1.0] * len(documents)

        for doc, metadata, distance in zip(documents, metadatas, distances):
            similarity_score = 1.0 - distance
            # Filter out results below cosine similarity threshold
            if similarity_score >= _SIMILARITY_THRESHOLD:
                output.append({
                    "document": doc,
                    "metadata": {
                        "source": metadata.get("source", ""),
                        "category": metadata.get("category", ""),
                        "published_date": metadata.get("published_date", ""),
                        "tickers_mentioned": metadata.get("tickers_mentioned", ""),
                    },
                    "similarity_score": round(similarity_score, 4),
                })

    return output


def _loads(value):
    """Best-effort parse of a JSON text column; returns None on empty/invalid."""
    if not value:
        return None
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return value


# Light columns for call-history lists (excludes heavy transcript/insights_json).
_CALL_LIST_COLUMNS = (
    "id, customer_id, call_date, duration_seconds, channel, summary, "
    "sentiment_score, sentiment_label, risk_signal, topics"
)


def get_calls(customer_id: int | None = None, limit: int = 50) -> list[dict]:
    """Return call-history rows (light columns), ordered by call_date desc.

    - customer_id: filter to one client (single-client demo uses id 1)
    - limit: max results (default 50, clamped 1-200)

    Excludes the full transcript and cached insights_json — use get_call() for
    a single call's full payload. The topics column is parsed from JSON.
    """
    conn = _get_sqlite_connection()
    try:
        try:
            limit = int(limit)
        except (ValueError, TypeError):
            limit = 50
        limit = max(1, min(200, limit))

        query = f"SELECT {_CALL_LIST_COLUMNS} FROM calls WHERE 1=1"
        params = []

        if customer_id is not None:
            try:
                query += " AND customer_id = ?"
                params.append(int(customer_id))
            except (ValueError, TypeError):
                pass

        query += " ORDER BY call_date DESC LIMIT ?"
        params.append(limit)

        cursor = conn.execute(query, params)
        rows = [dict(row) for row in cursor.fetchall()]
        for row in rows:
            row["topics"] = _loads(row.get("topics")) or []
        return rows
    except sqlite3.OperationalError as e:
        raise DataLayerError(f"SQLite database unavailable: {e}")
    finally:
        conn.close()


def get_call(call_id: int) -> dict:
    """Return a single call with full transcript and cached insights.

    Returns {} if no row matches. The topics and insights_json columns are
    parsed from JSON into Python objects.
    """
    conn = _get_sqlite_connection()
    try:
        try:
            call_id = int(call_id)
        except (ValueError, TypeError):
            return {}
        cursor = conn.execute("SELECT * FROM calls WHERE id = ?", [call_id])
        row = cursor.fetchone()
        if row is None:
            return {}
        result = dict(row)
        result["topics"] = _loads(result.get("topics")) or []
        result["insights"] = _loads(result.get("insights_json"))
        return result
    except sqlite3.OperationalError as e:
        raise DataLayerError(f"SQLite database unavailable: {e}")
    finally:
        conn.close()


def get_risk_history(customer_id: int | None = None) -> list[dict]:
    """Return risk-profile snapshots ordered by assessed_date asc (chronological).

    - customer_id: filter to one client (single-client demo uses id 1)

    Ascending order so the result is directly chartable as a trend line.
    """
    conn = _get_sqlite_connection()
    try:
        query = "SELECT * FROM risk_profile_history WHERE 1=1"
        params = []

        if customer_id is not None:
            try:
                query += " AND customer_id = ?"
                params.append(int(customer_id))
            except (ValueError, TypeError):
                pass

        query += " ORDER BY assessed_date ASC"

        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.OperationalError as e:
        raise DataLayerError(f"SQLite database unavailable: {e}")
    finally:
        conn.close()


def save_call_insights(
    call_id: int,
    insights: dict | None = None,
    *,
    summary: str | None = None,
    sentiment_score: float | None = None,
    sentiment_label: str | None = None,
    risk_signal: str | None = None,
    topics: list | None = None,
) -> None:
    """Persist a computed insights bundle (and trend columns) onto a call row.

    Only provided fields are written; existing values are kept otherwise
    (COALESCE). `insights` and `topics` are JSON-serialized. Raises
    DataLayerError if the call row does not exist or the DB is unavailable.
    """
    conn = _get_sqlite_connection()
    try:
        insights_json = json.dumps(insights) if insights is not None else None
        topics_json = json.dumps(topics) if topics is not None else None
        cursor = conn.execute(
            """
            UPDATE calls SET
                insights_json   = COALESCE(?, insights_json),
                summary         = COALESCE(?, summary),
                sentiment_score = COALESCE(?, sentiment_score),
                sentiment_label = COALESCE(?, sentiment_label),
                risk_signal     = COALESCE(?, risk_signal),
                topics          = COALESCE(?, topics)
            WHERE id = ?
            """,
            [insights_json, summary, sentiment_score, sentiment_label,
             risk_signal, topics_json, int(call_id)],
        )
        if cursor.rowcount == 0:
            raise DataLayerError(f"No call with id {call_id} to update")
        conn.commit()
    except sqlite3.OperationalError as e:
        raise DataLayerError(f"SQLite database unavailable: {e}")
    finally:
        conn.close()
