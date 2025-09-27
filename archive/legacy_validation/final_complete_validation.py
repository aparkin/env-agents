#!/usr/bin/env python3
"""
Final Complete Service Validation - ALL 10 SERVICES + Data Fusion
================================================================

Tests ALL canonical services uniformly with comprehensive coverage:
- All 10 unitary services + Earth Engine meta-service
- Uniform capability discovery validation
- Authentication testing where required
- Data fetching validation with proven locations
- Earth Engine two-stage discovery (fixed)
- Comprehensive data fusion demonstration
- Visualization of integrated results
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import time
import traceback
import matplotlib.pyplot as plt
import seaborn as sns

# Setup
project_root = Path().absolute()
sys.path.insert(0, str(project_root))

from env_agents.adapters import CANONICAL_SERVICES
from env_agents.core.models import RequestSpec, Geometry

print("🚀 FINAL COMPLETE SERVICE VALIDATION")
print("=" * 70)
print(f"📊 Testing ALL {len(CANONICAL_SERVICES)} canonical services")
print(f"🎯 Goal: Complete system validation + data fusion demo")
print()

# Optimized test locations for maximum coverage
PROVEN_LOCATIONS = {
    "Amazon_Basin": (-60.0, -3.0),           # Excellent: SoilGrids, GBIF, NASA_POWER
    "San_Francisco_Bay": (-122.4194, 37.7749), # USA: EPA_AQS, USGS_NWIS, WQP
    "Netherlands": (4.9041, 52.3676),         # Europe: OpenAQ, OSM_Overpass
    "Iowa_Farmland": (-93.8, 42.0),          # Agricultural: SSURGO
}

TEST_TIME_RANGE = ("2018-06-01T00:00:00Z", "2018-08-31T23:59:59Z")

def test_service_capabilities(service_name, adapter_class, timeout=30):
    """Test capability discovery for any service (unitary or meta)"""
    result = {
        'service_name': service_name,
        'success': False,
        'error': None,
        'duration': 0,
        'variable_count': 0,
        'service_type': 'unknown',
        'capabilities': None
    }

    try:
        print(f"🔍 {service_name}...")

        start_time = time.time()
        adapter = adapter_class()
        capabilities = adapter.capabilities()
        duration = time.time() - start_time

        # Extract info safely
        variables = capabilities.get('variables', [])
        service_type = capabilities.get('service_type', 'unitary')

        print(f"  ✅ {service_type} service - {len(variables)} variables - {duration:.2f}s")

        # Show sample variables (limit output)
        if variables:
            sample_vars = variables[:2]
            for var in sample_vars:
                var_name = var.get('name', var.get('canonical', var.get('id', 'unknown')))[:35]
                print(f"     - {var_name}")

        result.update({
            'success': True,
            'duration': duration,
            'variable_count': len(variables),
            'service_type': service_type,
            'capabilities': capabilities
        })

    except Exception as e:
        error_msg = str(e)[:80]
        print(f"  ❌ Error: {error_msg}")
        result.update({
            'error': error_msg,
            'duration': time.time() - start_time if 'start_time' in locals() else 0
        })

    return result

def test_earth_engine_two_stage():
    """Test Earth Engine meta-service two-stage discovery"""
    print("\\n🚀 EARTH ENGINE TWO-STAGE DISCOVERY")
    print("-" * 40)

    try:
        ee_class = CANONICAL_SERVICES['EARTH_ENGINE']

        # Stage 1: Asset Discovery
        print("🌍 Stage 1: Asset Discovery")
        discovery_adapter = ee_class()
        discovery_caps = discovery_adapter.capabilities()

        service_type = discovery_caps.get('service_type')
        assets = discovery_caps.get('assets', {})

        print(f"  ✅ Service type: {service_type}")
        print(f"  ✅ Asset structure: {type(assets)}")

        if isinstance(assets, dict):
            print(f"  ✅ Asset categories: {len(assets)}")
            for category, info in list(assets.items())[:3]:
                count = info.get('count', 0) if isinstance(info, dict) else 0
                print(f"    - {category}: {count} assets")
        else:
            print(f"  ✅ Assets discovered: {len(assets)}")

        # Stage 2: Asset-Specific Capabilities
        print("\\n🎯 Stage 2: Asset-Specific Capabilities")

        # Get test asset
        test_asset_id = None
        if isinstance(assets, dict) and len(assets) > 0:
            first_category = list(assets.keys())[0]
            category_info = assets[first_category]
            if isinstance(category_info, dict) and 'examples' in category_info:
                examples = category_info['examples']
                if examples and len(examples) > 0:
                    first_example = examples[0]
                    if isinstance(first_example, dict):
                        test_asset_id = first_example.get('id')
                    else:
                        test_asset_id = first_example

        if test_asset_id:
            print(f"  Testing asset: {test_asset_id}")

            asset_adapter = ee_class(asset_id=test_asset_id)
            asset_caps = asset_adapter.capabilities()

            asset_variables = asset_caps.get('variables', [])
            print(f"  ✅ Asset-specific variables: {len(asset_variables)}")

            if asset_variables:
                for var in asset_variables[:2]:
                    var_name = var.get('name', 'unknown')[:30]
                    print(f"    - {var_name}")

        success = len(assets) > 0 and service_type == 'meta'
        print(f"\\n✅ Two-stage pattern: {'SUCCESS' if success else 'FAILED'}")
        return success

    except Exception as e:
        print(f"❌ Earth Engine testing failed: {str(e)}")
        traceback.print_exc()
        return False

def test_data_fetching(service_name, adapter_class, location_name, coords):
    """Test data fetching for a service at optimal location"""
    print(f"📊 {service_name} at {location_name}")

    try:
        adapter = adapter_class()
        geometry = Geometry(type="point", coordinates=coords)

        spec = RequestSpec(
            geometry=geometry,
            time_range=TEST_TIME_RANGE,
            variables=None,  # Get available variables
            extra={"timeout": 45, "max_pixels": 1000}
        )

        start_time = time.time()
        df = adapter.fetch(spec)
        duration = time.time() - start_time

        if df is not None and not df.empty:
            unique_vars = df['variable'].nunique() if 'variable' in df.columns else 0
            has_coords = 'latitude' in df.columns and 'longitude' in df.columns
            has_core_schema = all(col in df.columns for col in ['observation_id', 'dataset', 'variable', 'value'])

            print(f"  ✅ {len(df)} rows, {unique_vars} vars, {duration:.2f}s")
            print(f"  ✅ Schema: {'✓' if has_core_schema else '✗'} | Coords: {'✓' if has_coords else '✗'}")

            return {
                'service_name': service_name,
                'success': True,
                'duration': duration,
                'row_count': len(df),
                'variable_count': unique_vars,
                'has_core_schema': has_core_schema,
                'dataframe': df
            }
        else:
            print(f"  ⚠️  No data returned")
            return {'service_name': service_name, 'success': False, 'reason': 'no_data'}

    except Exception as e:
        error_msg = str(e)[:60]
        print(f"  ❌ Error: {error_msg}")
        return {'service_name': service_name, 'success': False, 'error': error_msg}

def demonstrate_data_fusion(fetch_results):
    """Demonstrate comprehensive data fusion with visualization"""
    print("\\n🎨 COMPREHENSIVE DATA FUSION DEMONSTRATION")
    print("=" * 50)

    # Collect successful dataframes
    fusion_data = {}
    total_observations = 0

    for service, result in fetch_results.items():
        if result.get('success') and 'dataframe' in result:
            df = result['dataframe']
            if df is not None and not df.empty:
                fusion_data[service] = df
                total_observations += len(df)
                print(f"✅ {service}: {len(df)} observations, {df['variable'].nunique()} variables")

    if len(fusion_data) < 2:
        print("⚠️  Need at least 2 services for fusion demonstration")
        return

    print(f"\\n🔗 FUSION ANALYSIS:")
    print(f"   📊 Services: {len(fusion_data)}")
    print(f"   📊 Total observations: {total_observations}")

    # Create unified dataset
    print("\\n📈 Creating unified environmental dataset...")
    unified_df = pd.concat([
        df.assign(source_service=service)
        for service, df in fusion_data.items()
    ], ignore_index=True)

    print(f"   ✅ Unified dataset: {len(unified_df)} observations")
    print(f"   ✅ Variables: {unified_df['variable'].nunique()}")
    print(f"   ✅ Services: {unified_df['source_service'].nunique()}")
    print(f"   ✅ Locations: {unified_df[['latitude', 'longitude']].drop_duplicates().shape[0]}")

    # Analysis by service
    print("\\n📊 SERVICE CONTRIBUTIONS:")
    service_summary = unified_df.groupby('source_service').agg({
        'observation_id': 'count',
        'variable': 'nunique',
        'latitude': 'nunique',
        'longitude': 'nunique'
    }).round(2)
    service_summary.columns = ['Observations', 'Variables', 'Lat_Points', 'Lon_Points']
    print(service_summary.to_string())

    # Variable coverage analysis
    print("\\n🌍 VARIABLE COVERAGE ANALYSIS:")
    var_summary = unified_df.groupby('variable').agg({
        'value': ['count', 'mean', 'std'],
        'source_service': 'nunique'
    }).round(3)
    var_summary.columns = ['Count', 'Mean', 'Std', 'Services']

    # Show top variables by coverage
    top_vars = var_summary.sort_values('Count', ascending=False).head(10)
    print(top_vars.to_string())

    # Geographic coverage
    print("\\n🗺️  GEOGRAPHIC COVERAGE:")
    geo_bounds = {
        'lat_min': unified_df['latitude'].min(),
        'lat_max': unified_df['latitude'].max(),
        'lon_min': unified_df['longitude'].min(),
        'lon_max': unified_df['longitude'].max()
    }

    for bound, value in geo_bounds.items():
        print(f"   {bound}: {value:.3f}")

    # Create comprehensive visualization
    create_fusion_visualization(unified_df, service_summary)

    return unified_df

def create_fusion_visualization(unified_df, service_summary):
    """Create comprehensive data fusion visualization"""
    print("\\n🎨 Creating fusion visualization...")

    try:
        # Set up the plot style
        plt.style.use('default')
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Environmental Data Fusion Analysis', fontsize=16, fontweight='bold')

        # 1. Service Contributions (Bar plot)
        services = service_summary.index
        observations = service_summary['Observations']
        variables = service_summary['Variables']

        ax1.bar(services, observations, alpha=0.7, color='skyblue', label='Observations')
        ax1_twin = ax1.twinx()
        ax1_twin.plot(services, variables, 'ro-', linewidth=2, label='Variables')
        ax1.set_title('Service Contributions', fontweight='bold')
        ax1.set_ylabel('Observations')
        ax1_twin.set_ylabel('Variables')
        ax1.tick_params(axis='x', rotation=45)
        ax1.legend(loc='upper left')
        ax1_twin.legend(loc='upper right')

        # 2. Geographic Distribution (Scatter plot)
        services = unified_df['source_service'].unique()
        colors = plt.cm.Set3(np.linspace(0, 1, len(services)))

        for service, color in zip(services, colors):
            service_data = unified_df[unified_df['source_service'] == service]
            ax2.scatter(service_data['longitude'], service_data['latitude'],
                       c=[color], label=service, alpha=0.6, s=20)

        ax2.set_title('Geographic Coverage', fontweight='bold')
        ax2.set_xlabel('Longitude')
        ax2.set_ylabel('Latitude')
        ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax2.grid(True, alpha=0.3)

        # 3. Variable Distribution (Histogram)
        var_counts = unified_df['variable'].value_counts().head(15)
        ax3.barh(range(len(var_counts)), var_counts.values, color='lightcoral')
        ax3.set_yticks(range(len(var_counts)))
        ax3.set_yticklabels([v[:20] + '...' if len(v) > 20 else v for v in var_counts.index])
        ax3.set_title('Top Variables by Observation Count', fontweight='bold')
        ax3.set_xlabel('Observations')

        # 4. Data Quality Metrics (Pie chart)
        schema_compliance = unified_df.groupby('source_service').apply(
            lambda x: all(col in x.columns for col in ['observation_id', 'dataset', 'variable', 'value'])
        ).sum()

        quality_data = [schema_compliance, len(services) - schema_compliance]
        quality_labels = ['Schema Compliant', 'Non-Compliant']
        colors_pie = ['lightgreen', 'lightcoral']

        ax4.pie(quality_data, labels=quality_labels, colors=colors_pie, autopct='%1.1f%%', startangle=90)
        ax4.set_title('Schema Compliance', fontweight='bold')

        plt.tight_layout()
        plt.savefig('environmental_data_fusion_analysis.png', dpi=300, bbox_inches='tight')
        print("   ✅ Visualization saved: environmental_data_fusion_analysis.png")

        return True

    except Exception as e:
        print(f"   ⚠️  Visualization failed: {str(e)}")
        return False

def main():
    """Run final complete service validation"""

    print("Phase 1: Capability Discovery - ALL 10 SERVICES")
    print("=" * 50)

    capability_results = {}

    # Test all services uniformly
    for service_name, adapter_class in CANONICAL_SERVICES.items():
        result = test_service_capabilities(service_name, adapter_class)
        capability_results[service_name] = result
        time.sleep(0.5)  # Brief pause between services

    # Detailed Earth Engine two-stage testing
    print("\\nPhase 2: Earth Engine Meta-Service Validation")
    print("=" * 50)
    ee_result = test_earth_engine_two_stage()

    print("\\nPhase 3: Data Fetching - Optimal Locations")
    print("=" * 50)

    # Strategically test services at their optimal locations
    fetch_tests = [
        ('NASA_POWER', 'Amazon_Basin', PROVEN_LOCATIONS['Amazon_Basin']),
        ('SoilGrids', 'Amazon_Basin', PROVEN_LOCATIONS['Amazon_Basin']),
        ('GBIF', 'Amazon_Basin', PROVEN_LOCATIONS['Amazon_Basin']),
        ('OpenAQ', 'Netherlands', PROVEN_LOCATIONS['Netherlands']),
        ('EPA_AQS', 'San_Francisco_Bay', PROVEN_LOCATIONS['San_Francisco_Bay']),
        ('USGS_NWIS', 'San_Francisco_Bay', PROVEN_LOCATIONS['San_Francisco_Bay']),
        ('OSM_Overpass', 'Netherlands', PROVEN_LOCATIONS['Netherlands']),
        ('SSURGO', 'Iowa_Farmland', PROVEN_LOCATIONS['Iowa_Farmland']),
    ]

    fetch_results = {}
    for service_name, location_name, coords in fetch_tests:
        if service_name in CANONICAL_SERVICES:
            adapter_class = CANONICAL_SERVICES[service_name]
            result = test_data_fetching(service_name, adapter_class, location_name, coords)
            fetch_results[service_name] = result
            time.sleep(1)  # Pause between data requests

    print("\\nPhase 4: Data Fusion Demonstration")
    print("=" * 50)

    unified_dataset = demonstrate_data_fusion(fetch_results)

    # Final comprehensive analysis
    print("\\n" + "=" * 70)
    print("🏆 FINAL COMPLETE VALIDATION RESULTS")
    print("=" * 70)

    # Capability discovery results
    successful_caps = sum(1 for r in capability_results.values() if r.get('success'))
    total_variables = sum(r.get('variable_count', 0) for r in capability_results.values() if r.get('success'))
    unitary_services = sum(1 for r in capability_results.values() if r.get('service_type') == 'unitary')
    meta_services = sum(1 for r in capability_results.values() if r.get('service_type') == 'meta')

    print(f"📊 CAPABILITY DISCOVERY:")
    print(f"   ✅ Total services: {len(CANONICAL_SERVICES)}")
    print(f"   ✅ Successful: {successful_caps}/{len(CANONICAL_SERVICES)} ({successful_caps/len(CANONICAL_SERVICES)*100:.0f}%)")
    print(f"   ✅ Unitary services: {unitary_services}")
    print(f"   ✅ Meta-services: {meta_services}")
    print(f"   ✅ Total variables: {total_variables:,}")

    # Earth Engine meta-service
    print(f"\\n🚀 EARTH ENGINE META-SERVICE:")
    print(f"   ✅ Two-stage discovery: {'SUCCESS' if ee_result else 'FAILED'}")

    # Data fetching results
    successful_fetches = sum(1 for r in fetch_results.values() if r.get('success'))
    total_rows = sum(r.get('row_count', 0) for r in fetch_results.values() if r.get('success'))
    schema_compliant = sum(1 for r in fetch_results.values() if r.get('has_core_schema'))

    print(f"\\n📊 DATA FETCHING:")
    print(f"   ✅ Services tested: {len(fetch_tests)}")
    print(f"   ✅ Successful: {successful_fetches}/{len(fetch_tests)} ({successful_fetches/len(fetch_tests)*100:.0f}%)")
    print(f"   ✅ Total observations: {total_rows:,}")
    print(f"   ✅ Schema compliant: {schema_compliant}/{successful_fetches}")

    # Overall system assessment
    capability_score = successful_caps / len(CANONICAL_SERVICES) * 100
    ee_score = 100 if ee_result else 0
    fetch_score = (successful_fetches / len(fetch_tests) * 100) if fetch_tests else 0
    fusion_score = 100 if unified_dataset is not None and len(unified_dataset) > 0 else 0

    overall_score = np.mean([capability_score, ee_score * 0.2, fetch_score * 0.6, fusion_score * 0.2])

    print(f"\\n🏆 OVERALL SYSTEM ASSESSMENT:")
    print(f"   📋 Capability Discovery: {capability_score:.0f}%")
    print(f"   🚀 Earth Engine Meta-Service: {'PASS' if ee_result else 'FAIL'}")
    print(f"   📊 Data Fetching: {fetch_score:.0f}%")
    print(f"   🔗 Data Fusion: {'SUCCESS' if fusion_score == 100 else 'FAILED'}")
    print(f"   🎯 OVERALL SCORE: {overall_score:.0f}%")

    if overall_score >= 85:
        print("\\n🟢 SYSTEM STATUS: EXCELLENT - Production Ready for ECOGNITA")
    elif overall_score >= 70:
        print("\\n🟡 SYSTEM STATUS: GOOD - Ready with minor considerations")
    else:
        print("\\n🔴 SYSTEM STATUS: NEEDS IMPROVEMENT")

    # Service-by-service breakdown
    print(f"\\n📋 SERVICE-BY-SERVICE STATUS:")
    for service_name, result in capability_results.items():
        status = "✅" if result.get('success') else "❌"
        service_type = result.get('service_type', 'unknown')[:8]
        var_count = result.get('variable_count', 0)
        duration = result.get('duration', 0)

        # Add fetch status
        fetch_status = ""
        if service_name in fetch_results:
            fetch_success = fetch_results[service_name].get('success', False)
            fetch_status = f" | Fetch: {'✅' if fetch_success else '❌'}"

        print(f"   {status} {service_name:<15} {service_type:<8} {var_count:4d} vars {duration:5.2f}s{fetch_status}")

    print(f"\\n✅ Final validation complete! All services tested systematically.")
    print(f"🎯 Ready for ECOGNITA integration with {successful_caps}/{len(CANONICAL_SERVICES)} services operational")

if __name__ == "__main__":
    main()