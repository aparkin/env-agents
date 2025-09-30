#!/usr/bin/env python3
"""
Test the production script's process_cluster logic with SRTM
"""
import sys
import sqlite3
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from env_agents.adapters import CANONICAL_SERVICES
from env_agents.core.models import RequestSpec, Geometry

# Read a cluster from the database
db_path = Path(__file__).parent.parent / "notebooks/pangenome_env_data/pangenome_env.db"

print(f"📂 Database: {db_path}")
print(f"   Exists: {db_path.exists()}")

conn = sqlite3.connect(db_path)

# Get first TERRESTRIAL cluster (not ocean)
cursor = conn.execute("""
SELECT cluster_id, center_lat, center_lon, bbox_minlat, bbox_minlon, bbox_maxlat, bbox_maxlon, point_count
FROM spatial_clusters
WHERE center_lat BETWEEN 30 AND 48
  AND center_lon BETWEEN -120 AND -70
ORDER BY cluster_id
LIMIT 1
""")

row = cursor.fetchone()
conn.close()

if not row:
    print("❌ No terrestrial US clusters found")
    sys.exit(1)

cluster_id, center_lat, center_lon, minlat, minlon, maxlat, maxlon, point_count = row

print(f"\n📍 Test cluster: {cluster_id}")
print(f"   Center: {center_lat:.4f}, {center_lon:.4f}")
print(f"   Bbox: [{minlat:.4f}, {minlon:.4f}, {maxlat:.4f}, {maxlon:.4f}]")
print(f"   Points: {point_count}")

# Replicate production script's geometry creation
tight_minlat = center_lat - 0.005
tight_minlon = center_lon - 0.005
tight_maxlat = center_lat + 0.005
tight_maxlon = center_lon + 0.005

geometry = Geometry(type="bbox", coordinates=[tight_minlon, tight_minlat, tight_maxlon, tight_maxlat])

print(f"\n🔧 Production script geometry:")
print(f"   Tight bbox: [{tight_minlat:.4f}, {tight_minlon:.4f}, {tight_maxlat:.4f}, {tight_maxlon:.4f}]")
print(f"   Geometry coords: {geometry.coordinates}")

# Initialize SRTM adapter exactly like production script
EARTH_ENGINE = CANONICAL_SERVICES["EARTH_ENGINE"]
adapter = EARTH_ENGINE(asset_id="USGS/SRTMGL1_003")

# Create request spec exactly like production script
config = {
    "time_range": ("2021-01-01", "2021-12-31"),
    "timeout": 120
}

spec = RequestSpec(
    geometry=geometry,
    time_range=config['time_range'],
    variables=None,
    extra={"timeout": config['timeout']}
)

print(f"\n🔍 Calling adapter._fetch_rows(spec)...")
result = adapter._fetch_rows(spec)

print(f"\n📊 Result type: {type(result)}")
print(f"📊 Result value: {result is not None}")
if result is not None:
    print(f"📊 Result length: {len(result)}")

# Test production script's condition
if result and len(result) > 0:
    print(f"\n✅ SUCCESS: Production condition passed!")
    print(f"   Got {len(result)} observations")

    # Show first observation variable
    if result[0].get('variable'):
        print(f"   First variable: {result[0]['variable']}")
        print(f"   First value: {result[0].get('value')}")
else:
    print(f"\n❌ FAILURE: Production condition failed")
    print(f"   result and len(result) > 0 = {result and len(result) > 0}")
    if result is None:
        print(f"   Result is None")
    elif not result:
        print(f"   Result is falsy: {result}")
    elif len(result) == 0:
        print(f"   Result length is 0")