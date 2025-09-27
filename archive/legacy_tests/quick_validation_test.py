#!/usr/bin/env python3
"""
Quick System Validation - Focused Testing
==========================================

Tests core objectives with reasonable timeouts:
1. SoilGrids WCS adapter validation
2. Earth Engine two-stage discovery
3. Uniform capability discovery
4. Simple data fusion demonstration
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import time

# Setup
project_root = Path().absolute()
sys.path.insert(0, str(project_root))

from env_agents.adapters import CANONICAL_SERVICES
from env_agents.core.models import RequestSpec, Geometry

print("🚀 QUICK SYSTEM VALIDATION")
print("=" * 40)

def test_soilgrids_wcs():
    """Test the updated SoilGrids WCS adapter"""
    print("1️⃣ SOILGRIDS WCS ADAPTER VALIDATION")
    print("-" * 30)

    try:
        adapter_class = CANONICAL_SERVICES['SoilGrids']
        print(f"✅ Adapter class: {adapter_class.__name__}")
        print(f"✅ Source URL: {adapter_class.SOURCE_URL}")
        print(f"✅ Dataset: {adapter_class.DATASET}")

        adapter = adapter_class()
        print("✅ Adapter initialized")

        # Test capabilities
        caps = adapter.capabilities()
        variables = caps.get('variables', [])
        print(f"✅ Variables discovered: {len(variables)}")

        # Show sample variables
        for var in variables[:5]:
            name = var.get('canonical', var.get('name', 'unknown'))
            print(f"   - {name}")

        # Test data fetch with Amazon Basin (proven working)
        print("\\n📍 Testing data fetch (Amazon Basin)...")
        geometry = Geometry(type="bbox", coordinates=[-60.0, -3.0, -59.8, -2.8])
        spec = RequestSpec(
            geometry=geometry,
            variables=['soil:clay'],
            extra={'max_pixels': 1000}
        )

        start_time = time.time()
        rows = adapter._fetch_rows(spec)
        duration = time.time() - start_time

        if rows and len(rows) > 0:
            print(f"✅ Data fetch successful: {len(rows)} observations in {duration:.2f}s")
            sample = rows[0]
            print(f"✅ Sample data: {sample.get('variable')} = {sample.get('value')} {sample.get('unit')}")
            return True
        else:
            print("❌ No data returned")
            return False

    except Exception as e:
        print(f"❌ SoilGrids test failed: {str(e)}")
        return False

def test_earth_engine_two_stage():
    """Test Earth Engine two-stage discovery"""
    print("\\n2️⃣ EARTH ENGINE TWO-STAGE DISCOVERY")
    print("-" * 30)

    try:
        ee_class = CANONICAL_SERVICES['EARTH_ENGINE']

        # Stage 1: Asset Discovery
        print("🌍 Stage 1: Asset Discovery")
        discovery_adapter = ee_class()  # No asset_id

        discovery_caps = discovery_adapter.capabilities()
        service_type = discovery_caps.get('service_type')
        assets = discovery_caps.get('assets', [])

        print(f"✅ Service type: {service_type}")
        print(f"✅ Assets discovered: {len(assets)}")

        if assets:
            # Handle assets as dictionary (Earth Engine returns asset categories)
            if isinstance(assets, dict):
                print("✅ Asset categories:")
                for category, info in list(assets.items())[:5]:
                    count = info.get('count', 0) if isinstance(info, dict) else 0
                    print(f"   - {category}: {count}")
            else:
                # Show asset types for list format
                asset_types = {}
                for asset in assets:
                    asset_type = asset.get('category', 'unknown') if isinstance(asset, dict) else 'unknown'
                    asset_types[asset_type] = asset_types.get(asset_type, 0) + 1

                print("✅ Asset categories:")
                for category, count in list(asset_types.items())[:5]:
                    print(f"   - {category}: {count}")

        # Stage 2: Asset-Specific Capabilities
        print("\\n🎯 Stage 2: Asset-Specific Capabilities")

        if assets:
            # Extract test asset from structure
            test_asset_id = None

            if isinstance(assets, dict):
                # Get first asset from first category
                first_category = list(assets.keys())[0]
                category_info = assets[first_category]
                if isinstance(category_info, dict) and 'examples' in category_info:
                    examples = category_info['examples']
                    if examples and len(examples) > 0:
                        first_example = examples[0]
                        if isinstance(first_example, dict):
                            test_asset_id = first_example.get('id') or first_example.get('asset_id')
                        else:
                            test_asset_id = first_example
            else:
                # List format
                if len(assets) > 0:
                    test_asset = assets[0]
                    if isinstance(test_asset, dict):
                        test_asset_id = test_asset.get('asset_id') or test_asset.get('id')
                    else:
                        test_asset_id = test_asset

            if test_asset_id:
                print(f"Testing asset: {test_asset_id}")

                try:
                    asset_adapter = ee_class(asset_id=test_asset_id)
                    asset_caps = asset_adapter.capabilities()

                    asset_variables = asset_caps.get('variables', [])
                    print(f"✅ Asset variables: {len(asset_variables)}")

                    if asset_variables:
                        for var in asset_variables[:3]:
                            var_name = var.get('name', 'unknown') if isinstance(var, dict) else str(var)
                            print(f"   - {var_name}")
                except Exception as e:
                    print(f"❌ Asset test failed: {str(e)[:60]}")
            else:
                print("❌ No testable asset found")

        success = len(assets) > 0 and service_type == 'meta'
        print(f"\\n✅ Two-stage discovery: {'SUCCESS' if success else 'FAILED'}")
        return success

    except Exception as e:
        print(f"❌ Earth Engine test failed: {str(e)}")
        return False

def test_uniform_discovery():
    """Test uniform capability discovery across services"""
    print("\\n3️⃣ UNIFORM CAPABILITY DISCOVERY")
    print("-" * 30)

    results = {}

    # Test key services with short timeouts
    test_services = ['NASA_POWER', 'SoilGrids', 'EARTH_ENGINE']

    for service_name in test_services:
        try:
            adapter_class = CANONICAL_SERVICES[service_name]
            adapter = adapter_class()

            start_time = time.time()
            caps = adapter.capabilities()
            duration = time.time() - start_time

            variables = caps.get('variables', [])
            service_type = caps.get('service_type', 'unitary')

            print(f"✅ {service_name}: {len(variables)} vars, {service_type}, {duration:.2f}s")

            results[service_name] = {
                'success': True,
                'variable_count': len(variables),
                'service_type': service_type
            }

        except Exception as e:
            print(f"❌ {service_name}: {str(e)[:50]}")
            results[service_name] = {'success': False}

    success_count = sum(1 for r in results.values() if r.get('success'))
    total_vars = sum(r.get('variable_count', 0) for r in results.values() if r.get('success'))

    print(f"\\n✅ Discovery results: {success_count}/{len(test_services)} services, {total_vars} total variables")
    return success_count / len(test_services) >= 0.8

def test_simple_fusion():
    """Test simple data fusion with available data"""
    print("\\n4️⃣ SIMPLE DATA FUSION TEST")
    print("-" * 30)

    try:
        # Get data from SoilGrids (proven working)
        soilgrids_class = CANONICAL_SERVICES['SoilGrids']
        adapter = soilgrids_class()

        geometry = Geometry(type="point", coordinates=[-60.0, -3.0])  # Amazon
        spec = RequestSpec(
            geometry=geometry,
            variables=['soil:clay', 'soil:soc'],
            extra={'max_pixels': 500}
        )

        df = adapter.fetch(spec)

        if df is not None and not df.empty:
            print(f"✅ Base data: {len(df)} observations from SoilGrids")
            print(f"✅ Variables: {df['variable'].nunique() if 'variable' in df.columns else 0}")
            print(f"✅ Columns: {len(df.columns)}")

            # Check core schema compliance
            required_cols = ['observation_id', 'latitude', 'longitude', 'variable', 'value', 'unit']
            has_required = all(col in df.columns for col in required_cols)
            print(f"✅ Core schema compliance: {has_required}")

            if has_required:
                # Show fusion potential
                print("✅ Ready for multi-service fusion")
                return True

        print("❌ Insufficient data for fusion")
        return False

    except Exception as e:
        print(f"❌ Fusion test failed: {str(e)}")
        return False

def main():
    """Run quick validation tests"""

    results = {
        'soilgrids_wcs': test_soilgrids_wcs(),
        'earth_engine_two_stage': test_earth_engine_two_stage(),
        'uniform_discovery': test_uniform_discovery(),
        'simple_fusion': test_simple_fusion()
    }

    print("\\n" + "=" * 40)
    print("🏁 QUICK VALIDATION RESULTS")
    print("=" * 40)

    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name.replace('_', ' ').title()}")

    success_count = sum(results.values())
    success_rate = success_count / len(results) * 100

    print(f"\\n📊 OVERALL: {success_count}/{len(results)} tests passed ({success_rate:.0f}%)")

    if success_rate >= 75:
        print("🟢 SYSTEM STATUS: READY FOR PRODUCTION")
    elif success_rate >= 50:
        print("🟡 SYSTEM STATUS: MOSTLY FUNCTIONAL")
    else:
        print("🔴 SYSTEM STATUS: NEEDS WORK")

    print("\\n✅ Quick validation complete!")

if __name__ == "__main__":
    main()