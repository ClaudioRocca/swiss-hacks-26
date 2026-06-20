"""Database initialization script for the portfolio manager demo.

Runnable as: python -m src.data.init_db (from speech-to-text/ directory)

Drops and recreates all SQLite tables and the ChromaDB market_news collection,
then inserts realistic mock data for a Swiss high-net-worth client demo.
"""

import os
import sys
import sqlite3
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Load .env from project root (two levels up from this file)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

import chromadb
from openai import OpenAI

from src.data import DataLayerError

# Use a custom httpx client to bypass corporate proxy SSL issues
_HTTP_CLIENT = httpx.Client(verify=False)

# Resolve paths
_SPEECH_TO_TEXT_DIR = Path(__file__).resolve().parent.parent.parent
_SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
_SQLITE_PATH = os.environ.get("DATA_SQLITE_PATH", str(_SPEECH_TO_TEXT_DIR / "data" / "portfolio.db"))
_CHROMA_PATH = os.environ.get("DATA_CHROMA_PATH", str(_SPEECH_TO_TEXT_DIR / "data" / "chroma"))

# Collection name
_COLLECTION_NAME = "market_news"


# --- Mock Data: Swiss HNW Client Context ---

CUSTOMER_PROFILE = {
    "id": 1,
    "name": "Dr. Maximilian Keller",
    "risk_appetite": "moderate",
    "investment_horizon": "long_term",
    "esg_preference": "moderate",
    "preferred_sectors": "technology,healthcare,financials,energy",
    "total_aum": 47500000.00,
    "kyc_status": "verified",
    "onboarding_date": "2019-03-15",
}

PORTFOLIO_POSITIONS = [
    {"ticker": "NESN", "quantity": 1200, "purchase_price": 98.50, "current_price": 107.80, "currency": "CHF", "sector": "consumer staples"},
    {"ticker": "NOVN", "quantity": 800, "purchase_price": 82.30, "current_price": 91.45, "currency": "CHF", "sector": "healthcare"},
    {"ticker": "ROG", "quantity": 350, "purchase_price": 245.60, "current_price": 258.90, "currency": "CHF", "sector": "healthcare"},
    {"ticker": "UBSG", "quantity": 2000, "purchase_price": 24.80, "current_price": 28.35, "currency": "CHF", "sector": "financials"},
    {"ticker": "ZURN", "quantity": 600, "purchase_price": 450.20, "current_price": 478.60, "currency": "CHF", "sector": "insurance"},
    {"ticker": "AAPL", "quantity": 500, "purchase_price": 142.50, "current_price": 198.30, "currency": "USD", "sector": "technology"},
    {"ticker": "MSFT", "quantity": 300, "purchase_price": 280.00, "current_price": 430.50, "currency": "USD", "sector": "technology"},
    {"ticker": "ASML", "quantity": 150, "purchase_price": 580.00, "current_price": 645.20, "currency": "EUR", "sector": "technology"},
]

REAL_ESTATE_INVESTMENTS = [
    {
        "property_type": "residential",
        "location": "Zurich, Seefeld",
        "current_value": 4800000.00,
        "acquisition_price": 3900000.00,
        "acquisition_date": "2017-06-20",
        "rental_yield_percent": 3.2,
        "status": "active",
    },
    {
        "property_type": "commercial",
        "location": "Geneva, Rue du Rhone",
        "current_value": 8500000.00,
        "acquisition_price": 7200000.00,
        "acquisition_date": "2019-11-05",
        "rental_yield_percent": 4.8,
        "status": "active",
    },
    {
        "property_type": "residential",
        "location": "Lugano, Paradiso",
        "current_value": 2200000.00,
        "acquisition_price": 1950000.00,
        "acquisition_date": "2021-03-12",
        "rental_yield_percent": 2.9,
        "status": "active",
    },
    {
        "property_type": "land",
        "location": "Zug, Oberägeri",
        "current_value": 1500000.00,
        "acquisition_price": 1200000.00,
        "acquisition_date": "2022-08-01",
        "rental_yield_percent": None,
        "status": "active",
    },
    {
        "property_type": "commercial",
        "location": "Basel, Aeschenvorstadt",
        "current_value": 3100000.00,
        "acquisition_price": 3400000.00,
        "acquisition_date": "2020-01-15",
        "rental_yield_percent": 5.1,
        "status": "sold",
    },
]

