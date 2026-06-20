"""Database initialization script for a SECOND demo scenario.

A copy of init_db.py that builds an INDEPENDENT database, so the primary database
built by init_db.py is never touched. It writes to its own SQLite file + ChromaDB
directory (``data/client2/`` by default) using the SAME schema (schema.sql).

Runnable as: python -m src.data.init_db_client2  (from the speech-to-text/ dir)

To load THIS scenario into the app/data layer, point the data-layer env vars at
its files, e.g.:

    DATA_SQLITE_PATH=data/client2/portfolio.db \\
    DATA_CHROMA_PATH=data/client2/chroma \\
    python -m src.postcall.api   # (or whatever consumes db.py)

Scenario: same client as init_db.py — Dr. Maximilian Keller, with his recycled
base profile and Swiss financial base — but oriented to NICHE MARKETS. The news
is dominated by passion assets (fine art, wine, whisky, watches, classic cars,
color diamonds, music royalties) and the last call surfaces them, demonstrating
the system filling a knowledge gap the RM typically does not have. Mock data
follows DATA_SPEC.md: everything is a time series up to t (the last call,
2026-06-19); the risk series stops at t-1; the last call's computed fields are None.
"""

import json
import os
import random
import sys
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Load .env from the speech-to-text dir (three levels up from this file)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

import chromadb
from openai import OpenAI

from src.data import DataLayerError

# Use a custom httpx client to bypass corporate proxy SSL issues
_HTTP_CLIENT = httpx.Client(verify=False)

# Resolve paths. DEDICATED env vars + a distinct default ("data/client2/") so
# running this script can NEVER overwrite the primary database ("data/portfolio.db"),
# regardless of any DATA_SQLITE_PATH that may be set.
_SPEECH_TO_TEXT_DIR = Path(__file__).resolve().parent.parent.parent
_SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
_SQLITE_PATH = os.environ.get("DATA_SQLITE_PATH_CLIENT2", str(_SPEECH_TO_TEXT_DIR / "data" / "client2" / "portfolio.db"))
_CHROMA_PATH = os.environ.get("DATA_CHROMA_PATH_CLIENT2", str(_SPEECH_TO_TEXT_DIR / "data" / "client2" / "chroma"))

# Collection name (same as the primary client)
_COLLECTION_NAME = "market_news"

# customer_id used for calls / risk rows that don't specify one (recycled Keller).
_DEFAULT_CUSTOMER_ID = 1


# ============================================================================
#  SCENARIO DATA — Dr. Maximilian Keller (recycled), niche-markets focus.
#  Timeline ends at t = 2026-06-19.
# ============================================================================

# Recycled base profile (matches init_db.py's Keller).
CUSTOMER_PROFILE = {
    "id": 1,
    "name": "Dr. Maximilian Keller",
    "risk_appetite": "moderate",            # official/stated profile (never updated)
    "investment_horizon": "long_term",
    "esg_preference": "moderate",
    "preferred_sectors": "technology,healthcare,financials,energy",
    "total_aum": 47500000.00,
    "kyc_status": "verified",
    "onboarding_date": "2024-06-19",   # 2-year relationship; last call is t = 2026-06-19
}

# Recycled Swiss financial base.
PORTFOLIO_POSITIONS = [
    {"ticker": "NESN", "quantity": 1200, "purchase_price": 98.50, "current_price": 107.80, "currency": "CHF", "sector": "consumer staples"},
    {"ticker": "NOVN", "quantity": 800, "purchase_price": 82.30, "current_price": 91.45, "currency": "CHF", "sector": "healthcare"},
    {"ticker": "ROG", "quantity": 350, "purchase_price": 245.60, "current_price": 258.90, "currency": "CHF", "sector": "healthcare"},
    {"ticker": "UBSG", "quantity": 2000, "purchase_price": 24.80, "current_price": 28.35, "currency": "CHF", "sector": "financials"},
    {"ticker": "ZURN", "quantity": 600, "purchase_price": 450.20, "current_price": 478.60, "currency": "CHF", "sector": "insurance"},
    {"ticker": "AAPL", "quantity": 500, "purchase_price": 142.50, "current_price": 198.30, "currency": "USD", "sector": "technology"},
    {"ticker": "MSFT", "quantity": 300, "purchase_price": 280.00, "current_price": 430.50, "currency": "USD", "sector": "technology"},
    {"ticker": "ASML", "quantity": 150, "purchase_price": 580.00, "current_price": 600.00, "currency": "EUR", "sector": "technology"},
]

