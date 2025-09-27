# Environmental Data Services Demo - Salinas, California
# Run this code in a Jupyter notebook for interactive exploration

import sys
from pathlib import Path
import pandas as pd
import json
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Add the env_agents path
sys.path.insert(0, str(Path('.').absolute()))

from env_agents.core.router import EnvRouter
from env_agents.core.models import Geometry, RequestSpec

# Salinas, California coordinates
SALINAS_CA = [-121.6555, 36.6777]
print("🥬 Environmental Data Services Demo - Salinas, California")
print("=" * 60)

# Initialize router
router = EnvRouter(base_dir=".")

# Register all services
services = {}

print("\n📋 Registering Services...")

# NASA POWER - Weather/Climate
try:
    from env_agents.adapters.power.adapter import NasaPowerDailyAdapter
    power_adapter = NasaPowerDailyAdapter()
    router.register(power_adapter)
    services["NASA_POWER"] = power_adapter
    print("  ✅ NASA POWER - Weather & climate data")
except Exception as e:
    print(f"  ❌ NASA POWER failed: {e}")

# OpenAQ - Air Quality  
try:
    from env_agents.adapters.openaq.adapter import OpenaqV3Adapter
    openaq_adapter = OpenaqV3Adapter()
    router.register(openaq_adapter)
    services["OpenAQ"] = openaq_adapter
    print("  ✅ OpenAQ - Air quality monitoring (requires API key)")
except Exception as e:
    print(f"  ❌ OpenAQ failed: {e}")

# USGS NWIS - Water Resources
try:
    from env_agents.adapters.nwis.adapter import UsgsNwisLiveAdapter
    nwis_adapter = UsgsNwisLiveAdapter()
    router.register(nwis_adapter)
    services["USGS_NWIS"] = nwis_adapter
    print("  ✅ USGS NWIS - Water resources & monitoring")
except Exception as e:
    print(f"  ❌ USGS NWIS failed: {e}")

# USDA SURGO - Soil Survey (US)
try:
    from env_agents.adapters.soil.surgo_adapter import UsdaSurgoAdapter
    surgo_adapter = UsdaSurgoAdapter()
    router.register(surgo_adapter)
    services["USDA_SURGO"] = surgo_adapter
    print("  ✅ USDA SURGO - US soil survey data")
except Exception as e:
    print(f"  ❌ USDA SURGO failed: {e}")

# ISRIC SoilGrids - Global Soil Data
try:
    from env_agents.adapters.soil.soilgrids_adapter import IsricSoilGridsAdapter
    soilgrids_adapter = IsricSoilGridsAdapter()
    router.register(soilgrids_adapter)
    services["ISRIC_SoilGrids"] = soilgrids_adapter
    print("  ✅ ISRIC SoilGrids - Global soil properties")
except Exception as e:
    print(f"  ❌ ISRIC SoilGrids failed: {e}")

print(f"\n📊 Total Services Registered: {len(services)}")

# ============================================================================
# PART 1: SERVICE CAPABILITIES
# ============================================================================

print("\n" + "="*60)
print("🔍 PART 1: SERVICE CAPABILITIES")
print("="*60)

def display_capabilities(service_name, adapter):
    """Display service capabilities in a clear format"""
    print(f"\n📡 {service_name}")
    print("-" * 40)
    
    try:
        caps = adapter.capabilities()
        
        # Basic info
        print(f"Dataset: {caps.get('dataset', 'N/A')}")
        print(f"Geometry: {caps.get('geometry', [])}")
        print(f"Requires API Key: {caps.get('requires_api_key', False)}")
        print(f"Requires Time Range: {caps.get('requires_time_range', False)}")
        
        # Variables
        variables = caps.get('variables', [])
        print(f"\n📊 Available Variables ({len(variables)}):")
        
        for i, var in enumerate(variables[:10], 1):  # Show first 10
            canonical = var.get('canonical', 'N/A')
            platform = var.get('platform', 'N/A')
            unit = var.get('unit', '')
            description = var.get('description', '')[:50]
            print(f"  {i:2d}. {canonical}")
            print(f"      Platform: {platform}")
            print(f"      Unit: {unit}")
            print(f"      Description: {description}...")
            print()
        
        if len(variables) > 10:
            print(f"      ... and {len(variables) - 10} more variables")
        
        # Rate limits and notes
        rate_limits = caps.get('rate_limits', {})
        if rate_limits:
            print(f"⚡ Rate Limits: {rate_limits}")
        
        notes = caps.get('notes', '')
        if notes:
            print(f"📝 Notes: {notes}")
            
    except Exception as e:
        print(f"❌ Error getting capabilities: {e}")

# Display capabilities for all services
for service_name, adapter in services.items():
    display_capabilities(service_name, adapter)

# ============================================================================
# PART 2: DATA RETRIEVAL EXAMPLES
# ============================================================================

