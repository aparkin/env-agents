#!/usr/bin/env python3
"""
Debug Earth Engine query directly - bypass adapter
"""
import sys
sys.path.insert(0, '..')

import ee

# Authenticate
try:
    ee.data.getAssetRoots()
    print("✅ Earth Engine already authenticated")
except:
    print("Authenticating...")
    from pathlib import Path
    key_file = Path('../config/ecognita-470619-e9e223ea70a7.json')
    if key_file.exists():
        credentials = ee.ServiceAccountCredentials(email=None, key_file=str(key_file))
        ee.Initialize(credentials)
        print(f"✅ Authenticated from {key_file.name}")
    else:
        ee.Initialize()
        print("✅ Authenticated with user credentials")

# Test query - cluster 192 (Sweden)
test_lat = 62.27127147
test_lon = 16.93716839

print(f"\n📍 Testing: {test_lat}, {test_lon} (Sweden)")

# Create bbox
bbox = [test_lon - 0.005, test_lat - 0.005, test_lon + 0.005, test_lat + 0.005]
print(f"📦 Bbox: {bbox}")

# Create EE region
region = ee.Geometry.Rectangle(bbox)
print(f"🌍 EE Region: {region.getInfo()}")

# Load SRTM
img = ee.Image("USGS/SRTMGL1_003").clip(region)
print(f"🛰️  SRTM Image: {img}")

# Query
print(f"\n🔍 Querying with reduceRegion...")
stats = img.reduceRegion(
    reducer=ee.Reducer.mean(),
    geometry=region,
    scale=500,
    maxPixels=1e9
).getInfo()

print(f"\n📊 Result: {stats}")
print(f"   Type: {type(stats)}")
print(f"   Keys: {list(stats.keys()) if stats else 'None'}")

if stats:
    for key, value in stats.items():
        print(f"   {key}: {value}")

if stats and any(v is not None for v in stats.values()):
    print(f"\n✅ SUCCESS! Got elevation data")
else:
    print(f"\n❌ FAILED: No data or all None values")
    print(f"   This should NOT happen for SRTM over land!")