#!/usr/bin/env python3
"""
Debug why clusters are returning no_data in 0.15s
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from env_agents.adapters import CANONICAL_SERVICES
from env_agents.core.models import RequestSpec, Geometry
import time

# Test cluster 192 (Sweden - should definitely have SRTM data)
test_lat = 62.27127147
test_lon = 16.93716839

print(f"Testing cluster 192: {test_lat}, {test_lon} (Sweden - land)")
print()

# Create geometry like production script
geometry = Geometry(
    type="bbox",
    coordinates=[
        test_lon - 0.005, test_lat - 0.005,
        test_lon + 0.005, test_lat + 0.005
    ]
)

print(f"Geometry: {geometry}")
print()

# Create adapter
EE = CANONICAL_SERVICES["EARTH_ENGINE"]
print(f"Creating adapter...")
adapter = EE(asset_id="USGS/SRTMGL1_003")
print(f"Adapter type: {type(adapter).__name__}")
print(f"Adapter asset_id: {adapter.asset_id}")
print()

# Create spec
spec = RequestSpec(
    geometry=geometry,
    time_range=("2021-01-01", "2021-12-31"),
    variables=None,
    extra={"timeout": 60}
)

print("Calling adapter._fetch_rows(spec)...")
start = time.time()
try:
    result = adapter._fetch_rows(spec)
    elapsed = time.time() - start

    print(f"\n⏱️  Time: {elapsed:.2f}s")
    print(f"Result type: {type(result)}")
    print(f"Result: {result}")

    if result and len(result) > 0:
        print(f"✅ SUCCESS: {len(result)} observations")
        print(f"First obs: {result[0]}")
    else:
        print(f"❌ NO DATA (but query completed)")

        # Check what the result actually is
        if result is None:
            print("   Result is None")
        elif result == []:
            print("   Result is empty list")
        elif not result:
            print(f"   Result is falsy: {result}")

except Exception as e:
    elapsed = time.time() - start
    print(f"\n❌ ERROR after {elapsed:.2f}s:")
    print(f"   {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()