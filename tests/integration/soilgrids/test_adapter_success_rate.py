#!/usr/bin/env python3
"""
SoilGrids WCS Adapter Success Rate Test
Verifies actual success rate of the enhanced adapter
"""

import sys
import os
from pathlib import Path

# Add the package to Python path
env_agents_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(env_agents_path))

from env_agents.adapters.soil.wcs_adapter import SoilGridsWCSAdapter
from env_agents.core.models import RequestSpec, Geometry

def test_adapter_success_rate():
    """Test actual success rate of SoilGrids WCS adapter"""
    print("🧪 SoilGrids WCS Adapter Success Rate Test")
    print("=" * 50)

    adapter = SoilGridsWCSAdapter()

    # Test scenarios
    test_cases = [
        {
            "name": "Small Netherlands",
            "bbox": (5.78, 51.98, 5.8, 52.0),
            "variables": ["soil:clay"]
        },
        {
            "name": "California Central Valley",
            "bbox": (-122.0, 37.0, -121.98, 37.02),
            "variables": ["soil:organic_carbon"]
        },
        {
            "name": "Brazil Amazon",
            "bbox": (-60.0, -3.2, -59.98, -3.18),
            "variables": ["soil:ph"]
        },
        {
            "name": "Multiple Variables",
            "bbox": (5.78, 51.98, 5.82, 52.02),
            "variables": ["soil:clay", "soil:organic_carbon"]
        }
    ]

    successful_tests = 0
    total_tests = len(test_cases)

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n[{i}/{total_tests}] Testing {test_case['name']}...")

        try:
            geometry = Geometry(type="bbox", coordinates=list(test_case['bbox']))
            spec = RequestSpec(
                geometry=geometry,
                variables=test_case['variables'],
                extra={"max_pixels": 50000}
            )

            rows = adapter._fetch_rows(spec)

            if rows and len(rows) > 0:
                print(f"   ✅ SUCCESS: {len(rows)} observations returned")

                # Check data quality
                sample = rows[0]
                print(f"   Sample: {sample.get('variable', 'unknown')} = {sample.get('value', 'N/A')} {sample.get('unit', '')}")
                print(f"   Location: lat={sample.get('latitude', 'N/A'):.4f}, lon={sample.get('longitude', 'N/A'):.4f}")

                successful_tests += 1
            else:
                print("   ❌ FAILED: No data returned")

        except Exception as e:
            print(f"   ❌ ERROR: {str(e)[:100]}")

    success_rate = successful_tests / total_tests
    print(f"\n{'='*50}")
    print(f"📊 SUCCESS RATE ANALYSIS")
    print(f"{'='*50}")
    print(f"Successful tests: {successful_tests}/{total_tests}")
    print(f"Success rate: {success_rate:.1%}")

    if success_rate >= 0.75:
        status = "🎉 EXCELLENT"
    elif success_rate >= 0.50:
        status = "👍 GOOD"
    elif success_rate >= 0.25:
        status = "⚠️ POOR"
    else:
        status = "💥 CRITICAL"

    print(f"Assessment: {status}")

    return success_rate >= 0.5

if __name__ == "__main__":
    success = test_adapter_success_rate()
    sys.exit(0 if success else 1)