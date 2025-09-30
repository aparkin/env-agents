#!/usr/bin/env python3
"""
Direct test to replicate notebook's SRTM success pattern
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from env_agents.adapters import CANONICAL_SERVICES
from env_agents.core.models import RequestSpec, Geometry

# Use same test location as notebook
test_lat = 34.0997
test_lon = -115.4550

# Create tight bbox exactly like notebook
tight_bbox = [test_lat - 0.005, test_lon - 0.005, test_lat + 0.005, test_lon + 0.005]
test_geometry = Geometry(type="bbox", coordinates=[tight_bbox[1], tight_bbox[0], tight_bbox[3], tight_bbox[2]])

print(f"📍 Test location: {test_lat}, {test_lon}")
print(f"📦 Bbox: {tight_bbox}")
print(f"🔧 Geometry coordinates (lon, lat, lon, lat): {test_geometry.coordinates}")

# Initialize SRTM adapter exactly like notebook
EARTH_ENGINE = CANONICAL_SERVICES["EARTH_ENGINE"]
adapter = EARTH_ENGINE(asset_id="USGS/SRTMGL1_003")

# Create request spec exactly like notebook
spec = RequestSpec(
    geometry=test_geometry,
    time_range=("2021-01-01", "2021-12-31"),
    variables=None,
    extra={"timeout": 60}
)

print("\n🔍 Calling adapter._fetch_rows(spec)...")
result = adapter._fetch_rows(spec)

print(f"\n📊 Result type: {type(result)}")
print(f"📊 Result length: {len(result) if result else 'None'}")

if result and len(result) > 0:
    print(f"✅ SUCCESS: Got {len(result)} observations")
    print(f"\n📝 First observation:")
    for key, value in result[0].items():
        print(f"   {key}: {value}")
else:
    print(f"❌ FAILURE: No data returned")
    print(f"   Result: {result}")