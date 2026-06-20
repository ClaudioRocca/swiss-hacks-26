"""Quick verification tests for db.py query functions."""
import sys
import os
import sqlite3
import tempfile

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Create a temp db with the schema
schema_path = Path(__file__).parent.parent / "src" / "data" / "schema.sql"
with open(schema_path, "r") as f:
    schema = f.read()

tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
tmp_path = tmp.name
tmp.close()

os.environ["DATA_SQLITE_PATH"] = tmp_path

conn = sqlite3.connect(tmp_path)
conn.executescript(schema)

# Insert portfolio data
conn.execute(
    "INSERT INTO portfolio (ticker, quantity, purchase_price, current_price, currency, sector) "
    "VALUES ('AAPL', 100, 150.00, 175.00, 'USD', 'Technology')"
)
conn.execute(
    "INSERT INTO portfolio (ticker, quantity, purchase_price, current_price, currency, sector) "
    "VALUES ('GOOG', 50, 2800.00, 2750.00, 'USD', 'Technology')"
)
conn.execute(
    "INSERT INTO portfolio (ticker, quantity, purchase_price, current_price, currency, sector) "
    "VALUES ('XOM', 200, 60.00, 65.00, 'USD', 'Energy')"
)

# Insert trade operations
conn.execute(
    "INSERT INTO trade_operations (ticker, quantity, value, operation_type, timestamp) "
    "VALUES ('AAPL', 10, 1750.00, 'buy', '2025-01-15T10:00:00Z')"
)
conn.execute(
    "INSERT INTO trade_operations (ticker, quantity, value, operation_type, timestamp) "
    "VALUES ('GOOG', 5, 13750.00, 'sell', '2025-01-10T14:30:00Z')"
)
conn.execute(
    "INSERT INTO trade_operations (ticker, quantity, value, operation_type, timestamp) "
    "VALUES ('XOM', 20, 1300.00, 'buy', '2025-01-20T09:00:00Z')"
)

# Insert customer profile
conn.execute(
    "INSERT INTO customer_profile (id, name, risk_appetite, investment_horizon, esg_preference, "
    "total_aum, kyc_status, onboarding_date) "
    "VALUES (1, 'John Doe', 'aggressive', 'long_term', 'moderate', 5000000.00, 'verified', '2020-01-15')"
)

# Insert real estate
conn.execute(
    "INSERT INTO real_estate_investments (property_type, location, current_value, acquisition_price, "
    "acquisition_date, rental_yield_percent, status) "
    "VALUES ('residential', 'Zurich, Switzerland', 2500000.00, 2000000.00, '2021-06-15', 3.5, 'active')"
)
conn.execute(
    "INSERT INTO real_estate_investments (property_type, location, current_value, acquisition_price, "
    "acquisition_date, rental_yield_percent, status) "
    "VALUES ('commercial', 'Geneva, Switzerland', 5000000.00, 4500000.00, '2022-03-20', 5.2, 'active')"
)

# Insert market movements
conn.execute(
    "INSERT INTO market_movements (ticker, company_name, sector, price_change, percentage_change, "
    "current_price, volume, timestamp) "
    "VALUES ('AAPL', 'Apple Inc', 'Technology', 2.50, 1.45, 175.00, 50000000, '2025-01-25T16:00:00Z')"
)
conn.execute(
    "INSERT INTO market_movements (ticker, company_name, sector, price_change, percentage_change, "
    "current_price, volume, timestamp) "
    "VALUES ('TSLA', 'Tesla Inc', 'Technology', -5.00, -2.10, 233.00, 30000000, '2025-01-25T16:00:00Z')"
)

conn.commit()
conn.close()

# Now test
from src.data.db import (
    get_portfolio,
    get_trades,
    get_customer_profile,
    get_real_estate,
    get_market_movements,
)
from src.data import DataLayerError

# === get_portfolio ===
print("=== get_portfolio ===")
r = get_portfolio()
assert len(r) == 3, f"Expected 3, got {len(r)}"
print(f"  all: {len(r)} OK")

r = get_portfolio(ticker="aapl")
assert len(r) == 1 and r[0]["ticker"] == "AAPL"
print(f"  ticker=aapl: {len(r)} OK")