TRADE_OPERATIONS = [
    {"ticker": "NESN", "quantity": 200, "value": 21560.00, "operation_type": "buy", "timestamp": "2025-05-20T09:15:00Z"},
    {"ticker": "UBSG", "quantity": 500, "value": 14175.00, "operation_type": "buy", "timestamp": "2025-05-19T10:30:00Z"},
    {"ticker": "AAPL", "quantity": 100, "value": 19830.00, "operation_type": "sell", "timestamp": "2025-05-18T14:45:00Z"},
    {"ticker": "ROG", "quantity": 50, "value": 12945.00, "operation_type": "buy", "timestamp": "2025-05-17T11:00:00Z"},
    {"ticker": "NOVN", "quantity": 200, "value": 18290.00, "operation_type": "buy", "timestamp": "2025-05-16T09:45:00Z"},
    {"ticker": "MSFT", "quantity": 50, "value": 21525.00, "operation_type": "sell", "timestamp": "2025-05-15T15:30:00Z"},
    {"ticker": "ASML", "quantity": 30, "value": 19356.00, "operation_type": "buy", "timestamp": "2025-05-14T10:15:00Z"},
    {"ticker": "ZURN", "quantity": 100, "value": 47860.00, "operation_type": "sell", "timestamp": "2025-05-13T13:00:00Z"},
    {"ticker": "NESN", "quantity": 300, "value": 29550.00, "operation_type": "short_sell", "timestamp": "2025-05-12T09:30:00Z"},
    {"ticker": "NESN", "quantity": 300, "value": 32340.00, "operation_type": "short_cover", "timestamp": "2025-05-20T16:00:00Z"},
    {"ticker": "UBSG", "quantity": 400, "value": 9920.00, "operation_type": "buy", "timestamp": "2025-05-10T08:45:00Z"},
    {"ticker": "AAPL", "quantity": 200, "value": 28500.00, "operation_type": "buy", "timestamp": "2025-05-08T14:00:00Z"},
]

MARKET_MOVEMENTS = [
    {"ticker": "NESN", "company_name": "Nestle SA", "sector": "consumer staples", "price_change": 2.30, "percentage_change": 2.18, "current_price": 107.80, "volume": 4520000, "timestamp": "2025-05-26T16:30:00Z"},
    {"ticker": "NOVN", "company_name": "Novartis AG", "sector": "healthcare", "price_change": -1.55, "percentage_change": -1.67, "current_price": 91.45, "volume": 3870000, "timestamp": "2025-05-26T16:30:00Z"},
    {"ticker": "ROG", "company_name": "Roche Holding AG", "sector": "healthcare", "price_change": 3.80, "percentage_change": 1.49, "current_price": 258.90, "volume": 1950000, "timestamp": "2025-05-26T16:30:00Z"},
    {"ticker": "UBSG", "company_name": "UBS Group AG", "sector": "financials", "price_change": 0.45, "percentage_change": 1.61, "current_price": 28.35, "volume": 8200000, "timestamp": "2025-05-26T16:30:00Z"},
    {"ticker": "ZURN", "company_name": "Zurich Insurance Group", "sector": "insurance", "price_change": -5.40, "percentage_change": -1.12, "current_price": 478.60, "volume": 980000, "timestamp": "2025-05-26T16:30:00Z"},
    {"ticker": "AAPL", "company_name": "Apple Inc.", "sector": "technology", "price_change": 4.20, "percentage_change": 2.16, "current_price": 198.30, "volume": 52000000, "timestamp": "2025-05-26T20:00:00Z"},
    {"ticker": "MSFT", "company_name": "Microsoft Corp.", "sector": "technology", "price_change": -3.50, "percentage_change": -0.81, "current_price": 430.50, "volume": 28000000, "timestamp": "2025-05-26T20:00:00Z"},
    {"ticker": "ASML", "company_name": "ASML Holding NV", "sector": "technology", "price_change": 12.40, "percentage_change": 1.96, "current_price": 645.20, "volume": 3400000, "timestamp": "2025-05-26T17:30:00Z"},
    {"ticker": "CSGN", "company_name": "Credit Suisse (legacy)", "sector": "financials", "price_change": -0.02, "percentage_change": -2.50, "current_price": 0.78, "volume": 150000, "timestamp": "2025-05-26T16:30:00Z"},
    {"ticker": "SREN", "company_name": "Swiss Re AG", "sector": "insurance", "price_change": 1.80, "percentage_change": 1.45, "current_price": 125.80, "volume": 1200000, "timestamp": "2025-05-26T16:30:00Z"},
    {"ticker": "ABBN", "company_name": "ABB Ltd", "sector": "industrials", "price_change": -2.10, "percentage_change": -3.85, "current_price": 52.50, "volume": 5600000, "timestamp": "2025-05-26T16:30:00Z"},
    {"ticker": "GIVN", "company_name": "Givaudan SA", "sector": "materials", "price_change": 45.00, "percentage_change": 1.12, "current_price": 4070.00, "volume": 120000, "timestamp": "2025-05-26T16:30:00Z"},
]