print("\n\n" + "="*60)
print("📊 PART 2: DATA RETRIEVAL - SALINAS, CA")
print("="*60)

# Define test scenarios for each service
test_scenarios = {
    "NASA_POWER": {
        "spec": RequestSpec(
            geometry=Geometry(type="point", coordinates=SALINAS_CA),
            time_range=("2023-07-01", "2023-07-03"),  # Summer in Salinas
            variables=["atm:air_temperature_2m", "atm:precip_total"]
        ),
        "description": "Weather data for Salinas during summer harvest season"
    },
    "USGS_NWIS": {
        "spec": RequestSpec(
            geometry=Geometry(type="point", coordinates=SALINAS_CA),
            time_range=("2023-07-01T00:00:00Z", "2023-07-01T12:00:00Z"),
            variables=["water:discharge_cfs", "water:temperature"],
            extra={"max_sites": 3}
        ),
        "description": "Stream and groundwater monitoring near Salinas River"
    },
    "USDA_SURGO": {
        "spec": RequestSpec(
            geometry=Geometry(type="point", coordinates=SALINAS_CA),
            variables=["soil:clay_percent", "soil:sand_percent", "soil:organic_matter"]
        ),
        "description": "Agricultural soil properties in Salinas Valley"
    },
    "ISRIC_SoilGrids": {
        "spec": RequestSpec(
            geometry=Geometry(type="point", coordinates=SALINAS_CA),
            variables=["soil:clay", "soil:sand", "soil:soc"],
            extra={"depth": "0-5cm"}
        ),
        "description": "Global soil data for Salinas Valley (topsoil)"
    },
    "OpenAQ": {
        "spec": RequestSpec(
            geometry=Geometry(type="point", coordinates=SALINAS_CA),
            time_range=("2023-07-01", "2023-07-02"),
            variables=["air:pm25", "air:o3"],
            extra={"radius_m": 10000, "max_sensors": 3}
        ),
        "description": "Air quality monitoring in Salinas area (requires API key)"
    }
}

# Store results for later analysis
results = {}

def fetch_and_display(service_name, scenario):
    """Fetch data and display results clearly"""
    print(f"\n🌱 {service_name}")
    print(f"📝 {scenario['description']}")
    print("-" * 50)
    
    try:
        start_time = datetime.now()
        df = router.fetch(service_name, scenario["spec"])
        duration = datetime.now() - start_time
        
        if df is None or df.empty:
            print("❌ No data returned")
            results[service_name] = None
            return None
        
        # Basic info
        print(f"📊 Shape: {df.shape[0]} rows × {df.shape[1]} columns")
        print(f"⏱️  Duration: {duration.total_seconds():.2f}s")
        
        # Show key columns
        key_columns = ["time", "variable", "value", "unit", "latitude", "longitude"]
        available_keys = [col for col in key_columns if col in df.columns]
        
        if available_keys and len(df) > 0:
            print(f"\n📈 Sample Data:")
            display_df = df[available_keys].head(3)
            for i, (idx, row) in enumerate(display_df.iterrows()):
                print(f"  Row {i+1}:")
                for col in available_keys:
                    value = row[col]
                    print(f"    {col}: {value}")
                print()
        
        # Semantic columns
        semantic_cols = ["observed_property_uri", "unit_uri", "preferred_unit"]
        semantic_present = [col for col in semantic_cols if col in df.columns and not df[col].isna().all()]
        
        if semantic_present:
            print(f"🔬 Semantic Integration:")
            for col in semantic_present:
                unique_vals = df[col].dropna().unique()
                print(f"  {col}: {len(unique_vals)} unique values")
                if len(unique_vals) > 0 and pd.notna(unique_vals[0]):
                    print(f"    Sample: {unique_vals[0]}")
        
        results[service_name] = df
        return df
        
    except Exception as e:
        print(f"❌ Error: {str(e)[:100]}...")
        results[service_name] = None
        return None

# Fetch data from each service
for service_name, adapter in services.items():
    if service_name in test_scenarios:
        fetch_and_display(service_name, test_scenarios[service_name])

# ============================================================================
# PART 3: DETAILED PROVENANCE INSPECTION
# ============================================================================

print("\n\n" + "="*60)
print("🔍 PART 3: PROVENANCE & METADATA ANALYSIS")
print("="*60)

