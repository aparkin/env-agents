#!/usr/bin/env python3
"""
Quick test of fixed SoilGrids adapter
"""

import sys
from pathlib import Path

# Add the package to Python path
env_agents_path = Path(__file__).parent
sys.path.insert(0, str(env_agents_path))

from env_agents.adapters.soil import SoilGridsAdapter
from env_agents.core.models import RequestSpec, Geometry

def quick_test():
    print("=== Quick SoilGrids Test ===")

    try:
        adapter = SoilGridsAdapter()
        print("✅ Adapter initialized")

        # Test single coverage fetch with small area
        print("\n1. Testing single coverage fetch...")
        bbox = (5.78, 51.98, 5.8, 52.0)  # Small Netherlands area

        if hasattr(adapter, 'catalog_cache') and adapter.catalog_cache:
            # Get first clay coverage
            clay_coverages = adapter.catalog_cache.get('clay', [])
            if clay_coverages:
                coverage_id = clay_coverages[0]  # clay_0-5cm_Q0.05 or similar
                print(f"   Testing coverage: {coverage_id}")

                try:
                    df = adapter._fetch_coverage_to_df('clay', coverage_id, bbox)
                    if df is not None and not df.empty:
                        print(f"   ✅ SUCCESS: {len(df)} data points retrieved")
                        print(f"   Sample data: lat={df.iloc[0]['latitude']:.4f}, value={df.iloc[0]['value']}")
                    else:
                        print("   ⚠️  No data returned")
                except Exception as e:
                    print(f"   ❌ Error: {e}")

        # Test full adapter workflow
        print("\n2. Testing full adapter workflow...")
        geometry = Geometry(type="bbox", coordinates=list(bbox))
        spec = RequestSpec(
            geometry=geometry,
            variables=["soil:clay"],
            extra={"max_pixels": 50000}
        )

        try:
            rows = adapter._fetch_rows(spec)
            if rows:
                print(f"   ✅ SUCCESS: {len(rows)} observations")
                sample = rows[0]
                print(f"   Sample: {sample['variable']} = {sample['value']} {sample['unit']}")
            else:
                print("   ⚠️  No data returned from full workflow")
        except Exception as e:
            print(f"   ❌ Full workflow error: {e}")

    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    quick_test()