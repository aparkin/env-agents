# =============================================================================
# WORKING JUPYTER NOTEBOOK DEMO - Salinas Valley Environmental Data
# This uses the exact parameters that work from our successful tests
# =============================================================================

# CELL 1: Setup and Imports
# -------------------------
import sys
from pathlib import Path
import pandas as pd
import json
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Add the env_agents path
sys.path.insert(0, str(Path('.').absolute()))

from env_agents.core.router import EnvRouter
from env_agents.core.models import Geometry, RequestSpec

print("🥬 Environmental Data Services - Working Demo")
print("Using proven parameters from successful tests")
print("=" * 60)


# CELL 2: Service Registration (Same as before)
# ---------------------------------------------
router = EnvRouter(base_dir=".")
services = {}

print("📋 Registering Environmental Data Services...")

# NASA POWER
try:
    from env_agents.adapters.power.adapter import NasaPowerDailyAdapter
    power_adapter = NasaPowerDailyAdapter()
    router.register(power_adapter)
    services["NASA_POWER"] = power_adapter
    print("  ✅ NASA POWER - Daily weather data")
except Exception as e:
    print(f"  ❌ NASA POWER failed: {e}")

# USGS NWIS  
try:
    from env_agents.adapters.nwis.adapter import UsgsNwisLiveAdapter
    nwis_adapter = UsgsNwisLiveAdapter()
    router.register(nwis_adapter)
    services["USGS_NWIS"] = nwis_adapter
    print("  ✅ USGS NWIS - Water monitoring")
except Exception as e:
    print(f"  ❌ USGS NWIS failed: {e}")

# OpenAQ
try:
    from env_agents.adapters.openaq.adapter import OpenaqV3Adapter
    openaq_adapter = OpenaqV3Adapter()
    router.register(openaq_adapter)
    services["OpenAQ"] = openaq_adapter
    print("  ✅ OpenAQ - Air quality (API key required)")
except Exception as e:
    print(f"  ❌ OpenAQ failed: {e}")

print(f"\n📊 Total Services: {len(services)}")


# CELL 3: Working NASA POWER Test
# -------------------------------
print("\n🌤️ NASA POWER - Weather Data (PROVEN TO WORK)")
print("=" * 55)

# Use exact parameters from successful test
power_spec = RequestSpec(
    geometry=Geometry(type="point", coordinates=[-122.27, 37.87]),  # Berkeley (working location)
    time_range=("2023-01-01", "2023-01-02"),  # Known working dates
    variables=["atm:air_temperature_2m"]  # Single variable that works
)

try:
    weather_df = router.fetch("NASA_POWER", power_spec)
    print(f"✅ SUCCESS: {len(weather_df)} rows × {len(weather_df.columns)} columns")
    
    # Show the data structure
    print(f"\n📊 Data Structure:")
    print(f"  Variables: {list(weather_df['variable'].unique())}")
    print(f"  Time range: {weather_df['time'].min()} to {weather_df['time'].max()}")
    print(f"  Values: {weather_df['value'].min():.2f} to {weather_df['value'].max():.2f}")
    print(f"  Unit: {weather_df['unit'].iloc[0]}")
    
    # Show semantic integration
    print(f"\n🔬 Semantic Integration:")
    semantic_cols = ["observed_property_uri", "unit_uri", "preferred_unit"]
    for col in semantic_cols:
        if col in weather_df.columns:
            unique_count = weather_df[col].nunique()
            print(f"  {col}: {unique_count} unique values")
    
    # Sample data
    print(f"\n📈 Sample Data:")
    display_cols = ["time", "variable", "value", "unit", "latitude", "longitude"]
    print(weather_df[display_cols].head(3).to_string(index=False))
    
except Exception as e:
    print(f"❌ FAILED: {e}")
    weather_df = None


# CELL 4: Working USGS NWIS Test
# ------------------------------
print(f"\n💧 USGS NWIS - Water Data (PROVEN TO WORK)")
print("=" * 45)

# Use exact parameters from successful test
nwis_spec = RequestSpec(
    geometry=Geometry(type="point", coordinates=[-121.5, 38.6]),  # Sacramento area (working)
    time_range=("2023-01-01T00:00:00Z", "2023-01-01T06:00:00Z"),  # Short time window
    variables=["water:discharge_cfs"],  # Single working variable
    extra={"max_sites": 1}  # Limit to 1 site
)

