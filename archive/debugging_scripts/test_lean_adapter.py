#!/usr/bin/env python3
"""
Test the new LEAN production Earth Engine adapter
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Fresh import
from env_agents.adapters.earth_engine.production_adapter import ProductionEarthEngineAdapter
from env_agents.core.models import RequestSpec, Geometry

print(f"✅ Loaded: {ProductionEarthEngineAdapter}")
print(f"   Module: {ProductionEarthEngineAdapter.__module__}")

# Test location
test_lat = 34.0997
test_lon = -115.4550

geometry = Geometry(
    type="bbox",
    coordinates=[test_lon - 0.005, test_lat - 0.005, test_lon + 0.005, test_lat + 0.005]
)

print(f"\n📍 Test: {test_lat}, {test_lon}")
print(f"🔧 Creating SRTM adapter...")

adapter = ProductionEarthEngineAdapter(asset_id="USGS/SRTMGL1_003")

spec = RequestSpec(
    geometry=geometry,
    time_range=("2021-01-01", "2021-12-31"),
    variables=None,
    extra={"timeout": 60}
)

print(f"🔍 Querying...")
import time
start = time.time()
result = adapter._fetch_rows(spec)
elapsed = time.time() - start

print(f"\n📊 Result: {type(result)}, length={len(result) if result else 0}")
print(f"⏱️  Time: {elapsed:.2f}s")

if result and len(result) > 0:
    print(f"✅ SUCCESS!")
    first = result[0]
    print(f"\n📝 First observation:")
    print(f"   observation_id: {first.get('observation_id')}")
    print(f"   variable: {first.get('variable')}")
    print(f"   value: {first.get('value')}")
    print(f"   source_version: {first.get('source_version')}")

    # Check for ABSENCE of bloat
    attrs = first.get('attributes', {})
    has_bloat = 'comprehensive_result' in attrs or 'folium_map' in str(attrs)

    if has_bloat:
        print(f"\n⚠️  WARNING: Still has visualization bloat!")
    else:
        print(f"\n🎉 LEAN: No visualization bloat!")
        print(f"   Attributes keys: {list(attrs.keys())}")
else:
    print(f"❌ FAILED: No data")