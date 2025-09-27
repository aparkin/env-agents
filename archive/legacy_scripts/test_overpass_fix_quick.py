#!/usr/bin/env python3
"""
Quick test of the Overpass fix
"""
import sys
sys.path.insert(0, '.')

from env_agents.core.models import RequestSpec, Geometry
from env_agents.adapters.overpass.enhanced_adapter import EnhancedOverpassAdapter

def test_overpass_quick():
    print("🧪 Testing Overpass Fix")
    print("=" * 25)
    
    try:
        overpass = EnhancedOverpassAdapter()
        
        # Test with exact same San Francisco coordinates as your working version
        sf_geom = Geometry(type='point', coordinates=[-122.4194, 37.7749])
        spec = RequestSpec(
            geometry=sf_geom,
            time_range=('2024-01-01', '2024-12-31'),
            variables=['building'],
            extra={'radius': 500}  # Small radius matching your working test
        )
        
        print("Making query with fixed tiling approach...")
        
        # Debug the query and tiling
        print("\\n🔍 Debug: Testing coordinate handling...")
        
        # Test tiling coordinates 
        tiles = overpass._tile_bbox(37.77, -122.42, 37.78, -122.41)
        print(f"Generated {len(tiles)} tiles:")
        for i, tile in enumerate(tiles):
            print(f"  Tile {i+1}: {tile}")
        
        # Test query generation
        if tiles:
            test_query = overpass._overpass_query(*tiles[0])
            print("Query generation successful!")
        
        rows = overpass._fetch_rows(spec)
        
        print(f"✅ Retrieved: {len(rows)} OSM features")
        if rows:
            print("✅ Query successful - Overpass fix working")
            sample = rows[0]
            print(f"Sample feature: {sample.get('variable', 'unknown')}")
        else:
            print("⚠️ No features returned (but query worked)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_overpass_quick()