# Implementation Plan: Data Layer

## Overview

Build the local data layer for the portfolio manager transcription app. The implementation follows the design's layered approach: schema definition → database access module → initialization script → retriever integration. All files live under `speech-to-text/src/data/`.

## Tasks

- [x] 1. Set up project structure and dependencies
  - [x] 1.1 Create data module directory and install dependencies
    - Create `speech-to-text/src/data/` directory with `__init__.py`
    - Add `chromadb>=0.4.0` to `speech-to-text/requirements.txt` (production dep)
    - Add `pytest>=7.0` and `hypothesis>=6.0` to `speech-to-text/requirements.txt` (dev deps)
    - Export `DataLayerError` from `__init__.py`
    - _Requirements: 8.8_

- [x] 2. Define database schema
  - [x] 2.1 Create schema.sql with all table definitions
    - Write CREATE TABLE statements for: `portfolio`, `trade_operations`, `customer_profile`, `real_estate_investments`, `market_movements`
    - Include all CHECK constraints for enums, ranges, and field lengths as specified in design
    - Include GENERATED column for `profit_loss` in portfolio table
    - Include DEFAULT for `timestamp` in trade_operations using `strftime('%Y-%m-%dT%H:%M:%SZ','now')`
    - _Requirements: 1.1, 2.1, 2.2, 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 5.1_

- [ ] 3. Implement database access module
  - [x] 3.1 Implement SQLite query functions in db.py
    - Create `speech-to-text/src/data/db.py` with `DataLayerError` exception class
    - Implement `get_portfolio(ticker, sector, min_profit_loss, max_profit_loss)` with case-insensitive filtering and AND logic
    - Implement `get_trades(ticker, operation_type, since, until, min_value, limit)` with limit clamped to 1-200, ordered by timestamp desc
    - Implement `get_customer_profile()` returning single dict
    - Implement `get_real_estate(property_type, status, location, min_value, max_value)` with LIKE for location, ordered by acquisition_date desc
    - Implement `get_market_movements(ticker, min_change_percent, direction, since, sector, limit)` with abs() filter and direction logic, ordered by timestamp desc
    - All functions use parameterized SQL, return list[dict], raise `DataLayerError` if db unreachable
    - Invalid filter values (unrecognized enums, malformed datetimes) silently ignored
    - _Requirements: 1.2, 1.4, 1.5, 1.6, 1.7, 2.3, 2.5, 2.6, 2.7, 2.8, 2.9, 3.6, 4.4, 4.6, 4.7, 4.8, 4.9, 4.10, 5.2, 5.3, 5.5, 5.6, 5.7, 5.8, 5.9, 8.1, 8.2, 8.3, 8.4, 8.5, 8.7, 8.8, 8.9_

  - [x] 3.2 Implement search_news function with ChromaDB
    - Add `search_news(query, top_k, category, ticker)` to db.py
    - Use OpenAI text-embedding-3-small for query embedding generation
    - Apply metadata filters (category exact match, tickers_mentioned contains ticker)
    - Clamp top_k to range 1-20, default 5
    - Filter results below cosine similarity threshold of 0.3
    - Raise `DataLayerError` if ChromaDB unreachable or embedding API fails
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 8.6_

  - [ ]* 3.3 Write property test: Data round-trip preservation (Property 1)
    - **Property 1: Data round-trip preservation**
    - Use Hypothesis to generate valid portfolio records (valid ticker length, quantity >= 1, prices in range)
    - Insert into in-memory SQLite, call `get_portfolio()`, verify all records returned with identical values
    - `@settings(max_examples=100)`
    - **Validates: Requirements 1.2, 8.1**

  - [ ]* 3.4 Write property test: Constraint violation rejection (Property 2)
    - **Property 2: Constraint violation rejection**
    - Use Hypothesis to generate invalid records (ticker > 10 chars, quantity < 1, bad enum values, out-of-range numerics)
    - Verify each insert raises IntegrityError and db state is unchanged
    - `@settings(max_examples=100)`
    - **Validates: Requirements 1.3, 2.2, 3.2, 3.3, 3.4, 3.5, 4.2, 4.3, 4.5**

  - [ ]* 3.5 Write property test: Query ordering and limit enforcement (Property 3)
    - **Property 3: Query ordering and limit enforcement**
    - Use Hypothesis to generate N records for trade_operations, real_estate, and market_movements
    - Verify results are sorted by timestamp/acquisition_date descending
    - Verify result count never exceeds limit parameter
    - `@settings(max_examples=100)`
    - **Validates: Requirements 2.3, 4.4, 5.2, 8.2, 8.4**

  - [ ]* 3.6 Write property test: Case-insensitive ticker filtering (Property 4)
    - **Property 4: Case-insensitive ticker filtering**
    - Use Hypothesis to generate ticker strings in various case combinations
    - Insert market movements, filter with different case, verify correct subset returned
    - `@settings(max_examples=100)`
    - **Validates: Requirements 5.3**

  - [ ]* 3.7 Write property test: Parameter clamping (Property 6)
    - **Property 6: Parameter clamping**
    - Use Hypothesis to generate arbitrary integers for limit/top_k params
    - Verify effective value clamped to valid range (1-200 for limit, 1-20 for top_k)
    - Verify result count never exceeds clamped value
    - `@settings(max_examples=100)`
    - **Validates: Requirements 8.5, 8.6**

