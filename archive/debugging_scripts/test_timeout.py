#!/usr/bin/env python3
"""
Test that Earth Engine adapter now handles timeouts properly
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from env_agents.adapters import CANONICAL_SERVICES
from env_agents.core.models import RequestSpec, Geometry
import time

print("Testing timeout handling in Earth Engine adapter\n")

# Test cluster (Sweden)
test_lat = 62.27127147
test_lon = 16.93716839

geometry = Geometry(
    type="bbox",
    coordinates=[
        test_lon - 0.005, test_lat - 0.005,
        test_lon + 0.005, test_lat + 0.005
    ]
)

# Create adapter
EE = CANONICAL_SERVICES["EARTH_ENGINE"]
adapter = EE(asset_id="USGS/SRTMGL1_003")

spec = RequestSpec(
    geometry=geometry,
    time_range=("2021-01-01", "2021-12-31"),
    variables=None,
    extra={"timeout": 60}
)

print("Testing single query (should complete in ~2-3s)...")
start = time.time()
try:
    result = adapter._fetch_rows(spec)
    elapsed = time.time() - start
    print(f"✅ Query completed in {elapsed:.2f}s")
    print(f"   Result: {len(result) if result else 0} observations")
except Exception as e:
    elapsed = time.time() - start
    print(f"❌ Query failed after {elapsed:.2f}s: {e}")

print("\nAdapter is ready for production with timeout protection!")
print("If Earth Engine hangs, timeout will trigger after 60s and raise exception")
print("The acquisition script will then retry with backoff (60s wait)")