try:
    water_df = router.fetch("USGS_NWIS", nwis_spec)
    print(f"✅ SUCCESS: {len(water_df)} rows × {len(water_df.columns)} columns")
    
    if len(water_df) > 0:
        # Show data details
        print(f"\n📊 Water Data:")
        print(f"  Sites: {water_df['site_name'].nunique() if 'site_name' in water_df.columns else 'N/A'}")
        print(f"  Variables: {list(water_df['variable'].unique()) if 'variable' in water_df.columns else 'N/A'}")
        
        # Sample data
        print(f"\n📈 Sample Data:")
        display_cols = ["time", "site_name", "variable", "value", "unit"]
        available_cols = [col for col in display_cols if col in water_df.columns]
        if available_cols:
            print(water_df[available_cols].head(3).to_string(index=False))
    else:
        print("ℹ️  No monitoring stations found in this area/time")
        print("   This is normal - USGS monitoring is sparse")
    
except Exception as e:
    print(f"❌ FAILED: {e}")
    water_df = None


# CELL 5: Alternative Locations Test
# ----------------------------------
print(f"\n🌍 Testing Different California Locations")
print("=" * 45)

# Test multiple California locations to find what works
test_locations = {
    "Berkeley, CA": [-122.27, 37.87],
    "Salinas, CA": [-121.6555, 36.6777], 
    "Sacramento, CA": [-121.5, 38.6],
    "San Francisco, CA": [-122.4194, 37.7749],
    "Los Angeles, CA": [-118.2437, 34.0522]
}

working_locations = {}

for location_name, coords in test_locations.items():
    print(f"\n🗺️  Testing {location_name}...")
    
    # Test NASA POWER for this location
    try:
        test_spec = RequestSpec(
            geometry=Geometry(type="point", coordinates=coords),
            time_range=("2023-01-01", "2023-01-02"),
            variables=["atm:air_temperature_2m"]
        )
        
        test_df = router.fetch("NASA_POWER", test_spec)
        if len(test_df) > 0:
            avg_temp = test_df['value'].mean()
            print(f"  ✅ Weather: {len(test_df)} rows, avg temp: {avg_temp:.1f}°C")
            working_locations[location_name] = {
                'coords': coords,
                'weather_data': len(test_df),
                'avg_temp': avg_temp
            }
        else:
            print(f"  ❌ Weather: No data")
            
    except Exception as e:
        print(f"  ❌ Weather: {str(e)[:50]}...")

print(f"\n🎯 Working Locations Summary:")
for location, data in working_locations.items():
    print(f"  ✅ {location}: {data['weather_data']} weather records, {data['avg_temp']:.1f}°C avg")


# CELL 6: Detailed Provenance for Working Data
# --------------------------------------------
def show_detailed_provenance(df, service_name):
    """Show detailed provenance information"""
    if df is None or len(df) == 0:
        print(f"❌ No data available for {service_name}")
        return
        
    print(f"\n📚 {service_name} - Detailed Provenance")
    print("=" * 50)
    
    first_row = df.iloc[0]
    
    # Core provenance
    print("🏷️ Data Source:")
    print(f"  Dataset: {first_row.get('dataset')}")
    print(f"  Source URL: {first_row.get('source_url')}")
    print(f"  Version: {first_row.get('source_version')}")
    print(f"  License: {first_row.get('license')}")
    print(f"  Retrieved: {first_row.get('retrieval_timestamp')}")
    
    # Spatial info
    print(f"\n🌍 Location:")
    print(f"  Latitude: {first_row.get('latitude')}")
    print(f"  Longitude: {first_row.get('longitude')}")
    print(f"  Geometry Type: {first_row.get('geometry_type')}")
    
    # Temporal info
    print(f"\n⏰ Time Information:")
    print(f"  Time: {first_row.get('time')}")
    print(f"  Coverage: {first_row.get('temporal_coverage')}")
    
    # Quality info
    print(f"\n✅ Quality Control:")
    qc_flags = df['qc_flag'].value_counts() if 'qc_flag' in df.columns else {}
    print(f"  QC Flags: {dict(qc_flags)}")
    
    # Service attributes
    if 'attributes' in df.columns and pd.notna(first_row.get('attributes')):
        print(f"\n🏷️ Service Attributes:")
        attrs = first_row['attributes']
        if isinstance(attrs, dict):
            for key, value in list(attrs.items())[:5]:
                print(f"  {key}: {value}")
    
    # DataFrame metadata
    if hasattr(df, 'attrs'):
        print(f"\n📊 DataFrame Metadata:")
        if 'capabilities' in df.attrs:
            caps = df.attrs['capabilities']
            var_count = len(caps.get('variables', []))
            print(f"  Available Variables: {var_count}")
        if 'variable_registry' in df.attrs:
            registry = df.attrs['variable_registry']
            reg_vars = len(registry.get('variables', {}))
            print(f"  Registry Variables: {reg_vars}")

