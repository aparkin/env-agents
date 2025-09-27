#!/usr/bin/env python3
"""
Comprehensive data retrieval test with full visibility
Tests actual data fetching from each service with metadata and provenance inspection
"""

import sys
import pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from env_agents.core.router import EnvRouter
from env_agents.core.models import Geometry, RequestSpec
from datetime import datetime, timedelta
import json

# Test locations and parameters
BERKELEY_CA = [-122.27, 37.87]
SACRAMENTO_CA = [-121.5, 38.6] 
DAVIS_CA = [-121.74, 38.54]

def inspect_dataframe(df, service_name, test_name):
    """Detailed DataFrame inspection with visibility"""
    print(f"\n📊 {service_name} - {test_name}")
    print("=" * 60)
    
    if df is None or df.empty:
        print("  ❌ No data returned")
        return
    
    # Basic info
    print(f"  📏 Shape: {df.shape[0]} rows × {df.shape[1]} columns")
    print(f"  💾 Memory: {df.memory_usage(deep=True).sum() / 1024:.1f} KB")
    
    # Column analysis
    print(f"\n  📋 Columns ({len(df.columns)}):")
    for i, col in enumerate(df.columns):
        dtype = str(df[col].dtype)
        null_count = df[col].isnull().sum()
        unique_count = df[col].nunique()
        print(f"    {i+1:2d}. {col:<25} | {dtype:<10} | {null_count:3d} nulls | {unique_count:4d} unique")
    
    # Semantic columns inspection
    semantic_cols = ["variable", "value", "unit", "observed_property_uri", "unit_uri", "preferred_unit"]
    available_semantic = [col for col in semantic_cols if col in df.columns]
    print(f"\n  🔬 Semantic Columns: {len(available_semantic)}/{len(semantic_cols)}")
    for col in available_semantic:
        if col == "variable":
            variables = df[col].unique()
            print(f"    📈 Variables ({len(variables)}): {list(variables)[:3]}{'...' if len(variables) > 3 else ''}")
        elif col == "value":
            val_stats = df[col].describe()
            print(f"    📊 Values: min={val_stats['min']:.3f}, max={val_stats['max']:.3f}, mean={val_stats['mean']:.3f}")
        elif col == "unit":
            units = df[col].unique()
            print(f"    📏 Units ({len(units)}): {list(units)}")
        else:
            unique_vals = df[col].unique()
            print(f"    🏷️  {col}: {len(unique_vals)} unique values")
    
    # Provenance inspection
    if "provenance" in df.columns:
        print(f"\n  📚 Provenance Sample:")
        sample_prov = df["provenance"].iloc[0] if not df.empty else {}
        if isinstance(sample_prov, (str, dict)):
            try:
                prov_dict = json.loads(sample_prov) if isinstance(sample_prov, str) else sample_prov
                for key, value in prov_dict.items():
                    print(f"    {key}: {str(value)[:50]}{'...' if len(str(value)) > 50 else ''}")
            except:
                print(f"    Raw: {str(sample_prov)[:100]}...")
    
    # Attributes inspection
    if "attributes" in df.columns:
        print(f"\n  🏷️  Attributes Sample:")
        sample_attr = df["attributes"].iloc[0] if not df.empty else {}
        if isinstance(sample_attr, (str, dict)):
            try:
                attr_dict = json.loads(sample_attr) if isinstance(sample_attr, str) else sample_attr
                for key, value in attr_dict.items():
                    print(f"    {key}: {str(value)[:50]}{'...' if len(str(value)) > 50 else ''}")
            except:
                print(f"    Raw: {str(sample_attr)[:100]}...")
    
    # Sample data rows
    print(f"\n  📋 Sample Data (first 3 rows):")
    key_cols = ["time", "variable", "value", "unit", "latitude", "longitude"]
    available_key_cols = [col for col in key_cols if col in df.columns]
    if available_key_cols:
        print(df[available_key_cols].head(3).to_string(index=False))
    
    print()