NEWS_ARTICLES = [
    {
        "text": "Swiss National Bank maintains policy rate at 1.50%, signaling confidence in inflation trajectory. The SNB noted that the Swiss franc remains strong but manageable for exporters. Governor Thomas Jordan emphasized that monetary policy normalization is proceeding as expected.",
        "metadata": {"source": "Reuters", "category": "macro", "published_date": "2025-05-26", "tickers_mentioned": "UBSG,CSGN"},
    },
    {
        "text": "Novartis reports stronger-than-expected Q1 results with core operating income up 15%. The Basel-based pharma giant raised full-year guidance citing robust demand for key oncology and immunology products. Shares rose 3% in early Zurich trading.",
        "metadata": {"source": "Bloomberg", "category": "equity", "published_date": "2025-05-25", "tickers_mentioned": "NOVN"},
    },
    {
        "text": "Nestle announces CHF 3 billion share buyback program amid activist investor pressure. The Vevey-based food giant is restructuring its portfolio, divesting underperforming water brands while doubling down on health science and premium coffee segments.",
        "metadata": {"source": "Financial Times", "category": "equity", "published_date": "2025-05-24", "tickers_mentioned": "NESN"},
    },
    {
        "text": "UBS completes final integration phase of Credit Suisse wealth management operations. The merged entity now manages over CHF 5 trillion in invested assets, making it the world's largest wealth manager. Cost synergies ahead of schedule at CHF 10 billion annually.",
        "metadata": {"source": "NZZ", "category": "equity", "published_date": "2025-05-23", "tickers_mentioned": "UBSG,CSGN"},
    },
    {
        "text": "European Central Bank signals potential rate cut in July meeting as eurozone inflation drops to 2.1%. Markets are pricing in two additional 25bp cuts by year-end. The euro weakened against the Swiss franc on the announcement.",
        "metadata": {"source": "Reuters", "category": "macro", "published_date": "2025-05-22", "tickers_mentioned": ""},
    },
    {
        "text": "Zurich Insurance Group reports record first-half operating profit of USD 4.2 billion. Strong performance in property casualty insurance offset moderate growth in life insurance. The company raised its dividend outlook for 2025.",
        "metadata": {"source": "Bloomberg", "category": "equity", "published_date": "2025-05-21", "tickers_mentioned": "ZURN"},
    },
    {
        "text": "Swiss real estate market shows signs of cooling as mortgage rates stabilize at 2.8%. Luxury segment remains robust in Geneva and Zurich lakefront properties. Commercial real estate in Basel sees increased vacancy rates in peripheral locations.",
        "metadata": {"source": "Credit Suisse Research", "category": "real_estate", "published_date": "2025-05-20", "tickers_mentioned": ""},
    },
    {
        "text": "Apple unveils new AI-powered health monitoring features at WWDC 2025. The Apple Watch Series 11 will include blood pressure monitoring and continuous glucose tracking. Analysts expect this to drive upgrade cycles in the premium wearable segment.",
        "metadata": {"source": "CNBC", "category": "equity", "published_date": "2025-05-19", "tickers_mentioned": "AAPL"},
    },
    {
        "text": "ASML reports record backlog of EUR 56 billion as chip manufacturers race to secure EUV lithography capacity. The Dutch company raised its 2025 revenue guidance by 8%, citing strong demand from AI infrastructure buildout.",
        "metadata": {"source": "Bloomberg", "category": "equity", "published_date": "2025-05-18", "tickers_mentioned": "ASML"},
    },
    {
        "text": "Geopolitical tensions in the South China Sea escalate as naval exercises intensify. Swiss defense stocks and gold ETFs see inflows as investors seek safe-haven assets. The Swiss franc strengthened 0.8% against the euro on risk-off sentiment.",
        "metadata": {"source": "Reuters", "category": "geopolitical", "published_date": "2025-05-17", "tickers_mentioned": ""},
    },
    {
        "text": "Roche's new Alzheimer's drug receives FDA breakthrough therapy designation. Phase 3 trial data showed 35% reduction in cognitive decline. The Basel company's shares surged 4% on the news, outperforming the broader SPI index.",
        "metadata": {"source": "Financial Times", "category": "equity", "published_date": "2025-05-16", "tickers_mentioned": "ROG"},
    },
    {
        "text": "Swiss ESG funds see record inflows of CHF 8 billion in Q1 2025. Sustainable investing now represents 42% of total Swiss fund assets under management. Technology and healthcare remain the most popular ESG-screened sectors.",
        "metadata": {"source": "SIX Swiss Exchange", "category": "macro", "published_date": "2025-05-15", "tickers_mentioned": ""},
    },
    {
        "text": "Microsoft Azure reports 45% revenue growth driven by enterprise AI adoption. The company's partnership with OpenAI continues to drive competitive advantage in cloud services. Swiss corporate clients are among the fastest adopters in Europe.",
        "metadata": {"source": "Bloomberg", "category": "equity", "published_date": "2025-05-14", "tickers_mentioned": "MSFT"},
    },
    {
        "text": "Swiss Re warns of increasing climate-related insurance losses in Alpine regions. The reinsurer estimates CHF 2.5 billion in additional reserves needed for flood and landslide risks through 2030. Property insurance premiums expected to rise 15-20%.",
        "metadata": {"source": "NZZ", "category": "equity", "published_date": "2025-05-13", "tickers_mentioned": "SREN"},
    },
    {
        "text": "ABB secures CHF 1.2 billion robotics contract with major European automotive manufacturer. The order is the largest single robotics deal in the company's history and will be fulfilled from the Zurich headquarters facility over 3 years.",
        "metadata": {"source": "Reuters", "category": "equity", "published_date": "2025-05-12", "tickers_mentioned": "ABBN"},
    },
    {
        "text": "Global commodity prices surge as OPEC+ announces surprise production cuts of 1.5 million barrels per day. Brent crude rises above USD 95 per barrel. Swiss industrial companies face higher input costs, particularly in chemicals and manufacturing sectors.",
        "metadata": {"source": "Bloomberg", "category": "macro", "published_date": "2025-05-11", "tickers_mentioned": ""},
    },
    {
        "text": "Givaudan reports record fragrance division sales driven by luxury perfume demand in Asia. The Swiss specialty chemicals company raised its mid-term organic growth target to 5-7%. Shares hit an all-time high of CHF 4,100 in afternoon trading.",
        "metadata": {"source": "Financial Times", "category": "equity", "published_date": "2025-05-10", "tickers_mentioned": "GIVN"},
    },
]


