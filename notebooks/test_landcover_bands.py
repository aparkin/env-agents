#!/usr/bin/env python3
"""
Check what bands and metadata we get from MODIS landcover assets
"""

import sys
sys.path.insert(0, '/Users/aparkin/Arkin Lab Dropbox/Adam Arkin/Code/ENIGMA Project/analyses/2025-08-23-Soil Adaptor from GPT5/env-agents')

from env_agents.adapters.earth_engine.production_adapter import ProductionEarthEngineAdapter
from env_agents.core.models import RequestSpec, Geometry

def test_asset(asset_id, name, test_year):
    """Test what we get from an asset"""
    print(f"\n{'='*80}")
    print(f"Testing: {name}")
    print(f"Asset: {asset_id}")
    print(f"{'='*80}")
    
    try:
        adapter = ProductionEarthEngineAdapter(
            asset_id=asset_id,
            scale=500
        )
        
        # Get capabilities (band names)
        caps = adapter.capabilities()
        print(f"\n✓ Asset type: {caps['asset_type']}")
        print(f"✓ Variables available: {len(caps['variables'])}")
        for var in caps['variables']:
            print(f"    - {var['name']} ({var['description']})")
        
        # Try fetching data
        spec = RequestSpec(
            geometry=Geometry(
                type="point",
                coordinates=[-122.4, 37.8]  # San Francisco
            ),
            time_range=(f"{test_year}-01-01", f"{test_year}-12-31")
        )
        
        print(f"\n✓ Fetching data for {test_year}...")
        rows = adapter._fetch_rows(spec)
        
        if rows:
            print(f"✓ Retrieved {len(rows)} observations")
            print(f"\nFirst 5 observations:")
            for i, row in enumerate(rows[:5]):
                print(f"  {i+1}. {row['variable']}: {row['value']}")
            
            # Show attributes from first row
            if 'attributes' in rows[0]:
                print(f"\nAttributes from first observation:")
                for key, val in rows[0]['attributes'].items():
                    print(f"  {key}: {val}")
        else:
            print(f"✗ No data returned")
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Test both versions
    test_asset("MODIS/006/MCD12Q1", "MODIS 006 (old, deprecated)", "2019")
    test_asset("MODIS/061/MCD12Q1", "MODIS 061 (new)", "2022")
    
    print(f"\n{'='*80}")
    print("COMPARISON COMPLETE")
    print(f"{'='*80}")