def test_comprehensive_data_retrieval():
    print("🧪 Comprehensive Data Retrieval Test")
    print("=" * 70)
    
    # Setup router
    router = EnvRouter(base_dir=".")
    
    # Register all services
    services = {}
    
    # NASA POWER
    try:
        from env_agents.adapters.power.adapter import NasaPowerDailyAdapter
        power_adapter = NasaPowerDailyAdapter()
        router.register(power_adapter)
        services["NASA_POWER"] = power_adapter
        print("✅ NASA POWER registered")
    except Exception as e:
        print(f"❌ NASA POWER failed: {e}")
    
    # OpenAQ (requires API key)
    try:
        from env_agents.adapters.openaq.adapter import OpenaqV3Adapter
        openaq_adapter = OpenaqV3Adapter()
        router.register(openaq_adapter)
        services["OpenAQ"] = openaq_adapter
        print("✅ OpenAQ registered (API key required for data)")
    except Exception as e:
        print(f"❌ OpenAQ failed: {e}")
    
    # USGS NWIS
    try:
        from env_agents.adapters.nwis.adapter import UsgsNwisLiveAdapter
        nwis_adapter = UsgsNwisLiveAdapter()
        router.register(nwis_adapter)
        services["USGS_NWIS"] = nwis_adapter
        print("✅ USGS NWIS registered")
    except Exception as e:
        print(f"❌ USGS NWIS failed: {e}")
    
    # USDA SURGO
    try:
        from env_agents.adapters.soil.surgo_adapter import UsdaSurgoAdapter
        surgo_adapter = UsdaSurgoAdapter()
        router.register(surgo_adapter)
        services["USDA_SURGO"] = surgo_adapter
        print("✅ USDA SURGO registered")
    except Exception as e:
        print(f"❌ USDA SURGO failed: {e}")
    
    # ISRIC SoilGrids
    try:
        from env_agents.adapters.soil.soilgrids_adapter import IsricSoilGridsAdapter
        soilgrids_adapter = IsricSoilGridsAdapter()
        router.register(soilgrids_adapter)
        services["ISRIC_SoilGrids"] = soilgrids_adapter
        print("✅ ISRIC SoilGrids registered")
    except Exception as e:
        print(f"❌ ISRIC SoilGrids failed: {e}")
    
    print(f"\n📊 Total Services: {len(services)}")
    
    # Test scenarios for each service
    test_scenarios = {
        "NASA_POWER": {
            "spec": RequestSpec(
                geometry=Geometry(type="point", coordinates=BERKELEY_CA),
                time_range=("2023-01-01", "2023-01-03"),
                variables=["atm:air_temperature_2m", "atm:precip_total"]
            ),
            "description": "Weather data for Berkeley, CA (2 days)"
        },
        "USGS_NWIS": {
            "spec": RequestSpec(
                geometry=Geometry(type="point", coordinates=SACRAMENTO_CA),
                time_range=("2023-01-01T00:00:00Z", "2023-01-01T06:00:00Z"),
                variables=["water:discharge_cfs"],
                extra={"max_sites": 1}
            ),
            "description": "Stream discharge near Sacramento, CA (6 hours)"
        },
        "OpenAQ": {
            "spec": RequestSpec(
                geometry=Geometry(type="point", coordinates=BERKELEY_CA),
                time_range=("2023-01-01", "2023-01-02"),
                variables=["air:pm25", "air:o3"],
                extra={"radius_m": 5000, "max_sensors": 2}
            ),
            "description": "Air quality data for Berkeley, CA (1 day) - requires API key"
        },
        "USDA_SURGO": {
            "spec": RequestSpec(
                geometry=Geometry(type="point", coordinates=DAVIS_CA),
                variables=["soil:clay_percent", "soil:sand_percent", "soil:ph"]
            ),
            "description": "Soil properties for Davis, CA"
        },
        "ISRIC_SoilGrids": {
            "spec": RequestSpec(
                geometry=Geometry(type="point", coordinates=DAVIS_CA),
                variables=["soil:clay", "soil:sand", "soil:phh2o"],
                extra={"depth": "0-5cm"}
            ),
            "description": "Global soil data for Davis, CA (0-5cm depth)"
        }
    }
    
    # Run tests for each registered service
    results = {}
    
    for service_name, adapter in services.items():
        if service_name not in test_scenarios:
            continue
            
        scenario = test_scenarios[service_name]
        print(f"\n🔍 Testing {service_name}")
        print(f"📝 {scenario['description']}")
        
        try:
            # Fetch data
            start_time = datetime.now()
            df = router.fetch(service_name, scenario["spec"])
            duration = datetime.now() - start_time
            
            # Inspect results
            inspect_dataframe(df, service_name, scenario["description"])
            print(f"  ⏱️  Duration: {duration.total_seconds():.2f}s")
            
            results[service_name] = {
                "success": True,
                "rows": len(df) if df is not None else 0,
                "columns": len(df.columns) if df is not None else 0,
                "duration_seconds": duration.total_seconds(),
                "has_semantic": any(col in df.columns for col in ["observed_property_uri", "unit_uri"] if df is not None),
                "variables": list(df["variable"].unique()) if df is not None and "variable" in df.columns else []
            }
            
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            results[service_name] = {
                "success": False,
                "error": str(e),
                "duration_seconds": 0
            }
    
    # Summary
    print(f"\n🎯 Test Summary")
    print("=" * 40)
    
    successful = sum(1 for r in results.values() if r.get("success", False))
    total_tests = len(results)
    total_rows = sum(r.get("rows", 0) for r in results.values())
    avg_duration = sum(r.get("duration_seconds", 0) for r in results.values()) / max(len(results), 1)
    
    print(f"✅ Success Rate: {successful}/{total_tests} ({successful/total_tests:.1%})")
    print(f"📊 Total Data: {total_rows} rows")
    print(f"⏱️  Avg Duration: {avg_duration:.2f}s")
    
    for service, result in results.items():
        if result.get("success"):
            rows = result.get("rows", 0)
            vars_count = len(result.get("variables", []))
            semantic = "✅" if result.get("has_semantic") else "❌"
            print(f"  {service}: {rows} rows, {vars_count} variables, semantic: {semantic}")
        else:
            print(f"  {service}: ❌ {result.get('error', 'Unknown error')}")
    
    return results

if __name__ == "__main__":
    results = test_comprehensive_data_retrieval()
    
    # Exit code based on success rate
    successful = sum(1 for r in results.values() if r.get("success", False))
    total = len(results)
    
    if successful == total:
        print(f"\n🎉 All tests passed!")
        sys.exit(0)
    elif successful > 0:
        print(f"\n⚠️  Partial success: {successful}/{total}")
        sys.exit(1)
    else:
        print(f"\n💥 All tests failed")
        sys.exit(2)