import os, sys
sys.path.insert(0, '.')
os.environ['DATA_SQLITE_PATH'] = '/nonexistent/dir/db.sqlite'
from src.data.db import get_portfolio
from src.data import DataLayerError

print("Testing get_portfolio with unreachable db...")
try:
    r = get_portfolio()
    print(f"get_portfolio succeeded: {len(r)} results")
except DataLayerError as e:
    print(f"DataLayerError raised: {e}")
except Exception as e:
    print(f"Other error: {type(e).__name__}: {e}")
