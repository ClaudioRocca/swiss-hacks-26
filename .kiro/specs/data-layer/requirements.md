# Requirements Document

## Introduction

This feature adds a data layer to the portfolio manager transcription application. The data layer provides structured storage (SQLite) for a single high-net-worth customer's portfolio, real estate investments, market movements, trade operations, and profile, plus a vector database (ChromaDB) for semantic search over financial and geopolitical news. An initialization script populates both databases with realistic mock data for one demo customer suitable for a hackathon prototype.

## Glossary

- **Data_Layer**: The combined SQLite and ChromaDB database subsystem that stores and retrieves portfolio manager data
- **SQLite_Database**: The relational database storing structured customer and market data locally
- **Vector_Database**: The ChromaDB instance storing news embeddings for semantic similarity search
- **Portfolio**: A collection of stock positions owned by the demo customer, including ticker symbol, quantity, purchase price, current price, and profit/loss
- **Trade_Operation**: A buy or sell transaction (including short positions) with ticker, quantity, value, and direction
- **Customer_Profile**: Structured KYC and preference data for the single demo customer including risk appetite, investment horizon, and ESG preferences
- **Real_Estate_Investment**: A property-based investment record including location, type, value, rental yield, and acquisition date
- **Market_Movement**: A recent price change record for a financial instrument including ticker, price change, percentage change, and timestamp
- **Initialization_Script**: A Python script that creates both database schemas and inserts mock data for the demo customer
- **Embedding_Model**: The OpenAI embedding model used to vectorize news text for ChromaDB storage and retrieval

## Requirements

### Requirement 1: SQLite Portfolio Table

**User Story:** As a portfolio manager, I want the demo customer's stock portfolio data stored in a relational database, so that I can quickly query holdings during a client call.

#### Acceptance Criteria

1. THE SQLite_Database SHALL store portfolio records with columns: id (integer primary key, auto-increment), ticker (text, max 10 characters, not null), quantity (integer, minimum value of 1, not null), purchase_price (numeric with 2 decimal places, range 0.01 to 999,999,999.99, not null), current_price (numeric with 2 decimal places, range 0.01 to 999,999,999.99, not null), profit_loss (numeric with 2 decimal places, computed as (current_price - purchase_price) * quantity), currency (text, 3-character ISO 4217 code, not null), and sector (text, max 50 characters)
2. WHEN a portfolio query is executed without filters, THE SQLite_Database SHALL return all stock positions in the portfolio table
3. IF a record is inserted with a quantity less than 1 or a ticker exceeding 10 characters, THEN THE SQLite_Database SHALL reject the insert and return a constraint violation error
4. WHEN a portfolio query is executed with a ticker filter, THE SQLite_Database SHALL return only positions whose ticker matches the filter value using case-insensitive exact matching
5. WHEN a portfolio query is executed with a sector filter, THE SQLite_Database SHALL return only positions whose sector matches the filter value using case-insensitive exact matching
6. WHEN a portfolio query is executed with a min_profit_loss filter, THE SQLite_Database SHALL return only positions whose profit_loss is greater than or equal to the filter value
7. WHEN a portfolio query is executed with a max_profit_loss filter, THE SQLite_Database SHALL return only positions whose profit_loss is less than or equal to the filter value

### Requirement 2: SQLite Trade Operations Table

**User Story:** As a portfolio manager, I want to see recent buy and sell operations, so that I can reference trading history during discussions.

#### Acceptance Criteria

1. THE SQLite_Database SHALL store trade operations with columns: id (integer primary key, auto-increment), ticker (text, max 10 characters, not null), quantity (integer greater than 0, not null), value (real number with 2 decimal places, range 0.01 to 999,999,999.99, not null), operation_type (text, not null), and timestamp (ISO 8601 datetime)
2. THE SQLite_Database SHALL constrain operation_type to one of: "buy", "sell", "short_sell", "short_cover"
3. WHEN a trade query is executed without filters, THE SQLite_Database SHALL return at most 50 operations ordered by timestamp descending
4. WHEN a trade operation is inserted without an explicit timestamp, THE SQLite_Database SHALL default the timestamp to the current UTC datetime at insertion time
5. WHEN a trade query is executed with a ticker filter, THE SQLite_Database SHALL return only operations whose ticker matches the filter value using case-insensitive exact matching
6. WHEN a trade query is executed with an operation_type filter, THE SQLite_Database SHALL return only operations whose operation_type matches the filter value
7. WHEN a trade query is executed with a since filter (ISO 8601 datetime string), THE SQLite_Database SHALL return only operations whose timestamp is after the since value
8. WHEN a trade query is executed with an until filter (ISO 8601 datetime string), THE SQLite_Database SHALL return only operations whose timestamp is before the until value
9. WHEN a trade query is executed with a min_value filter, THE SQLite_Database SHALL return only operations whose value is greater than or equal to the min_value