- [~] 4. Checkpoint - Verify schema and access module
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement initialization script
  - [x] 5.1 Create init_db.py with schema setup and mock data
    - Implement as runnable module (`python -m src.data.init_db`)
    - Drop and recreate all SQLite tables using schema.sql
    - Drop and recreate ChromaDB `market_news` collection
    - Insert mock data: 1 customer profile, 5+ portfolio positions, 3+ real estate investments, 10+ trade operations, 10+ market movements, 15+ news articles with embeddings
    - Use OpenAI text-embedding-3-small for news article embeddings
    - Print record counts per table/collection on success
    - Exit non-zero with error message if OpenAI API fails
    - Resolve paths from `DATA_SQLITE_PATH` / `DATA_CHROMA_PATH` env vars or default to `data/portfolio.db` and `data/chroma/`
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8_

  - [ ]* 5.2 Write property test: Initialization idempotency (Property 5)
    - **Property 5: Initialization idempotency**
    - Use Hypothesis to generate random initial db states (empty, partial, full)
    - Run init script, verify final state has expected record counts regardless of initial state
    - Use mock embedding function to avoid API calls
    - `@settings(max_examples=100)`
    - **Validates: Requirements 7.4**

- [ ] 6. Implement data retriever
  - [~] 6.1 Create retriever.py with LLM intent extraction and query dispatch
    - Implement `retrieve_context(chunk: ConceptChunk) -> dict`
    - Use OpenAI chat completion to extract structured query intent from chunk summary/entities
    - Map intent action + fields directly to db.py filter parameters (1:1 mapping)
    - Handle multiple actions in a single chunk (e.g., portfolio + news search)
    - Wrap blocking db calls in `asyncio.to_thread` for async pipeline compatibility
    - Return dict with query results keyed by action type
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

- [ ] 7. Wire data layer into existing pipeline
  - [~] 7.1 Integrate retriever with orchestrator
    - Import retriever in `speech-to-text/src/orchestrator.py`
    - Add `retrieve_context` call in the `on_trigger` callback after concept segmentation
    - Pass retrieved data to downstream consumers
    - _Requirements: 8.1, 8.6_

- [~] 8. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- All database operations use in-memory SQLite (`:memory:`) during testing for speed
- ChromaDB tests use a temporary directory with mock embeddings to avoid OpenAI API calls
- The design specifies Python throughout — all implementation uses Python 3.10+

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["2.1"] },
    { "id": 2, "tasks": ["3.1", "3.2"] },
    { "id": 3, "tasks": ["3.3", "3.4", "3.5", "3.6", "3.7"] },
    { "id": 4, "tasks": ["5.1"] },
    { "id": 5, "tasks": ["5.2", "6.1"] },
    { "id": 6, "tasks": ["7.1"] }
  ]
}
```
