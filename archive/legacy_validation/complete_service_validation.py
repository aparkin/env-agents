#!/usr/bin/env python3
"""
Complete Service Validation - ALL 10 Services
==============================================

Tests ALL canonical services uniformly:
- All 9 unitary services
- Earth Engine meta-service with asset-specific testing
- Uniform capability discovery
- Authentication testing
- Data fetching validation
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import time
import traceback

# Setup
project_root = Path().absolute()
sys.path.insert(0, str(project_root))

from env_agents.adapters import CANONICAL_SERVICES
from env_agents.core.models import RequestSpec, Geometry

print("🚀 COMPLETE SERVICE VALIDATION - ALL 10 SERVICES")
print("=" * 60)
print(f"📊 Testing {len(CANONICAL_SERVICES)} canonical services")
print()

# Optimized test locations for maximum coverage
TEST_LOCATIONS = {
    "Amazon Basin": (-60.0, -3.0),          # Excellent SoilGrids, GBIF, NASA_POWER
    "San Francisco Bay": (-122.4194, 37.7749), # USA services: EPA_AQS, USGS_NWIS, WQP
    "Netherlands": (4.9041, 52.3676),        # European coverage: OpenAQ, OSM_Overpass
}

TEST_TIME_RANGE = ("2018-06-01T00:00:00Z", "2018-08-31T23:59:59Z")

def test_service_capabilities(service_name, adapter_class, timeout=30):
    """Test capability discovery for a single service"""
    result = {
        'service_name': service_name,
        'success': False,
        'error': None,
        'duration': 0,
        'variable_count': 0,
        'service_type': 'unknown'
    }

    try:
        print(f"🔍 Testing {service_name}...")

        # Initialize adapter
        start_time = time.time()
        adapter = adapter_class()

        # Get capabilities
        capabilities = adapter.capabilities()
        duration = time.time() - start_time

        # Extract info
        variables = capabilities.get('variables', [])
        service_type = capabilities.get('service_type', 'unitary')

        print(f"  ✅ Response time: {duration:.2f}s")
        print(f"  ✅ Service type: {service_type}")
        print(f"  ✅ Variables: {len(variables)}")

        # Show sample variables
        if variables:
            sample_vars = variables[:3]
            for var in sample_vars:
                var_name = var.get('name', var.get('canonical', 'unknown'))[:40]
                print(f"     - {var_name}...")

        result.update({
            'success': True,
            'duration': duration,
            'variable_count': len(variables),
            'service_type': service_type,
            'capabilities': capabilities
        })

    except Exception as e:
        error_msg = str(e)[:100]
        print(f"  ❌ Error: {error_msg}")
        result.update({
            'error': error_msg,
            'duration': time.time() - start_time if 'start_time' in locals() else 0
        })

    print()
    return result

def test_earth_engine_two_stage():
    """Detailed Earth Engine two-stage discovery testing"""
    print("🚀 EARTH ENGINE TWO-STAGE DISCOVERY (DETAILED)")
    print("-" * 50)

    try:
        ee_class = CANONICAL_SERVICES['EARTH_ENGINE']

        # Stage 1: Asset Discovery
        print("🌍 Stage 1: Asset Discovery")
        discovery_adapter = ee_class()
        discovery_caps = discovery_adapter.capabilities()

        service_type = discovery_caps.get('service_type')
        assets = discovery_caps.get('assets', [])

        print(f"  ✅ Service type: {service_type}")
        print(f"  ✅ Assets discovered: {len(assets)}")
        print(f"  ✅ Assets type: {type(assets)}")

        if assets and len(assets) > 0:
            # Handle assets as dictionary (Earth Engine returns asset categories)
            if isinstance(assets, dict):
                print(f"  ✅ Asset structure: dictionary with {len(assets)} categories")
                print(f"  ✅ Asset categories: {list(assets.keys())}")

                # Get first example from first category
                first_category = list(assets.keys())[0]
                first_category_assets = assets[first_category]
                if isinstance(first_category_assets, dict) and 'examples' in first_category_assets:
                    first_asset = first_category_assets['examples'][0]
                    print(f"  ✅ First asset example: {first_asset}")
                else:
                    first_asset = first_category_assets
                    print(f"  ✅ First category content: {type(first_asset)}")
            else:
                print(f"  ✅ First asset type: {type(assets[0])}")
                print(f"  ✅ First asset: {assets[0]}")

        # Stage 2: Asset-Specific Capabilities
        print("\\n🎯 Stage 2: Asset-Specific Capabilities")

        asset_results = []

        # Extract testable assets from the structure
        test_assets = []
        if isinstance(assets, dict):
            # Extract examples from asset categories
            for category_name, category_info in list(assets.items())[:3]:  # Test first 3 categories
                if isinstance(category_info, dict) and 'examples' in category_info:
                    for example in category_info['examples'][:2]:  # First 2 examples per category
                        if isinstance(example, dict):
                            asset_id = example.get('id') or example.get('asset_id')
                            test_assets.append(asset_id)
                        else:
                            test_assets.append(example)
        elif isinstance(assets, list):
            test_assets = assets[:3]  # First 3 if it's a list

        test_limit = min(3, len(test_assets))

        for i in range(test_limit):
            asset_id = test_assets[i]
            print(f"\\n  [{i+1}/{test_limit}] Testing asset: {asset_id}")

            try:
                print(f"    Asset ID: {asset_id}")

                # Create asset-specific adapter
                asset_adapter = ee_class(asset_id=asset_id)
                asset_caps = asset_adapter.capabilities()

                asset_variables = asset_caps.get('variables', [])
                print(f"    ✅ Asset variables: {len(asset_variables)}")

                if asset_variables:
                    for var in asset_variables[:2]:
                        var_name = var.get('name', 'unknown')[:30]
                        print(f"       - {var_name}")

                asset_results.append({
                    'asset_id': asset_id,
                    'success': True,
                    'variable_count': len(asset_variables)
                })

            except Exception as e:
                error_msg = str(e)[:60]
                print(f"    ❌ Error: {error_msg}")
                asset_results.append({
                    'asset_id': str(asset_id),
                    'success': False,
                    'error': error_msg
                })

        # Summary
        successful_assets = sum(1 for r in asset_results if r.get('success'))

        print(f"\\n📊 EARTH ENGINE SUMMARY:")
        print(f"  ✅ Stage 1 (Discovery): {'SUCCESS' if len(assets) > 0 else 'FAILED'}")
        print(f"  ✅ Assets discovered: {len(assets)}")
        print(f"  ✅ Stage 2 (Asset-specific): {successful_assets}/{len(asset_results)}")

        overall_success = len(assets) > 0 and successful_assets > 0
        print(f"  🎯 Two-stage pattern: {'OPERATIONAL' if overall_success else 'NEEDS WORK'}")

        return {
            'stage1_success': len(assets) > 0,
            'assets_discovered': len(assets),
            'stage2_success': successful_assets,
            'assets_tested': len(asset_results),
            'overall_success': overall_success,
            'asset_results': asset_results
        }

    except Exception as e:
        print(f"❌ Earth Engine testing failed: {str(e)}")
        traceback.print_exc()
        return {'overall_success': False, 'error': str(e)}

def test_service_data_fetch(service_name, adapter_class, location_name, coords, timeout=60):
    """Test data fetching for a service"""
    print(f"📊 Testing data fetch: {service_name} at {location_name}")

    try:
        adapter = adapter_class()
        geometry = Geometry(type="point", coordinates=coords)

        spec = RequestSpec(
            geometry=geometry,
            time_range=TEST_TIME_RANGE,
            variables=None,  # Get all available
            extra={"timeout": timeout}
        )

        start_time = time.time()
        df = adapter.fetch(spec)
        duration = time.time() - start_time

        if df is not None and not df.empty:
            unique_vars = df['variable'].nunique() if 'variable' in df.columns else 0
            has_coords = 'latitude' in df.columns and 'longitude' in df.columns
            has_core_schema = all(col in df.columns for col in ['observation_id', 'dataset', 'variable', 'value'])

            print(f"  ✅ Fetch time: {duration:.2f}s")
            print(f"  ✅ Rows: {len(df)}")
            print(f"  ✅ Variables: {unique_vars}")
            print(f"  ✅ Has coordinates: {has_coords}")
            print(f"  ✅ Core schema: {has_core_schema}")

            return {
                'success': True,
                'duration': duration,
                'row_count': len(df),
                'variable_count': unique_vars,
                'has_core_schema': has_core_schema
            }
        else:
            print(f"  ⚠️  No data returned")
            return {'success': False, 'reason': 'no_data'}

    except Exception as e:
        error_msg = str(e)[:80]
        print(f"  ❌ Fetch error: {error_msg}")
        return {'success': False, 'error': error_msg}

def main():
    """Run complete service validation"""

    print("Phase 1: Capability Discovery for ALL Services")
    print("=" * 50)

    capability_results = {}

    # Test all services
    for service_name, adapter_class in CANONICAL_SERVICES.items():
        result = test_service_capabilities(service_name, adapter_class)
        capability_results[service_name] = result

    # Detailed Earth Engine testing
    print("\\nPhase 2: Earth Engine Two-Stage Discovery")
    print("=" * 50)
    ee_result = test_earth_engine_two_stage()

    print("\\nPhase 3: Data Fetching Tests")
    print("=" * 50)

    # Test data fetching for key services with appropriate locations
    fetch_tests = [
        ('NASA_POWER', 'Amazon Basin', TEST_LOCATIONS['Amazon Basin']),
        ('SoilGrids', 'Amazon Basin', TEST_LOCATIONS['Amazon Basin']),  # Proven working
        ('GBIF', 'Amazon Basin', TEST_LOCATIONS['Amazon Basin']),
        ('OpenAQ', 'Netherlands', TEST_LOCATIONS['Netherlands']),
        ('EPA_AQS', 'San Francisco Bay', TEST_LOCATIONS['San Francisco Bay']),
        ('USGS_NWIS', 'San Francisco Bay', TEST_LOCATIONS['San Francisco Bay']),
        ('OSM_Overpass', 'Netherlands', TEST_LOCATIONS['Netherlands']),
    ]

    fetch_results = {}
    for service_name, location_name, coords in fetch_tests:
        if service_name in CANONICAL_SERVICES:
            adapter_class = CANONICAL_SERVICES[service_name]
            result = test_service_data_fetch(service_name, adapter_class, location_name, coords)
            fetch_results[service_name] = result
            print()

    # Final Analysis
    print("COMPLETE VALIDATION RESULTS")
    print("=" * 60)

    # Capability discovery results
    successful_caps = sum(1 for r in capability_results.values() if r.get('success'))
    total_variables = sum(r.get('variable_count', 0) for r in capability_results.values() if r.get('success'))

    print(f"📊 CAPABILITY DISCOVERY:")
    print(f"  ✅ Successful: {successful_caps}/{len(CANONICAL_SERVICES)} services")
    print(f"  📊 Total variables: {total_variables}")
    print(f"  🎯 Success rate: {successful_caps/len(CANONICAL_SERVICES)*100:.0f}%")

    # Earth Engine results
    ee_success = ee_result.get('overall_success', False)
    print(f"\\n🚀 EARTH ENGINE TWO-STAGE:")
    print(f"  ✅ Overall: {'SUCCESS' if ee_success else 'FAILED'}")
    print(f"  ✅ Assets discovered: {ee_result.get('assets_discovered', 0)}")
    print(f"  ✅ Asset-specific tests: {ee_result.get('stage2_success', 0)}/{ee_result.get('assets_tested', 0)}")

    # Data fetching results
    successful_fetches = sum(1 for r in fetch_results.values() if r.get('success'))
    total_rows = sum(r.get('row_count', 0) for r in fetch_results.values() if r.get('success'))

    print(f"\\n📊 DATA FETCHING:")
    print(f"  ✅ Successful: {successful_fetches}/{len(fetch_results)} services")
    print(f"  📊 Total rows: {total_rows}")
    print(f"  🎯 Success rate: {successful_fetches/len(fetch_results)*100:.0f}% (of tested)")

    # Overall system score
    capability_score = successful_caps / len(CANONICAL_SERVICES) * 100
    ee_score = 100 if ee_success else 0
    fetch_score = (successful_fetches / len(fetch_results) * 100) if fetch_results else 0

    overall_score = np.mean([capability_score, ee_score * 0.3, fetch_score * 0.7])  # Weight data fetching higher

    print(f"\\n🏆 OVERALL SYSTEM ASSESSMENT:")
    print(f"  📋 Capability Discovery: {capability_score:.0f}%")
    print(f"  🚀 Earth Engine Two-Stage: {'PASS' if ee_success else 'FAIL'}")
    print(f"  📊 Data Fetching: {fetch_score:.0f}%")
    print(f"  🎯 OVERALL SCORE: {overall_score:.0f}%")

    if overall_score >= 80:
        print("\\n🟢 SYSTEM STATUS: EXCELLENT - Production Ready")
    elif overall_score >= 65:
        print("\\n🟡 SYSTEM STATUS: GOOD - Minor Issues")
    else:
        print("\\n🔴 SYSTEM STATUS: NEEDS WORK - Significant Issues")

    # Detailed service breakdown
    print(f"\\n📋 DETAILED SERVICE STATUS:")
    for service_name, result in capability_results.items():
        status = "✅" if result.get('success') else "❌"
        service_type = result.get('service_type', 'unknown')
        var_count = result.get('variable_count', 0)
        duration = result.get('duration', 0)

        print(f"  {status} {service_name:<15} {service_type:<8} {var_count:3d} vars {duration:5.2f}s")

    print(f"\\n✅ Complete validation finished!")
    print(f"📊 {successful_caps}/{len(CANONICAL_SERVICES)} services operational")

if __name__ == "__main__":
    main()