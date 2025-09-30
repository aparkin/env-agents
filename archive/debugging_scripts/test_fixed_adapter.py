#!/usr/bin/env python3
"""
Test the FIXED adapter pattern: Create fresh EE adapters per query (like notebook)
"""
import sys
import sqlite3
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from env_agents.adapters import CANONICAL_SERVICES
from env_agents.core.models import RequestSpec, Geometry

# Read multiple terrestrial clusters from database
db_path = Path(__file__).parent.parent / "notebooks/pangenome_env_data/pangenome_env.db"

conn = sqlite3.connect(db_path)
cursor = conn.execute("""
SELECT cluster_id, center_lat, center_lon
FROM spatial_clusters
WHERE center_lat BETWEEN 30 AND 48
  AND center_lon BETWEEN -120 AND -70
ORDER BY cluster_id
LIMIT 10
""")

clusters = cursor.fetchall()
conn.close()

print(f"📂 Testing FIXED adapter pattern (fresh EE adapter per query)")
print(f"   Testing {len(clusters)} clusters with SRTM")
print(f"   Pattern: Create NEW adapter for EACH query (matches notebook)")

EARTH_ENGINE = CANONICAL_SERVICES["EARTH_ENGINE"]
asset_id = "USGS/SRTMGL1_003"

config = {
    "rate_limit": 10.0,
    "time_range": ("2021-01-01", "2021-12-31"),
    "timeout": 120
}

results = []

for cluster_id, center_lat, center_lon in clusters:
    print(f"\n{'='*60}")
    print(f"📍 Cluster {cluster_id}: {center_lat:.4f}, {center_lon:.4f}")

    # FIXED PATTERN: Create FRESH adapter for each query (like working notebook)
    print(f"   🔧 Creating fresh SRTM adapter...")
    adapter = EARTH_ENGINE(asset_id=asset_id)

    geometry = Geometry(
        type="bbox",
        coordinates=[
            center_lon - 0.005, center_lat - 0.005,
            center_lon + 0.005, center_lat + 0.005
        ]
    )

    spec = RequestSpec(
        geometry=geometry,
        time_range=config['time_range'],
        variables=None,
        extra={"timeout": config['timeout']}
    )

    try:
        print(f"   🔍 Querying...")
        start = time.time()
        result = adapter._fetch_rows(spec)
        elapsed = time.time() - start

        if result and len(result) > 0:
            print(f"   ✅ Success: {len(result)} obs in {elapsed:.1f}s")
            print(f"      Variable: {result[0].get('variable')}, Value: {result[0].get('value'):.2f}")
            results.append(('success', len(result)))
        else:
            print(f"   ⚠️  No data in {elapsed:.1f}s")
            print(f"      Result: {result}")
            results.append(('no_data', 0))

    except Exception as e:
        print(f"   ❌ Error: {str(e)[:100]}")
        results.append(('error', 0))

    # Rate limit like production
    print(f"   ⏱️  Sleeping {config['rate_limit']}s...")
    time.sleep(config['rate_limit'])

# Summary
print(f"\n{'='*60}")
print(f"📊 FIXED ADAPTER PATTERN TEST SUMMARY")
print(f"{'='*60}")

success_count = sum(1 for status, _ in results if status == 'success')
no_data_count = sum(1 for status, _ in results if status == 'no_data')
error_count = sum(1 for status, _ in results if status == 'error')
total_obs = sum(count for status, count in results if status == 'success')

print(f"\n✅ Success: {success_count}/{len(clusters)}")
print(f"⚠️  No data: {no_data_count}/{len(clusters)}")
print(f"❌ Errors: {error_count}/{len(clusters)}")
print(f"📈 Total observations: {total_obs}")

if success_count == len(clusters):
    print(f"\n🎉 PERFECT! Fixed adapter pattern works correctly!")
    print(f"   Creating fresh EE adapters per query avoids state issues")
    print(f"   This matches the working notebook pattern")
else:
    print(f"\n⚠️  Still seeing issues - may need further investigation")