def display_provenance(service_name, df):
    """Display provenance information in a clear format"""
    print(f"\n📚 {service_name} - Detailed Provenance")
    print("-" * 45)
    
    if df is None or df.empty:
        print("❌ No data to analyze")
        return
    
    # Basic provenance from standard columns
    if not df.empty:
        first_row = df.iloc[0]
        
        print("🏷️  Data Source:")
        print(f"  Dataset: {first_row.get('dataset', 'N/A')}")
        print(f"  Source URL: {first_row.get('source_url', 'N/A')}")
        print(f"  Version: {first_row.get('source_version', 'N/A')}")
        print(f"  License: {first_row.get('license', 'N/A')}")
        print(f"  Retrieved: {first_row.get('retrieval_timestamp', 'N/A')}")
        
        print(f"\n🌍 Spatial Context:")
        print(f"  Latitude: {first_row.get('latitude', 'N/A')}")
        print(f"  Longitude: {first_row.get('longitude', 'N/A')}")
        print(f"  Geometry Type: {first_row.get('geometry_type', 'N/A')}")
        
        print(f"\n⏰ Temporal Context:")
        print(f"  Time: {first_row.get('time', 'N/A')}")
        print(f"  Temporal Coverage: {first_row.get('temporal_coverage', 'N/A')}")
    
    # Detailed provenance from provenance column
    if "provenance" in df.columns and not df["provenance"].isna().all():
        print(f"\n🔍 Detailed Provenance:")
        prov = df["provenance"].iloc[0]
        
        if isinstance(prov, dict):
            for key, value in prov.items():
                if key == "request_geometry":
                    print(f"  Request Geometry: {value}")
                elif key == "request_variables":
                    print(f"  Requested Variables: {value}")
                elif key == "execution_time":
                    print(f"  Execution Time: {value}s")
                elif key == "upstream":
                    print(f"  Upstream Source: {value}")
                else:
                    str_value = str(value)[:50] + ("..." if len(str(value)) > 50 else "")
                    print(f"  {key}: {str_value}")
        elif isinstance(prov, str):
            try:
                prov_dict = json.loads(prov)
                for key, value in prov_dict.items():
                    str_value = str(value)[:50] + ("..." if len(str(value)) > 50 else "")
                    print(f"  {key}: {str_value}")
            except:
                print(f"  Raw provenance: {prov[:100]}...")
    
    # Attributes analysis
    if "attributes" in df.columns and not df["attributes"].isna().all():
        print(f"\n🏷️  Service-Specific Attributes:")
        attrs = df["attributes"].iloc[0]
        
        if isinstance(attrs, dict):
            for key, value in attrs.items():
                str_value = str(value)[:40] + ("..." if len(str(value)) > 40 else "")
                print(f"  {key}: {str_value}")
    
    # DataFrame metadata
    if hasattr(df, 'attrs') and df.attrs:
        print(f"\n📊 DataFrame Metadata:")
        attrs = df.attrs
        
        if 'schema' in attrs:
            schema = attrs['schema']
            print(f"  Schema Version: {schema}")
            
        if 'capabilities' in attrs:
            caps = attrs['capabilities']
            print(f"  Service Capabilities: {len(caps.get('variables', []))} variables available")
            
        if 'variable_registry' in attrs:
            registry = attrs['variable_registry']
            print(f"  Registry Variables: {len(registry.get('variables', {}))}")

# Display provenance for all successful retrievals
for service_name, df in results.items():
    if df is not None:
        display_provenance(service_name, df)

# ============================================================================
# PART 4: SUMMARY STATISTICS
# ============================================================================

print("\n\n" + "="*60)
print("📊 PART 4: SUMMARY STATISTICS")
print("="*60)

successful_retrievals = sum(1 for df in results.values() if df is not None)
total_rows = sum(len(df) for df in results.values() if df is not None)

print(f"\n🎯 Overall Results:")
print(f"  Services Tested: {len(results)}")
print(f"  Successful Retrievals: {successful_retrievals}")
print(f"  Total Data Rows: {total_rows}")
print(f"  Success Rate: {successful_retrievals/len(results):.1%}")

print(f"\n📈 By Service:")
for service_name, df in results.items():
    if df is not None:
        variables = df["variable"].nunique() if "variable" in df.columns else 0
        time_span = ""
        if "time" in df.columns and len(df) > 1:
            times = pd.to_datetime(df["time"], errors='coerce').dropna()
            if len(times) > 1:
                time_span = f" ({times.min()} to {times.max()})"
        
        print(f"  ✅ {service_name}: {len(df)} rows, {variables} variables{time_span}")
    else:
        print(f"  ❌ {service_name}: No data retrieved")

print(f"\n🌱 Ready for analysis! All DataFrames are stored in the 'results' dictionary.")
print("   Use results['NASA_POWER'], results['USGS_NWIS'], etc. for further analysis.")

# Make results easily accessible
nasa_power_data = results.get("NASA_POWER")
usgs_nwis_data = results.get("USGS_NWIS") 
surgo_data = results.get("USDA_SURGO")
soilgrids_data = results.get("ISRIC_SoilGrids")
openaq_data = results.get("OpenAQ")

print(f"\n💡 Quick Access Variables:")
print(f"  nasa_power_data  - Weather/climate data")
print(f"  usgs_nwis_data   - Water monitoring data") 
print(f"  surgo_data       - US soil survey data")
print(f"  soilgrids_data   - Global soil data")
print(f"  openaq_data      - Air quality data")