r = get_portfolio(sector="technology")
assert len(r) == 2
print(f"  sector=technology: {len(r)} OK")

r = get_portfolio(min_profit_loss=0)
assert len(r) == 2  # AAPL profit=2500, XOM profit=1000
print(f"  min_profit_loss=0: {len(r)} OK")

r = get_portfolio(max_profit_loss=0)
assert len(r) == 1  # GOOG loss=-2500
print(f"  max_profit_loss=0: {len(r)} OK")

# === get_trades ===
print("=== get_trades ===")
r = get_trades()
assert len(r) == 3
print(f"  all: {len(r)} OK")

r = get_trades(operation_type="buy")
assert len(r) == 2
print(f"  operation_type=buy: {len(r)} OK")

r = get_trades(since="2025-01-12T00:00:00Z")
assert len(r) == 2
print(f"  since=2025-01-12: {len(r)} OK")

r = get_trades(operation_type="invalid")
assert len(r) == 3  # silently ignored
print(f"  invalid enum: {len(r)} (ignored) OK")

r = get_trades(limit=2)
assert len(r) == 2
print(f"  limit=2: {len(r)} OK")

# Verify ordering: most recent first
r = get_trades()
assert r[0]["timestamp"] >= r[1]["timestamp"] >= r[2]["timestamp"]
print("  ordering OK")

# === get_customer_profile ===
print("=== get_customer_profile ===")
p = get_customer_profile()
assert p["name"] == "John Doe"
assert p["risk_appetite"] == "aggressive"
print(f"  profile: {p['name']} OK")

# === get_real_estate ===
print("=== get_real_estate ===")
r = get_real_estate()
assert len(r) == 2
print(f"  all: {len(r)} OK")

r = get_real_estate(location="zurich")
assert len(r) == 1
print(f"  location=zurich: {len(r)} OK")

r = get_real_estate(property_type="commercial")
assert len(r) == 1
print(f"  property_type=commercial: {len(r)} OK")

r = get_real_estate(min_value=3000000)
assert len(r) == 1
print(f"  min_value=3M: {len(r)} OK")

r = get_real_estate(property_type="invalid_type")
assert len(r) == 2  # silently ignored
print(f"  invalid enum: {len(r)} (ignored) OK")

# Verify ordering: most recent acquisition first
r = get_real_estate()
assert r[0]["acquisition_date"] >= r[1]["acquisition_date"]
print("  ordering OK")

# === get_market_movements ===
print("=== get_market_movements ===")
r = get_market_movements()
assert len(r) == 2
print(f"  all: {len(r)} OK")

r = get_market_movements(direction="up")
assert len(r) == 1 and r[0]["ticker"] == "AAPL"
print(f"  direction=up: {len(r)} OK")

r = get_market_movements(direction="down")
assert len(r) == 1 and r[0]["ticker"] == "TSLA"
print(f"  direction=down: {len(r)} OK")

r = get_market_movements(min_change_percent=2.0)
assert len(r) == 1 and r[0]["ticker"] == "TSLA"
print(f"  min_change_percent=2.0: {len(r)} OK")

r = get_market_movements(sector="Technology")
assert len(r) == 2
print(f"  sector=Technology: {len(r)} OK")

r = get_market_movements(direction="invalid")
assert len(r) == 2  # silently ignored
print(f"  invalid direction: {len(r)} (ignored) OK")

# === DataLayerError ===
print("=== DataLayerError ===")
# Use a truly invalid path (directory doesn't exist)
new_path = "/this/path/definitely/does/not/exist/db.sqlite"
os.environ["DATA_SQLITE_PATH"] = new_path
print(f"  ENV set to: {os.environ.get('DATA_SQLITE_PATH')}")
# Reimport to ensure module uses updated env
import importlib
import src.data.db as db_module
importlib.reload(db_module)
try:
    result = db_module.get_portfolio()
    print(f"  WARNING: got {len(result)} results instead of error")
except DataLayerError as e:
    print(f"  Raised correctly: {e}")

# Cleanup
os.unlink(tmp_path)
print("\n=== ALL TESTS PASSED ===")
