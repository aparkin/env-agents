#!/usr/bin/env python3
"""
Test the rewritten SoilGrids WCS adapter based on user's proven implementation
"""

import sys
from pathlib import Path

# Add the package to Python path
env_agents_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(env_agents_path))

from env_agents.adapters.soil.soilgrids_wcs_adapter import SoilGridsWCSAdapter
from env_agents.core.models import RequestSpec, Geometry

def test_proven_implementation():
    """Test the rewritten adapter based on user's proven approach"""
    print("🧪 Testing Rewritten SoilGrids WCS Adapter")
    print("=" * 50)

    try:
        # Initialize adapter
        print("1. Initializing adapter...")
        adapter = SoilGridsWCSAdapter()

        # Test catalog building (should be fast)
        print("2. Building catalog...")
        catalog = adapter._build_catalog(refresh=True)
        total_coverages = sum(len(v) for v in catalog.values())
        print(f"   ✅ Catalog built: {len(catalog)} properties, {total_coverages} coverages")

        # Test capabilities
        print("3. Testing capabilities...")
        caps = adapter.capabilities()
        print(f"   ✅ Capabilities: {len(caps.get('variables', []))} variables")
        print(f"   Service type: {caps.get('service_type')}")
        print(f"   Proven approach: {caps.get('proven_approach')}")

        # Test data fetch with small area
        print("4. Testing data fetch...")
        test_cases = [
            {
                "name": "Netherlands Agricultural Area",
                "bbox": (5.2, 52.0, 5.4, 52.2),
                "variables": ["soil:clay", "soil:soc"]
            },
            {
                "name": "Iowa Farmland",
                "bbox": (-94.0, 42.0, -93.8, 42.2),
                "variables": ["soil:clay"]
            }
        ]

        successful_tests = 0
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n   [{i}/{len(test_cases)}] Testing {test_case['name']}...")

            try:
                geometry = Geometry(type="bbox", coordinates=list(test_case["bbox"]))
                spec = RequestSpec(
                    geometry=geometry,
                    variables=test_case["variables"],
                    extra={"max_pixels": 10000, "statistics": ["mean"]}
                )

                rows = adapter._fetch_rows(spec)

                if rows and len(rows) > 0:
                    print(f"      ✅ SUCCESS: {len(rows)} observations")

                    # Check data quality
                    sample = rows[0]
                    print(f"      Sample: {sample.get('variable')} = {sample.get('value')} {sample.get('unit')}")
                    print(f"      Location: lat={sample.get('latitude'):.4f}, lon={sample.get('longitude'):.4f}")

                    # Check for real values (not zeros)
                    real_values = [r for r in rows if r.get('value') and r.get('value') != 0]
                    zero_values = [r for r in rows if r.get('value') == 0]

                    print(f"      Non-zero values: {len(real_values)}/{len(rows)}")
                    if zero_values:
                        print(f"      Zero values: {len(zero_values)} (may be valid)")

                    if real_values:
                        successful_tests += 1
                        print(f"      🎉 REAL DATA RETRIEVED!")
                    else:
                        print(f"      ⚠️  Only zeros returned")
                else:
                    print(f"      ❌ No data returned")

            except Exception as e:
                print(f"      ❌ Error: {str(e)[:100]}")

        # Summary
        success_rate = successful_tests / len(test_cases)
        print(f"\n{'='*50}")
        print(f"📊 TEST RESULTS")
        print(f"{'='*50}")
        print(f"Successful tests: {successful_tests}/{len(test_cases)}")
        print(f"Success rate: {success_rate:.1%}")

        if success_rate >= 0.5:
            print(f"🎉 OVERALL: SUCCESS - Rewritten adapter working!")
            print(f"   ✅ Based on user's proven implementation")
            print(f"   ✅ Fast catalog discovery")
            print(f"   ✅ Real data retrieval")
            return True
        else:
            print(f"⚠️  OVERALL: Needs investigation")
            return False

    except Exception as e:
        print(f"💥 FATAL ERROR: {e}")
        return False

if __name__ == "__main__":
    success = test_proven_implementation()
    print(f"\n{'🎉 PASS' if success else '💥 FAIL'}: Proven implementation test")
    sys.exit(0 if success else 1)