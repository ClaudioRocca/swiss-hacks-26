-- Schema for portfolio manager data layer
-- SQLite database schema with all constraints

CREATE TABLE IF NOT EXISTS portfolio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL CHECK(length(ticker) <= 10),
    quantity INTEGER NOT NULL CHECK(quantity >= 1),
    purchase_price REAL NOT NULL CHECK(purchase_price >= 0.01 AND purchase_price <= 999999999.99),
    current_price REAL NOT NULL CHECK(current_price >= 0.01 AND current_price <= 999999999.99),
    profit_loss REAL GENERATED ALWAYS AS ((current_price - purchase_price) * quantity) STORED,
    currency TEXT NOT NULL CHECK(length(currency) = 3),
    sector TEXT CHECK(sector IS NULL OR length(sector) <= 50)
);

CREATE TABLE IF NOT EXISTS trade_operations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL CHECK(length(ticker) <= 10),
    quantity INTEGER NOT NULL CHECK(quantity > 0),
    value REAL NOT NULL CHECK(value >= 0.01 AND value <= 999999999.99),
    operation_type TEXT NOT NULL CHECK(operation_type IN ('buy', 'sell', 'short_sell', 'short_cover')),
    timestamp TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS customer_profile (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL CHECK(length(name) <= 200),
    risk_appetite TEXT NOT NULL CHECK(risk_appetite IN ('conservative', 'moderate', 'aggressive')),
    investment_horizon TEXT NOT NULL CHECK(investment_horizon IN ('short_term', 'medium_term', 'long_term')),
    esg_preference TEXT NOT NULL CHECK(esg_preference IN ('none', 'moderate', 'strong')),
    preferred_sectors TEXT CHECK(preferred_sectors IS NULL OR length(preferred_sectors) - length(replace(preferred_sectors, ',', '')) < 5),
    total_aum REAL CHECK(total_aum IS NULL OR total_aum >= 0),
    kyc_status TEXT NOT NULL CHECK(kyc_status IN ('verified', 'pending', 'expired')),
    onboarding_date TEXT
);

CREATE TABLE IF NOT EXISTS real_estate_investments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_type TEXT NOT NULL CHECK(property_type IN ('residential', 'commercial', 'industrial', 'land')),
    location TEXT NOT NULL CHECK(length(location) <= 255),
    current_value REAL NOT NULL CHECK(current_value >= 0.01 AND current_value <= 999999999.99),
    acquisition_price REAL NOT NULL CHECK(acquisition_price >= 0.01 AND acquisition_price <= 999999999.99),
    acquisition_date TEXT NOT NULL,
    rental_yield_percent REAL CHECK(rental_yield_percent IS NULL OR (rental_yield_percent >= 0.00 AND rental_yield_percent <= 100.00)),
    status TEXT NOT NULL CHECK(status IN ('active', 'sold', 'under_contract'))
);

CREATE TABLE IF NOT EXISTS market_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL CHECK(length(ticker) <= 10),
    company_name TEXT CHECK(company_name IS NULL OR length(company_name) <= 100),
    sector TEXT CHECK(sector IS NULL OR length(sector) <= 50),
    price_change REAL NOT NULL,
    percentage_change REAL NOT NULL,
    current_price REAL NOT NULL CHECK(current_price > 0),
    volume INTEGER CHECK(volume IS NULL OR volume >= 0),
    timestamp TEXT NOT NULL
);

-- Call history: one row per past relationship-manager <-> client call.
-- transcript is the full text; sentiment/risk_signal/topics are first-class
-- columns for trend queries; insights_json caches the computed post-call bundle.
CREATE TABLE IF NOT EXISTS calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    call_date TEXT NOT NULL,
    duration_seconds INTEGER CHECK(duration_seconds IS NULL OR duration_seconds >= 0),
    channel TEXT CHECK(channel IS NULL OR channel IN ('phone', 'video', 'in_person')),
    transcript TEXT NOT NULL,
    summary TEXT,
    sentiment_score REAL CHECK(sentiment_score IS NULL OR (sentiment_score >= -1.0 AND sentiment_score <= 1.0)),
    sentiment_label TEXT CHECK(sentiment_label IS NULL OR sentiment_label IN ('negative', 'neutral', 'positive')),
    risk_signal TEXT CHECK(risk_signal IS NULL OR risk_signal IN ('conservative', 'moderate', 'aggressive')),
    topics TEXT,
    facts_json TEXT,
    insights_json TEXT
);

-- Risk-profile snapshots over time: the canonical chartable series behind the
-- "risk profile over time" trend and the behavioral-drift signal.
CREATE TABLE IF NOT EXISTS risk_profile_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    assessed_date TEXT NOT NULL,
    risk_appetite TEXT NOT NULL CHECK(risk_appetite IN ('conservative', 'moderate', 'aggressive')),
    risk_score REAL CHECK(risk_score IS NULL OR (risk_score >= 1.0 AND risk_score <= 10.0)),
    source TEXT CHECK(source IS NULL OR source IN ('onboarding', 'call', 'review')),
    note TEXT
);
