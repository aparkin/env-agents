#!/usr/bin/env python3
"""
Test updated WCS adapter with user's proven catalog approach
"""

import sys
from pathlib import Path

# Add the package to Python path
env_agents_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(env_agents_path))

from env_agents.adapters.soil.wcs_adapter import SoilGridsWCSAdapter
from env_agents.core.models import RequestSpec, Geometry

def test_updated_adapter():
    """Test the updated WCS adapter with user's catalog approach"""
    print("🧪 Updated SoilGrids WCS Adapter Test")
    print("=" * 40)

    # Test just catalog building first
    print("1. Testing catalog building...")
    adapter = SoilGridsWCSAdapter()

    try:
        # Force a fresh catalog build with user's approach
        catalog = adapter._build_catalog(force_refresh=True)

        if catalog:
            total_coverages = sum(len(v) for v in catalog.values())
            print(f"   ✅ Catalog built: {len(catalog)} properties, {total_coverages} coverages")

            # Show sample coverages
            for prop, coverages in list(catalog.items())[:3]:
                print(f"   {prop}: {len(coverages)} coverages (e.g., {coverages[0] if coverages else 'none'})")

            return True
        else:
            print("   ❌ Catalog build returned empty")
            return False

    except Exception as e:
        print(f"   ❌ Catalog build failed: {e}")
        return False

if __name__ == "__main__":
    success = test_updated_adapter()
    print(f"\n{'🎉 PASS' if success else '💥 FAIL'}: Updated adapter catalog test")
    sys.exit(0 if success else 1)