REAL_ESTATE_INVESTMENTS = [
    {"property_type": "residential", "location": "Zurich, Seefeld", "current_value": 4800000.00, "acquisition_price": 3900000.00, "acquisition_date": "2017-06-20", "rental_yield_percent": 3.2, "status": "active"},
    {"property_type": "commercial", "location": "Geneva, Rue du Rhone", "current_value": 8500000.00, "acquisition_price": 7200000.00, "acquisition_date": "2019-11-05", "rental_yield_percent": 4.8, "status": "active"},
    {"property_type": "residential", "location": "Lugano, Paradiso", "current_value": 2200000.00, "acquisition_price": 1950000.00, "acquisition_date": "2021-03-12", "rental_yield_percent": 2.9, "status": "active"},
    {"property_type": "land", "location": "Zug, Oberägeri", "current_value": 1500000.00, "acquisition_price": 1200000.00, "acquisition_date": "2022-08-01", "rental_yield_percent": None, "status": "active"},
    {"property_type": "commercial", "location": "Basel, Aeschenvorstadt", "current_value": 3100000.00, "acquisition_price": 3400000.00, "acquisition_date": "2020-01-15", "rental_yield_percent": 5.1, "status": "sold"},
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

# --- market_movements: deterministic daily (weekday) time series per ticker,
#     ending exactly at the portfolio current_price on t (2026-06-19). ----------
_MARKET_ANCHOR_T = datetime(2026, 6, 19, 16, 0, 0)  # last trading timestamp = t
_MARKET_DAYS = 30  # number of trading-day points per ticker
# ticker -> (company_name, sector, start_price, end_price=current, base_volume)
_MARKET_SPEC = {
    "NESN": ("Nestle SA", "consumer staples", 104.00, 107.80, 4_500_000),
    "NOVN": ("Novartis AG", "healthcare", 94.00, 91.45, 3_800_000),
    "ROG": ("Roche Holding AG", "healthcare", 250.00, 258.90, 1_900_000),
    "UBSG": ("UBS Group AG", "financials", 27.00, 28.35, 8_000_000),
    "ZURN": ("Zurich Insurance Group", "insurance", 470.00, 478.60, 980_000),
    "AAPL": ("Apple Inc.", "technology", 205.00, 198.30, 50_000_000),
    "MSFT": ("Microsoft Corp.", "technology", 415.00, 430.50, 28_000_000),
    "ASML": ("ASML Holding NV", "technology", 660.00, 600.00, 3_400_000),
}


def _build_market_movements() -> list[dict]:
    """Build a weekday price series per ticker that lands exactly on end_price at t."""
    rng = random.Random(20260619)  # fixed seed -> reproducible series
    # collect _MARKET_DAYS weekday timestamps ending at the anchor
    dates: list[datetime] = []
    d = _MARKET_ANCHOR_T
    while len(dates) < _MARKET_DAYS:
        if d.weekday() < 5:  # Mon-Fri
            dates.append(d)
        d -= timedelta(days=1)
    dates.reverse()

    rows: list[dict] = []
    n = len(dates)
    for ticker, (name, sector, start, end, base_vol) in _MARKET_SPEC.items():
        prev = None
        for i, dt in enumerate(dates):
            frac = i / (n - 1)
            base = start + (end - start) * frac
            if i == n - 1:
                price = float(end)  # pin the final point to portfolio current_price
            else:
                price = round(base + (rng.random() - 0.5) * start * 0.02, 2)
                if price <= 0:
                    price = round(start * 0.5, 2)
            if prev is None:
                change, pct = 0.0, 0.0
            else:
                change = round(price - prev, 2)
                pct = round((change / prev) * 100, 2)
            rows.append({
                "ticker": ticker,
                "company_name": name,
                "sector": sector,
                "price_change": change,
                "percentage_change": pct,
                "current_price": price,
                "volume": int(base_vol * (0.8 + 0.4 * rng.random())),
                "timestamp": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            })
            prev = price
    return rows


MARKET_MOVEMENTS = _build_market_movements()

# --- market_news (ChromaDB). NICHE-MARKET focus: passion assets dominate, plus
#     June-2026 macro and Keller's Swiss holdings. category extends the base set
#     with "commodities"/"alternatives" (ChromaDB metadata is unconstrained). ----
NEWS_ARTICLES = [
    # --- alternatives / passion assets (the niche, RM-blind-spot angle) ---
    {"text": "Fine art, rare wine, classic cars and luxury watches are increasingly treated as part of a real-assets strategy for diversification and long-term appreciation. They act as inflation hedges and stores of value, but carry valuation challenges, illiquidity, and require specialized knowledge and authenticity verification.", "metadata": {"source": "Knight Frank", "category": "alternatives", "published_date": "2026-06-10", "tickers_mentioned": ""}},
    {"text": "Unlike public markets, collectible assets trade thinly and depend on a limited pool of buyers. Auction houses such as Sotheby's and Christie's set reference valuations, but pricing remains opaque. Advisors typically recommend keeping such holdings a small share of total wealth.", "metadata": {"source": "Barron's", "category": "alternatives", "published_date": "2026-06-05", "tickers_mentioned": ""}},
    {"text": "Royalty income from music catalogs, patents, trademarks and licensing is drawing interest as an alternative asset largely uncorrelated to public markets. Catalogs can generate steady cash flow, but valuation hinges on usage trends, rights complexity, and contract structures.", "metadata": {"source": "Financial Times", "category": "alternatives", "published_date": "2026-06-08", "tickers_mentioned": ""}},
    {"text": "Beyond music, IP and royalty streams from books, patents and licensing agreements are being structured into investable vehicles. The appeal lies in predictable, inflation-linked income, though liquidity is limited and specialized due diligence is essential.", "metadata": {"source": "Bloomberg", "category": "alternatives", "published_date": "2026-06-03", "tickers_mentioned": ""}},
    {"text": "The global art market is valued around $1.7 trillion with annual sales above $68 billion. Fine art has historically returned roughly 8.5% per year since 1950, and blue-chip works have outpaced many traditional assets, with the Artprice100 index up around 56% since 2018.", "metadata": {"source": "Artprice", "category": "alternatives", "published_date": "2026-06-09", "tickers_mentioned": ""}},
    {"text": "Despite strong headline returns, art carries high transaction costs (often 20-25%), opaque pricing, and authenticity risk. Valuations depend heavily on provenance and usually require expert advisory or art funds. It suits long horizons and should remain a measured share of total wealth.", "metadata": {"source": "Barron's", "category": "alternatives", "published_date": "2026-06-04", "tickers_mentioned": ""}},
    {"text": "Fine wine has risen more than 37% over ten years and is attracting ultra-high-net-worth investors, with over a third already active owners per global surveys. The market is tracked in real time by Liv-ex, offering institutional-grade price indices and trading data.", "metadata": {"source": "Liv-ex", "category": "alternatives", "published_date": "2026-06-09", "tickers_mentioned": ""}},
    {"text": "A recent correction in fine wine prices has created more attractive entry levels for long-term buyers. Bordeaux's classification dates to 1855 and the secondary market spans generations, but liquidity depends on auction houses and collector networks.", "metadata": {"source": "Liv-ex", "category": "alternatives", "published_date": "2026-06-02", "tickers_mentioned": ""}},
    {"text": "Rare and aged whisky has been among the strongest luxury-asset performers. Cask-aged whisky is especially attractive because the spirit continues to mature and gain value while stored, and limited bottlings from prestigious distilleries command premium prices.", "metadata": {"source": "Knight Frank", "category": "alternatives", "published_date": "2026-06-07", "tickers_mentioned": ""}},
    {"text": "Luxury watches have appreciated around 125% over ten years, the strongest gain among tracked luxury categories. Vintage Patek Philippe, Rolex and Audemars Piguet pieces drive much of the demand, though condition, rarity and provenance are decisive for value.", "metadata": {"source": "Knight Frank", "category": "alternatives", "published_date": "2026-06-06", "tickers_mentioned": ""}},
    {"text": "Classic cars from the late 1980s to early 2000s are now entering collectible territory, often outperforming traditional classics. The segment rewards specialist knowledge, with condition, originality and restoration history heavily influencing value.", "metadata": {"source": "Hagerty", "category": "alternatives", "published_date": "2026-06-06", "tickers_mentioned": ""}},
    {"text": "Fancy color diamonds remain a store of value sought by collectors for their rarity. Recent landmark auction sales include a 9.51-carat blue diamond at $25.6 million. More maisons are entering the market as clients seek stones that hold value, though the segment is highly illiquid.", "metadata": {"source": "Sotheby's", "category": "alternatives", "published_date": "2026-06-01", "tickers_mentioned": ""}},
    # --- macro / commodities / Swiss real estate ---
    {"text": "Gold is trading around $4,100 per ounce after a sharp correction from earlier highs near $5,000. A stronger dollar and elevated Treasury yields have weighed on the metal, while investors weigh it as a hedge amid geopolitical stress.", "metadata": {"source": "Reuters", "category": "commodities", "published_date": "2026-06-18", "tickers_mentioned": ""}},
    {"text": "Despite the recent pullback, structural demand for gold remains intact, driven by central-bank buying and persistent geopolitical uncertainty. Analysts see the $4,000 level as a key support zone.", "metadata": {"source": "Bloomberg", "category": "commodities", "published_date": "2026-06-15", "tickers_mentioned": ""}},
    {"text": "Core CPI rose just 0.2% month-over-month in May, down from 0.4% in April, suggesting underlying inflation is not broadening. Most of the headline pressure came from energy prices.", "metadata": {"source": "Bloomberg", "category": "macro", "published_date": "2026-06-11", "tickers_mentioned": ""}},
    {"text": "The Federal Reserve's June meeting marks the first under new leadership. With inflation above target but driven by geopolitical factors, the rate path has become highly uncertain, keeping markets on edge.", "metadata": {"source": "Reuters", "category": "macro", "published_date": "2026-06-13", "tickers_mentioned": ""}},
    {"text": "Prime Swiss real estate around Zurich and Geneva's lakefront remains resilient as investors seek stability. Luxury residential prices are holding firm, while peripheral commercial space sees softer demand.", "metadata": {"source": "Credit Suisse Research", "category": "real_estate", "published_date": "2026-06-14", "tickers_mentioned": ""}},
    {"text": "Swiss ESG funds continue to attract inflows, with sustainable strategies now a large share of total fund assets. Technology and healthcare remain the most popular ESG-screened sectors.", "metadata": {"source": "SIX Swiss Exchange", "category": "macro", "published_date": "2026-06-11", "tickers_mentioned": ""}},
    # --- Keller's Swiss holdings (for opportunity-delta / proposal grounding) ---
    {"text": "Nestle announced a further share buyback as it streamlines its portfolio, divesting underperforming brands while doubling down on health science and premium coffee. The defensive name remains a core Swiss blue chip.", "metadata": {"source": "Financial Times", "category": "equity", "published_date": "2026-06-10", "tickers_mentioned": "NESN"}},
    {"text": "Novartis reported stronger-than-expected quarterly results with core operating income up double digits, raising full-year guidance on robust demand for key oncology and immunology products.", "metadata": {"source": "Bloomberg", "category": "equity", "published_date": "2026-05-28", "tickers_mentioned": "NOVN"}},
    {"text": "Roche's new Alzheimer's therapy continues to show strong Phase 3 data, with regulators granting expedited review. The Basel company's shares outperformed the broader SPI index on the news.", "metadata": {"source": "Financial Times", "category": "equity", "published_date": "2026-06-05", "tickers_mentioned": "ROG"}},
    {"text": "UBS completed the final integration of Credit Suisse's wealth operations, with cost synergies ahead of schedule. The combined group is now among the world's largest wealth managers.", "metadata": {"source": "NZZ", "category": "equity", "published_date": "2026-05-30", "tickers_mentioned": "UBSG"}},
    {"text": "Zurich Insurance Group reported record first-half operating profit, with strong property-casualty performance and a raised dividend outlook.", "metadata": {"source": "Bloomberg", "category": "equity", "published_date": "2026-06-09", "tickers_mentioned": "ZURN"}},
    {"text": "Apple unveiled new on-device AI features expected to drive an upgrade cycle across its premium hardware, with services revenue continuing to expand at a double-digit pace.", "metadata": {"source": "CNBC", "category": "equity", "published_date": "2026-06-16", "tickers_mentioned": "AAPL"}},
    {"text": "Microsoft Azure reported strong double-digit revenue growth driven by enterprise AI adoption, with European corporate clients among the fastest adopters.", "metadata": {"source": "Bloomberg", "category": "equity", "published_date": "2026-06-12", "tickers_mentioned": "MSFT"}},
    {"text": "ASML reported a record backlog as chip manufacturers race to secure EUV lithography capacity, and raised its revenue guidance citing strong demand from AI infrastructure build-out.", "metadata": {"source": "Bloomberg", "category": "equity", "published_date": "2026-06-03", "tickers_mentioned": "ASML"}},
    {"text": "The Dutch government, under intensified US pressure, sharply expanded export-control restrictions on ASML's advanced DUV and EUV lithography systems bound for China. ASML warned the curbs could cut near-term revenue by a high-single-digit percentage, with China accounting for roughly a fifth of system sales, and flagged risk to its order outlook. The shares fell around 7% in Amsterdam.", "metadata": {"source": "Reuters", "category": "geopolitical", "published_date": "2026-06-17", "tickers_mentioned": "ASML"}},
]

# --- calls: 11 calls. 10 PAST calls (2024-06 -> 2026-03) span the 2-year
#     relationship from onboarding; each carries ONLY a mocked, "as-if-LLM-extracted"
#     risk profile (score + tag) under insights_json — no other extraction is done on
#     them. The LAST call (11, t=2026-06-19) leaves all computed fields None for the
#     pipeline to infer with the LLM. The `risk_score` field on each past call is the
#     mocked extraction point and also seeds risk_profile_history (see below). --------
CALLS = [
    {
        "customer_id": 1,
        "call_date": "2024-07-15T10:00:00Z",
        "duration_seconds": 600,
        "channel": "phone",
        "transcript": (
            "RM: Dr. Keller, welcome aboard. Now that the account is set up, let's talk about how you like to invest.\n"
            "Client: I'm a long-term investor. Moderate risk suits me - Swiss blue chips, healthcare, a little US technology. I'd rather sleep well than chase the last few percent.\n"
            "RM: That's a sensible, balanced starting point. We'll build the core around exactly that.\n"
            "Client: Good. Let's get it working."
        ),
        "summary": "Onboarding follow-up; client sets out a balanced, moderate, long-term mandate around Swiss blue chips, healthcare and some US tech.",
        "sentiment_score": 0.5,
        "sentiment_label": "positive",
        "risk_signal": "moderate",
        "risk_score": 6.0,
        "topics": ["mandate", "balanced allocation", "long-term"],
    },
    {
        "customer_id": 1,
        "call_date": "2024-09-10T11:30:00Z",
        "duration_seconds": 540,
        "channel": "phone",
        "transcript": (
            "RM: First review since we set things up. The book has had a steady start - Nestle and Roche calm, the US tech names strong.\n"
            "Client: I'm pleased. The growth has been welcome and nothing has surprised me.\n"
            "RM: Comfortable keeping the same balance for now?\n"
            "Client: Yes. Steady as she goes."
        ),
        "summary": "First portfolio review; client pleased with steady performance and comfortable holding the balanced allocation.",
        "sentiment_score": 0.4,
        "sentiment_label": "positive",
        "risk_signal": "moderate",
        "risk_score": 5.8,
        "topics": ["portfolio review", "balanced allocation"],
    },
    {
        "customer_id": 1,
        "call_date": "2024-11-12T14:00:00Z",
        "duration_seconds": 540,
        "channel": "phone",
        "transcript": (
            "RM: Markets have been a little jumpy lately. How are you feeling?\n"
            "Client: Calm, mostly. Though I've started wondering whether I'm too concentrated in equities.\n"
            "RM: We could broaden into other real assets over time - property, perhaps some alternatives.\n"
            "Client: I like that idea. I already have the apartments. Something beyond stocks and bonds, maybe.\n"
            "RM: We can explore it. For now the core stays intact.\n"
            "Client: Agreed. Keep it measured."
        ),
        "summary": "Client raises equity concentration and an interest in broadening into real assets and alternatives.",
        "sentiment_score": 0.2,
        "sentiment_label": "neutral",
        "risk_signal": "moderate",
        "risk_score": 5.7,
        "topics": ["diversification", "real assets", "concentration"],
    },
    {
        "customer_id": 1,
        "call_date": "2025-01-20T14:00:00Z",
        "duration_seconds": 720,
        "channel": "video",
        "transcript": (
            "RM: Since the last review I wanted to revisit your risk. Equities are still the bulk of the book.\n"
            "Client: With all the noise in the world, I've been feeling a little more cautious lately.\n"
            "RM: That's reasonable. We can trim some equity risk and add stability.\n"
            "Client: Yes. And honestly - I have a small art collection and a wine cellar I've built over the years. I've started to wonder if those count as part of my wealth.\n"
            "RM: They can be considered real assets. We could look at how they'd fit one day.\n"
            "Client: I'd like that. I'd like to think more holistically about what I own.\n"
            "RM: Leave it with me - we'll de-risk slightly now."
        ),
        "summary": "Volatility prompts mild de-risking; client first raises his art collection and wine cellar as possible wealth.",
        "sentiment_score": -0.1,
        "sentiment_label": "neutral",
        "risk_signal": "moderate",
        "risk_score": 5.5,
        "topics": ["de-risking", "collectibles", "art and wine"],
    },
    {
        "customer_id": 1,
        "call_date": "2025-03-18T10:30:00Z",
        "duration_seconds": 480,
        "channel": "phone",
        "transcript": (
            "RM: Quick check-in on positioning. Anything on your mind?\n"
            "Client: Just the headlines - rates, geopolitics. I'd rather not take on any new risk right now.\n"
            "RM: Understood. We'll hold quality and avoid adding beta.\n"
            "Client: Exactly. Steady hands."
        ),
        "summary": "Brief check-in; client wary of headlines and unwilling to add new risk, preferring to hold quality.",
        "sentiment_score": 0.0,
        "sentiment_label": "neutral",
        "risk_signal": "moderate",
        "risk_score": 5.4,
        "topics": ["caution", "hold quality"],
    },
    {
        "customer_id": 1,
        "call_date": "2025-05-14T09:30:00Z",
        "duration_seconds": 540,
        "channel": "phone",
        "transcript": (
            "RM: Spring review. The Swiss names have been resilient; tech has run hard.\n"
            "Client: The tech gains are nice, but they now feel like a large part of the pot. It makes me a little uneasy.\n"
            "RM: We can start to think about trimming that concentration gradually.\n"
            "Client: Gradually, yes. No sudden moves."
        ),
        "summary": "Client first voices unease about the size of the tech position and is open to trimming concentration gradually.",
        "sentiment_score": -0.1,
        "sentiment_label": "neutral",
        "risk_signal": "moderate",
        "risk_score": 5.2,
        "topics": ["tech concentration", "trim", "gradual"],
    },
    {
        "customer_id": 1,
        "call_date": "2025-07-22T11:00:00Z",
        "duration_seconds": 540,
        "channel": "video",
        "transcript": (
            "RM: Mid-year review. How are you thinking about the balance of growth versus stability?\n"
            "Client: Stability is climbing up my list. I'm not getting younger, and I value calm more than the extra percent.\n"
            "RM: We can keep tilting toward steadier, quality holdings.\n"
            "Client: Please do. That's the direction I want."
        ),
        "summary": "Client signals a clearer preference for stability over growth and asks to keep tilting toward steadier holdings.",
        "sentiment_score": -0.1,
        "sentiment_label": "neutral",
        "risk_signal": "moderate",
        "risk_score": 5.0,
        "topics": ["stability over growth", "quality tilt"],
    },
    {
        "customer_id": 1,
        "call_date": "2025-09-16T09:30:00Z",
        "duration_seconds": 540,
        "channel": "phone",
        "transcript": (
            "RM: Markets wobbled over the summer. Did it unsettle you?\n"
            "Client: A little. I keep my ESG preferences in mind too - I care about that - but mostly I want to feel protected if things turn.\n"
            "RM: We can keep the quality Swiss names and healthcare front and centre and keep beta low.\n"
            "Client: Good. Protected and sustainable. That's where I am."
        ),
        "summary": "Summer volatility nudges the client further toward protection; reaffirms ESG preferences alongside a low-beta, quality stance.",
        "sentiment_score": -0.2,
        "sentiment_label": "neutral",
        "risk_signal": "moderate",
        "risk_score": 4.8,
        "topics": ["protection", "ESG", "low beta"],
    },
    {
        "customer_id": 1,
        "call_date": "2025-11-11T09:30:00Z",
        "duration_seconds": 600,
        "channel": "phone",
        "transcript": (
            "RM: Given the volatility this autumn, I wanted to check in on positioning.\n"
            "Client: I'd like more stability. Capital preservation matters more to me now than it used to.\n"
            "RM: We can shift toward a more conservative stance - reduce some of the higher-beta tech.\n"
            "Client: Yes. And keep my ESG preferences in mind; I care about that.\n"
            "RM: Of course. We'll keep the quality Swiss names and healthcare.\n"
            "Client: Good. Stability and quality. That's where I am now."
        ),
        "summary": "Client crosses into a conservative stance, prioritising capital preservation and ESG over higher-beta tech.",
        "sentiment_score": -0.3,
        "sentiment_label": "negative",
        "risk_signal": "conservative",
        "risk_score": 4.6,
        "topics": ["capital preservation", "ESG", "reduce tech"],
    },
    {
        "customer_id": 1,
        "call_date": "2026-03-10T10:00:00Z",
        "duration_seconds": 540,
        "channel": "video",
        "transcript": (
            "RM: Start-of-year review. You've been steering toward preservation - shall we keep that course?\n"
            "Client: Yes. I want to protect what I've built. Stability over growth, firmly now.\n"
            "RM: Then we hold the conservative tilt and keep looking for ballast that doesn't move with equities.\n"
            "Client: That's exactly it. Ballast."
        ),
        "summary": "Client firmly confirms the conservative, preservation-first stance and asks for ballast uncorrelated with equities.",
        "sentiment_score": -0.2,
        "sentiment_label": "neutral",
        "risk_signal": "conservative",
        "risk_score": 4.5,
        "topics": ["capital preservation", "conservative", "uncorrelated assets"],
    },
    {
        # LAST CALL (t). Computed fields left None -> inferred by the pipeline.
        "customer_id": 1,
        "call_date": "2026-06-19T15:00:00Z",
        "duration_seconds": 1680,
        "channel": "video",
        "transcript": (
            "RM: Dr. Keller, it's good to see you. Before anything else - how is Sophie? Last time we spoke she was expecting.\n"
            "Client: A grandfather now, if you can believe it. Little Emma arrived in April. It changes how you look at everything, Thomas. You start thinking less about the next quarter and more about the next generation.\n"
            "RM: Congratulations, truly. And how have you been keeping? You mentioned the back.\n"
            "Client: The surgery went well, thank you. I'm slower than I was, but I'm well. Though I'll admit, between the operation and losing my old friend Heinrich in the spring, it's been a year that makes a man take stock.\n"
            "RM: I'm sorry about Heinrich. Take all the time you need today.\n"
            "Client: Thank you. Let's talk - I have a lot on my mind. First, the markets. I watch the news and it's gold swinging around four thousand, energy prices jumping, all this noise about the new Fed chair. Honestly, it unsettles me more than it used to.\n"
            "RM: That's understandable. How is it changing the way you want to be positioned?\n"
            "Client: I want to sleep at night, frankly. I keep coming back to the idea of holding a little gold as a hedge - not to make money, just so I'm not so exposed if things turn. Is that foolish?\n"
            "RM: Not at all. A modest gold allocation as portfolio insurance is very defensible in this environment.\n"
            "Client: Good. And while we're being honest - the technology names. Apple, Microsoft, the Dutch chip company. They've been wonderful to me, but they're now such a large part of the pot. It worries me. If one of them stumbled I'd feel it badly.\n"
            "RM: So you'd be open to trimming some of that concentration and rotating into something steadier?\n"
            "Client: I think so. I'm not chasing the last few percent anymore. Stability matters more to me now than growth - I'd rather protect what Emma and Sophie will one day inherit than gamble it.\n"
            "RM: That's a clear signal, and an important one. We can reduce the tech weighting and lean into the quality Swiss names - Nestle, Roche, Zurich - and keep your ESG preferences front and centre.\n"
            "Client: Yes. The sustainable side still matters to me, don't lose that.\n"
            "RM: Never. Now, you said there was more.\n"
            "Client: I mentioned this once before, a good while back, but we never took it anywhere. Over thirty years I've quietly built a proper collection - paintings, a serious wine cellar, a handful of watches, and a classic car I restored myself. I've always thought of them as my private passions, not as money. But with everything uncertain, I find myself wondering whether they're actually real investments I should be managing properly.\n"
            "RM: That's a wonderful question, and increasingly a serious one - passion assets are now treated as part of a real-assets strategy by many private banks.\n"
            "Client: Then I want to understand them properly. What is the art actually worth as an asset class? How liquid is fine wine, really - if I needed to sell, what would it cost me and how long would it take? And do these things hold their value when the stock market falls, or do they fall with it?\n"
            "RM: All the right questions. Correlation, liquidity, transaction costs, authenticity - they each behave differently.\n"
            "Client: That last point is what draws me. If they're genuinely uncorrelated with my equities, then perhaps they're part of the stability I've been searching for - not just things I love, but ballast.\n"
            "RM: Let me pull together a proper picture: market size and historical returns for art, wine, watches and collectible cars, the real transaction costs, and crucially how correlated they are with your Swiss and US holdings.\n"
            "Client: I'd value that enormously. I'll be honest with you, Thomas - I was a little disappointed the bank never raised any of this with me. During the worst of the volatility last autumn, I didn't hear from anyone for weeks. You I trust completely, but I did wonder whether Julius Baer was looking after me as a whole person, not just an account.\n"
            "RM: That's fair, and I take it personally. I should have reached out sooner, and I'll make sure you're never left in silence like that again.\n"
            "Client: I appreciate you saying so. It's why I keep working with you specifically.\n"
            "RM: Then let me earn it. I'll prepare three things: a modest gold hedge sized to your portfolio, a plan to gently reduce the tech concentration toward steadier income, and a full assessment of your collection as a genuine asset class. And separately, given Emma, perhaps we should revisit your estate and succession planning.\n"
            "Client: Yes - all of it. Especially the last part. Getting it right for Sophie and Emma is the thing that matters most to me now.\n"
            "RM: Understood. I'll have the collection analysis and the gold proposal ready for our next meeting.\n"
            "Client: Thank you. This is exactly the kind of advice I value - it's why I'm still here."
        ),
        "summary": None,
        "sentiment_score": None,
        "sentiment_label": None,
        "risk_signal": None,
        "topics": None,
    },
]

# --- risk_profile_history: the behavioural risk-score trend, onboarding -> t-1 ONLY
#     (no point at the 2026-06-19 last call; the pipeline infers that). It is the
#     onboarding starting point PLUS one mocked, as-if-LLM-extracted point per past
#     call (score + tag), derived directly from CALLS so the two never drift. The
#     series falls from moderate (6.0) to conservative (4.5) while the stated profile
#     stays "moderate" -> behavioural-drift signal. -------------------------------
_ONBOARDING_RISK = {
    "customer_id": 1, "assessed_date": "2024-06-19", "risk_appetite": "moderate",
    "risk_score": 6.0, "source": "onboarding", "note": "Initial onboarding assessment.",
}


def _build_risk_history() -> list[dict]:
    """Onboarding point + one mocked risk snapshot per PAST call (those carrying a
    `risk_score`). The last call has no risk_score, so it is naturally excluded."""
    history = [dict(_ONBOARDING_RISK)]
    for call in CALLS:
        score = call.get("risk_score")
        if score is None:
            continue
        history.append({
            "customer_id": call.get("customer_id", _DEFAULT_CUSTOMER_ID),
            "assessed_date": call["call_date"][:10],
            "risk_appetite": call.get("risk_signal"),
            "risk_score": score,
            "source": "call",
            "note": call.get("summary"),
        })
    return history


RISK_PROFILE_HISTORY = _build_risk_history()


def _init_sqlite() -> dict[str, int]:
    """Drop and recreate all SQLite tables in THIS scenario's DB, insert data."""
    # Ensure parent directory exists
    db_path = Path(_SQLITE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(_SQLITE_PATH)
    try:
        # Drop existing tables
        tables = ["calls", "risk_profile_history", "market_movements",
                  "real_estate_investments", "trade_operations", "portfolio", "customer_profile"]
        for table in tables:
            conn.execute(f"DROP TABLE IF EXISTS {table}")
        conn.commit()

        # Recreate schema from schema.sql
        schema_sql = _SCHEMA_PATH.read_text()
        conn.executescript(schema_sql)

        # Insert customer profile (skip if not filled in yet)
        if CUSTOMER_PROFILE:
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

        # Insert call history. `topics` is a list but stored as a JSON-string column.
        # PAST calls carry ONLY a mocked, as-if-LLM-extracted risk profile (score +
        # tag) under insights_json — no other extraction is ever run on history. The
        # LAST call (no risk_score) leaves insights_json NULL: the pipeline computes
        # its full extraction live.
        for call in CALLS:
            topics = call.get("topics")
            risk_score = call.get("risk_score")
            insights_json = (
                json.dumps({"risk": {
                    "inferred_risk_score": risk_score,
                    "inferred_risk_appetite": call.get("risk_signal"),
                }}) if risk_score is not None else None
            )
            conn.execute(
                """INSERT INTO calls (customer_id, call_date, duration_seconds, channel,
                   transcript, summary, sentiment_score, sentiment_label, risk_signal, topics, insights_json)
                   VALUES (:customer_id, :call_date, :duration_seconds, :channel,
                   :transcript, :summary, :sentiment_score, :sentiment_label, :risk_signal, :topics, :insights_json)""",
                {
                    "customer_id": call.get("customer_id", _DEFAULT_CUSTOMER_ID),
                    "call_date": call["call_date"],
                    "duration_seconds": call.get("duration_seconds"),
                    "channel": call.get("channel"),
                    "transcript": call["transcript"],
                    "summary": call.get("summary"),
                    "sentiment_score": call.get("sentiment_score"),
                    "sentiment_label": call.get("sentiment_label"),
                    "risk_signal": call.get("risk_signal"),
                    "topics": json.dumps(topics) if isinstance(topics, (list, dict)) else topics,
                    "insights_json": insights_json,
                },
            )

        # Insert risk-profile history
        for snapshot in RISK_PROFILE_HISTORY:
            conn.execute(
                """INSERT INTO risk_profile_history (customer_id, assessed_date, risk_appetite,
                   risk_score, source, note)
                   VALUES (:customer_id, :assessed_date, :risk_appetite, :risk_score, :source, :note)""",
                {
                    "customer_id": snapshot.get("customer_id", _DEFAULT_CUSTOMER_ID),
                    "assessed_date": snapshot["assessed_date"],
                    "risk_appetite": snapshot["risk_appetite"],
                    "risk_score": snapshot.get("risk_score"),
                    "source": snapshot.get("source"),
                    "note": snapshot.get("note"),
                },
            )

        conn.commit()

        # Get record counts
        counts = {}
        for table in ["customer_profile", "portfolio", "real_estate_investments",
                      "trade_operations", "market_movements", "calls", "risk_profile_history"]:
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

    # Drop existing collection if it exists
    try:
        client.delete_collection(name=_COLLECTION_NAME)
    except Exception:
        pass  # Collection doesn't exist (raise type varies across chromadb versions)

    # Create fresh collection
    collection = client.create_collection(
        name=_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    # Generate embeddings for all news articles
    texts = [article["text"] for article in NEWS_ARTICLES]
    if not texts:
        return collection.count()  # nothing to embed yet

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
    """Initialize the scenario's databases with its mock data."""
    # Initialize SQLite first (no API key needed).
    print(f"Initializing scenario SQLite database at: {_SQLITE_PATH}")
    try:
        sqlite_counts = _init_sqlite()
    except Exception as e:
        print(f"ERROR: SQLite initialization failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Initialize ChromaDB only if there is news to embed (needs OPENAI_API_KEY).
    news_count = 0
    if NEWS_ARTICLES:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("ERROR: OPENAI_API_KEY environment variable is not set "
                  "(required to embed NEWS_ARTICLES).", file=sys.stderr)
            sys.exit(1)
        openai_client = OpenAI(api_key=api_key, http_client=_HTTP_CLIENT)
        print("Initializing ChromaDB collection (generating embeddings)...")
        try:
            news_count = _init_chromadb(openai_client)
        except Exception as e:
            print(f"ERROR: ChromaDB initialization failed (embedding API may be unavailable): {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("No NEWS_ARTICLES yet — skipping ChromaDB embedding step.")

    # Print results
    print("\nInitialization complete!")
    print("-" * 40)
    for table, count in sqlite_counts.items():
        print(f"  {table}: {count} records")
    print(f"  market_news (ChromaDB): {news_count} documents")
    print("-" * 40)
    print(f"  SQLite: {_SQLITE_PATH}")
    print(f"  ChromaDB: {_CHROMA_PATH}")


if __name__ == "__main__":
    main()