def _init_sqlite() -> dict[str, int]:
    """Drop and recreate all SQLite tables, insert mock data. Returns record counts."""
    # Ensure parent directory exists
    db_path = Path(_SQLITE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(_SQLITE_PATH)
    try:
        # Drop existing tables
        tables = ["market_movements", "real_estate_investments", "trade_operations", "portfolio", "customer_profile"]
        for table in tables:
            conn.execute(f"DROP TABLE IF EXISTS {table}")
        conn.commit()

        # Recreate schema from schema.sql
        schema_sql = _SCHEMA_PATH.read_text()
        conn.executescript(schema_sql)

        # Insert customer profile
        conn.execute(
            """INSERT INTO customer_profile (id, name, risk_appetite, investment_horizon, esg_preference,
               preferred_sectors, total_aum, kyc_status, onboarding_date)
               VALUES (:id, :name, :risk_appetite, :investment_horizon, :esg_preference,
               :preferred_sectors, :total_aum, :kyc_status, :onboarding_date)""",
            CUSTOMER_PROFILE,
        )

        # Insert portfolio positions
        for pos in PORTFOLIO_POSITIONS:
            conn.execute(
                """INSERT INTO portfolio (ticker, quantity, purchase_price, current_price, currency, sector)
                   VALUES (:ticker, :quantity, :purchase_price, :current_price, :currency, :sector)""",
                pos,
            )

        # Insert real estate investments
        for inv in REAL_ESTATE_INVESTMENTS:
            conn.execute(
                """INSERT INTO real_estate_investments (property_type, location, current_value,
                   acquisition_price, acquisition_date, rental_yield_percent, status)
                   VALUES (:property_type, :location, :current_value, :acquisition_price,
                   :acquisition_date, :rental_yield_percent, :status)""",
                inv,
            )

        # Insert trade operations
        for trade in TRADE_OPERATIONS:
            conn.execute(
                """INSERT INTO trade_operations (ticker, quantity, value, operation_type, timestamp)
                   VALUES (:ticker, :quantity, :value, :operation_type, :timestamp)""",
                trade,
            )

        # Insert market movements
        for movement in MARKET_MOVEMENTS:
            conn.execute(
                """INSERT INTO market_movements (ticker, company_name, sector, price_change,
                   percentage_change, current_price, volume, timestamp)
                   VALUES (:ticker, :company_name, :sector, :price_change, :percentage_change,
                   :current_price, :volume, :timestamp)""",
                movement,
            )

        conn.commit()

        # Get record counts
        counts = {}
        for table in ["customer_profile", "portfolio", "real_estate_investments", "trade_operations", "market_movements"]:
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cursor.fetchone()[0]

        return counts
    finally:
        conn.close()


def _init_chromadb(openai_client: OpenAI) -> int:
    """Drop and recreate ChromaDB collection, insert news with embeddings. Returns count."""
    # Ensure directory exists
    chroma_path = Path(_CHROMA_PATH)
    chroma_path.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=_CHROMA_PATH)

    # Drop existing collection if it exists.
    # chromadb >=1.x raises NotFoundError (not ValueError) when it's absent.
    try:
        client.delete_collection(name=_COLLECTION_NAME)
    except Exception:
        pass  # Collection doesn't exist

    # Create fresh collection
    collection = client.create_collection(
        name=_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    # Generate embeddings for all news articles
    texts = [article["text"] for article in NEWS_ARTICLES]

    response = openai_client.embeddings.create(
        input=texts,
        model="text-embedding-3-small",
    )

    embeddings = [item.embedding for item in response.data]

    # Insert into ChromaDB
    ids = [f"news_{i:03d}" for i in range(len(NEWS_ARTICLES))]
    metadatas = [article["metadata"] for article in NEWS_ARTICLES]

    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    return collection.count()


def main() -> None:
    """Initialize both databases with mock data."""
    # Check OpenAI API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    openai_client = OpenAI(api_key=api_key, http_client=_HTTP_CLIENT)

    # Initialize SQLite
    print("Initializing SQLite database...")
    try:
        sqlite_counts = _init_sqlite()
    except Exception as e:
        print(f"ERROR: SQLite initialization failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Initialize ChromaDB with embeddings
    print("Initializing ChromaDB collection (generating embeddings)...")
    try:
        news_count = _init_chromadb(openai_client)
    except Exception as e:
        print(f"ERROR: ChromaDB initialization failed (embedding API may be unavailable): {e}", file=sys.stderr)
        sys.exit(1)

    # Print results
    print("\nInitialization complete!")
    print("-" * 40)
    for table, count in sqlite_counts.items():
        print(f"  {table}: {count} records")
    print(f"  market_news (ChromaDB): {news_count} documents")
    print("-" * 40)


if __name__ == "__main__":
    main()