### Requirement 3: SQLite Customer Profile Table

**User Story:** As a portfolio manager, I want structured access to the demo customer's KYC and preference data, so that I can tailor investment discussions.

#### Acceptance Criteria

1. THE SQLite_Database SHALL store a single customer profile record with columns: id (integer primary key), name (text, maximum 200 characters, not null), risk_appetite (text, not null), investment_horizon (text, not null), esg_preference (text, not null), preferred_sectors (comma-separated text, maximum 5 sector entries), total_aum (non-negative decimal in range 0.00 to 999,999,999,999.99), kyc_status (text, not null), and onboarding_date (ISO 8601 date format YYYY-MM-DD)
2. THE SQLite_Database SHALL constrain risk_appetite to one of: "conservative", "moderate", "aggressive"
3. THE SQLite_Database SHALL constrain investment_horizon to one of: "short_term", "medium_term", "long_term"
4. THE SQLite_Database SHALL constrain kyc_status to one of: "verified", "pending", "expired"
5. THE SQLite_Database SHALL constrain esg_preference to one of: "none", "moderate", "strong"
6. WHEN a customer profile query is executed, THE SQLite_Database SHALL return the single customer profile record

### Requirement 4: SQLite Real Estate Investments Table

**User Story:** As a portfolio manager, I want real estate investment data available alongside stock portfolios, so that I can discuss the client's full wealth picture.

#### Acceptance Criteria

1. THE SQLite_Database SHALL store real estate investments with columns: id (integer primary key, auto-increment), property_type (text, not null), location (text, not null, maximum 255 characters), current_value (real, not null, range 0.01 to 999,999,999.99), acquisition_price (real, not null, range 0.01 to 999,999,999.99), acquisition_date (text, not null, format YYYY-MM-DD), rental_yield_percent (real, range 0.00 to 100.00), and status (text, not null)
2. THE SQLite_Database SHALL constrain property_type to one of: "residential", "commercial", "industrial", "land"
3. THE SQLite_Database SHALL constrain status to one of: "active", "sold", "under_contract"
4. WHEN a real estate query is executed without filters, THE SQLite_Database SHALL return all real estate holdings ordered by acquisition_date descending
5. IF a real estate investment record is inserted with current_value, acquisition_price, or rental_yield_percent outside their defined ranges, THEN THE SQLite_Database SHALL reject the insert
6. WHEN a real estate query is executed with a property_type filter, THE SQLite_Database SHALL return only investments whose property_type matches the filter value
7. WHEN a real estate query is executed with a status filter, THE SQLite_Database SHALL return only investments whose status matches the filter value
8. WHEN a real estate query is executed with a location filter, THE SQLite_Database SHALL return only investments whose location contains the filter value as a substring (partial match, case-insensitive)
9. WHEN a real estate query is executed with a min_value filter, THE SQLite_Database SHALL return only investments whose current_value is greater than or equal to the min_value
10. WHEN a real estate query is executed with a max_value filter, THE SQLite_Database SHALL return only investments whose current_value is less than or equal to the max_value

### Requirement 5: SQLite Market Movements Table

**User Story:** As a portfolio manager, I want recent market movements available for quick reference, so that I can discuss market context with clients.

#### Acceptance Criteria

1. THE SQLite_Database SHALL store market movements with columns: id (integer primary key, auto-increment), ticker (text, max 10 characters, not null), company_name (text, max 100 characters), sector (text, max 50 characters), price_change (numeric with 2 decimal places, not null), percentage_change (numeric with 2 decimal places, not null), current_price (numeric with 2 decimal places, greater than 0, not null), volume (integer, 0 or greater), and timestamp (ISO 8601 UTC format, not null)
2. WHEN a market movements query is executed without filters, THE SQLite_Database SHALL return at most 100 records ordered by timestamp descending
3. WHEN a market movements query is executed with a ticker filter, THE SQLite_Database SHALL return only records whose ticker matches the filter value using case-insensitive exact matching
4. IF a market movements query returns no matching records, THEN THE SQLite_Database SHALL return an empty result set with no error
5. WHEN a market movements query is executed with a min_change_percent filter, THE SQLite_Database SHALL return only records whose absolute value of percentage_change is greater than or equal to the filter value
6. WHEN a market movements query is executed with a direction filter of "up", THE SQLite_Database SHALL return only records whose price_change is greater than 0
7. WHEN a market movements query is executed with a direction filter of "down", THE SQLite_Database SHALL return only records whose price_change is less than 0
8. WHEN a market movements query is executed with a since filter (ISO 8601 datetime string), THE SQLite_Database SHALL return only records whose timestamp is after the since value
9. WHEN a market movements query is executed with a sector filter, THE SQLite_Database SHALL return only records whose sector matches the filter value using case-insensitive exact matching