# Show provenance for successful retrievals
if weather_df is not None:
    show_detailed_provenance(weather_df, "NASA POWER Weather")
    
if water_df is not None:
    show_detailed_provenance(water_df, "USGS NWIS Water")


# CELL 7: Service Capabilities Summary
# ------------------------------------
print(f"\n📊 SERVICE CAPABILITIES SUMMARY")
print("=" * 40)

for service_name, adapter in services.items():
    try:
        caps = adapter.capabilities()
        variables = caps.get('variables', [])
        
        print(f"\n🔧 {service_name}:")
        print(f"  Variables: {len(variables)}")
        print(f"  Geometry Support: {caps.get('geometry', [])}")
        print(f"  API Key Required: {caps.get('requires_api_key', False)}")
        print(f"  Time Range Required: {caps.get('requires_time_range', False)}")
        
        # Show a few example variables
        print(f"  Sample Variables:")
        for i, var in enumerate(variables[:3], 1):
            canonical = var.get('canonical', 'N/A')
            unit = var.get('unit', 'N/A')
            print(f"    {i}. {canonical} ({unit})")
            
    except Exception as e:
        print(f"\n🔧 {service_name}: Error getting capabilities - {e}")


# CELL 8: Final Summary and Data Access
# -------------------------------------
print(f"\n🎉 FINAL SUMMARY")
print("=" * 30)

# Count successful retrievals
successful_services = []
total_rows = 0

if weather_df is not None and len(weather_df) > 0:
    successful_services.append("NASA POWER")
    total_rows += len(weather_df)
    
if water_df is not None and len(water_df) > 0:
    successful_services.append("USGS NWIS")
    total_rows += len(water_df)

print(f"✅ Successful Services: {len(successful_services)}/3")
print(f"📊 Total Data Rows: {total_rows}")
print(f"🌍 Working Locations: {len(working_locations)}")

if successful_services:
    print(f"\n📈 Available Data:")
    if weather_df is not None:
        print(f"  weather_df: NASA POWER weather data ({len(weather_df)} rows)")
    if water_df is not None:
        print(f"  water_df: USGS NWIS water data ({len(water_df)} rows)")
        
    print(f"\n💡 Next Steps:")
    print(f"  - Analyze temperature patterns in weather_df")
    print(f"  - Examine water discharge patterns in water_df") 
    print(f"  - Try different time ranges and locations")
    print(f"  - Add API key for OpenAQ air quality data")
    
print(f"\n🏁 Demo Complete! Data ready for environmental analysis.")


# OPTIONAL CELL 9: Quick Analysis
# -------------------------------
if weather_df is not None:
    print(f"\n📈 QUICK WEATHER ANALYSIS")
    print("=" * 30)
    
    # Temperature analysis
    temp_stats = weather_df['value'].describe()
    print(f"Temperature Statistics (°C):")
    print(f"  Mean: {temp_stats['mean']:.2f}")
    print(f"  Min: {temp_stats['min']:.2f}")
    print(f"  Max: {temp_stats['max']:.2f}")
    print(f"  Range: {temp_stats['max'] - temp_stats['min']:.2f}")
    
    # Convert to Fahrenheit for US users
    temp_f = weather_df['value'] * 9/5 + 32
    print(f"\nIn Fahrenheit:")
    print(f"  Mean: {temp_f.mean():.2f}°F")
    print(f"  Range: {temp_f.min():.2f}°F to {temp_f.max():.2f}°F")

print(f"\n🔬 All data is accessible via variable names:")
print(f"   weather_df  - NASA POWER weather data")
print(f"   water_df    - USGS NWIS water data")
print(f"   services    - Dictionary of all registered services")
print(f"   working_locations - Dictionary of tested California locations")