### Requirement 6: ChromaDB News Collection

**User Story:** As a portfolio manager, I want to semantically search financial and geopolitical news, so that I can find relevant context for client discussions based on meaning rather than keywords.

#### Acceptance Criteria

1. THE Vector_Database SHALL store news documents in a collection named "market_news" with fields: document text (maximum 8,000 characters), embedding vector, and metadata (source, category, published_date, tickers_mentioned)
2. WHEN a semantic search query is executed with a text input, THE Vector_Database SHALL return the top-k most similar news documents ranked by cosine similarity, where k defaults to 5 and has a maximum value of 20
3. THE Vector_Database SHALL use the OpenAI text-embedding-3-small model via the Embedding_Model to generate embeddings
4. THE Vector_Database SHALL support filtering search results by exact match on metadata fields (category, tickers_mentioned), where tickers_mentioned supports matching any single value within the stored list
5. IF the Embedding_Model is unavailable or returns an error during a search query, THEN THE Vector_Database SHALL return an error indication specifying that embedding generation failed, without returning partial or unranked results
6. IF a semantic search query yields no documents above a minimum cosine similarity threshold of 0.3, THEN THE Vector_Database SHALL return an empty result set

### Requirement 7: Initialization Script

**User Story:** As a developer on the hackathon team, I want a single script that sets up both databases with mock data for the demo customer, so that anyone can spin up the demo environment instantly.

#### Acceptance Criteria

1. WHEN the Initialization_Script is executed, THE Data_Layer SHALL create the SQLite database file and all tables defined in Requirements 1 through 5 (portfolio, trade_operations, customer_profile, real_estate_investments, market_movements)
2. WHEN the Initialization_Script is executed, THE Data_Layer SHALL create the ChromaDB collection named "market_news" as defined in Requirement 6
3. WHEN the Initialization_Script is executed, THE Data_Layer SHALL insert 1 mock customer profile, at least 5 portfolio positions, at least 3 real estate investments, at least 10 trade operations, at least 10 market movement records into SQLite, and at least 15 news articles into ChromaDB as embedded documents with metadata
4. IF the databases already contain data, THEN THE Initialization_Script SHALL drop and recreate all SQLite tables and the ChromaDB collection before inserting mock data
5. THE Initialization_Script SHALL complete execution without requiring external network calls beyond the OpenAI embedding API
6. WHEN the Initialization_Script completes successfully, THE Data_Layer SHALL print to stdout the count of records inserted into each SQLite table and the ChromaDB collection
7. IF the OpenAI embedding API is unreachable or returns an error during execution, THEN THE Initialization_Script SHALL terminate with a non-zero exit code and print an error message indicating the embedding failure
8. THE Initialization_Script SHALL complete all database setup and mock data insertion within 60 seconds, excluding OpenAI API response time

### Requirement 8: Database Access Module

**User Story:** As a developer, I want a simple Python module that provides query functions for both databases, so that the transcription pipeline can retrieve data without raw SQL.

#### Acceptance Criteria

1. THE Data_Layer SHALL expose a function `get_portfolio(ticker, sector, min_profit_loss, max_profit_loss)` with all parameters optional, returning a list of dictionaries representing stock positions
2. THE Data_Layer SHALL expose a function `get_trades(ticker, operation_type, since, until, min_value, limit)` with all parameters optional (limit defaults to 50), returning a list of dictionaries ordered by timestamp descending
3. THE Data_Layer SHALL expose a function `get_customer_profile()` returning a single dictionary
4. THE Data_Layer SHALL expose a function `get_real_estate(property_type, status, location, min_value, max_value)` with all parameters optional, returning a list of dictionaries ordered by acquisition_date descending
5. THE Data_Layer SHALL expose a function `get_market_movements(ticker, min_change_percent, direction, since, sector, limit)` with all parameters optional (limit defaults to 50, clamped to range 1-200), returning results ordered by timestamp descending
6. THE Data_Layer SHALL expose a function `search_news(query, top_k, category, ticker)` to perform semantic search on the news collection given a query string and an optional top_k parameter (default 5, range 1 to 20)
7. THE Data_Layer SHALL return an empty list from collection query functions when no records match a given filter
8. IF the SQLite database file or the ChromaDB collection is unreachable, THEN THE Data_Layer SHALL raise an exception with a message indicating which database is unavailable
9. WHEN any query function receives an invalid filter value (unrecognized enum value, malformed datetime, or nonsensical numeric range), THE Data_Layer SHALL silently ignore that filter parameter and treat it as unspecified, returning results as if that filter were not applied
