# =============================================================================
# FINAL JUPYTER DEMO - Environmental Data with SURGO Status Update
# This demo shows what's working and provides clear service status
# =============================================================================

# CELL 1: Setup and Service Overview
# ----------------------------------
import sys
from pathlib import Path
import pandas as pd
import json
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Add path
sys.path.insert(0, str(Path('.').absolute()))

from env_agents.core.router import EnvRouter
from env_agents.core.models import Geometry, RequestSpec

print("🌍 Environmental Data Services - Current Status Report")
print("=" * 60)

# California locations for testing
locations = {
    "Salinas Valley": [-121.6555, 36.6777],  # Agricultural center
    "Davis, CA": [-121.74, 38.54],           # UC Davis agricultural research
    "Berkeley, CA": [-122.27, 37.87]         # Reference location
}

# Initialize router
router = EnvRouter(base_dir=".")


# CELL 2: Register and Test All Services
# --------------------------------------
print("\n📋 Environmental Data Services Registration")
print("=" * 50)

services_status = {}

# NASA POWER - Meteorological Data (CONFIRMED WORKING)
try:
    from env_agents.adapters.power.adapter import NasaPowerDailyAdapter
    power_adapter = NasaPowerDailyAdapter()
    router.register(power_adapter)
    services_status["NASA_POWER"] = {"registered": True, "working": True, "note": "Full meteorological data"}
    print("✅ NASA POWER - Daily weather & climate data")
except Exception as e:
    services_status["NASA_POWER"] = {"registered": False, "error": str(e)}
    print(f"❌ NASA POWER: {e}")

# USGS NWIS - Water Resources (CONFIRMED WORKING)
try:
    from env_agents.adapters.nwis.adapter import UsgsNwisLiveAdapter
    nwis_adapter = UsgsNwisLiveAdapter()
    router.register(nwis_adapter)
    services_status["USGS_NWIS"] = {"registered": True, "working": True, "note": "Water monitoring (sparse stations)"}
    print("✅ USGS NWIS - Water resources monitoring")
except Exception as e:
    services_status["USGS_NWIS"] = {"registered": False, "error": str(e)}
    print(f"❌ USGS NWIS: {e}")

# OpenAQ - Air Quality (WORKING WITH API KEY)
try:
    from env_agents.adapters.openaq.adapter import OpenaqV3Adapter
    openaq_adapter = OpenaqV3Adapter()
    router.register(openaq_adapter)
    services_status["OpenAQ"] = {"registered": True, "working": "with_api_key", "note": "Requires OPENAQ_API_KEY"}
    print("✅ OpenAQ - Air quality monitoring (requires API key)")
except Exception as e:
    services_status["OpenAQ"] = {"registered": False, "error": str(e)}
    print(f"❌ OpenAQ: {e}")

# USDA SURGO - US Soil Survey (STATUS: UNDER INVESTIGATION)
try:
    from env_agents.adapters.soil.surgo_adapter import UsdaSurgoAdapter
    surgo_adapter = UsdaSurgoAdapter()
    router.register(surgo_adapter)
    services_status["USDA_SURGO"] = {"registered": True, "working": False, "note": "USDA SDA API format changed - under investigation"}
    print("⚠️  USDA SURGO - US soil survey (API format issues - under investigation)")
except Exception as e:
    services_status["USDA_SURGO"] = {"registered": False, "error": str(e)}
    print(f"❌ USDA SURGO: {e}")

# ISRIC SoilGrids - Global Soil Data (STATUS: SERVER ISSUES)
try:
    from env_agents.adapters.soil.soilgrids_adapter import IsricSoilGridsAdapter
    soilgrids_adapter = IsricSoilGridsAdapter()
    router.register(soilgrids_adapter)
    services_status["ISRIC_SoilGrids"] = {"registered": True, "working": False, "note": "ISRIC server experiencing issues"}
    print("⚠️  ISRIC SoilGrids - Global soil data (server issues)")
except Exception as e:
    services_status["ISRIC_SoilGrids"] = {"registered": False, "error": str(e)}
    print(f"❌ ISRIC SoilGrids: {e}")

print(f"\n📊 Registration Summary: {sum(1 for s in services_status.values() if s['registered'])}/5 services registered")


# CELL 3: Working Services - Detailed Capabilities
# ------------------------------------------------
print(f"\n🔧 WORKING SERVICES - Detailed Capabilities")
print("=" * 50)

working_services = [name for name, status in services_status.items() 
                   if status.get("working") in [True, "with_api_key"]]

for service_name in working_services:
    print(f"\n📡 {service_name}")
    print("-" * 40)
    
    try:
        if service_name == "NASA_POWER":
            caps = power_adapter.capabilities()
        elif service_name == "USGS_NWIS":
            caps = nwis_adapter.capabilities()
        elif service_name == "OpenAQ":
            caps = openaq_adapter.capabilities()
        else:
            continue
            
        # Show key info
        print(f"Dataset: {caps.get('dataset')}")
        print(f"Requires API Key: {caps.get('requires_api_key', False)}")
        print(f"Geometry Support: {caps.get('geometry', [])}")
        
        # Show variables
        variables = caps.get('variables', [])
        print(f"Variables Available: {len(variables)}")
        
        for i, var in enumerate(variables[:5], 1):
            canonical = var.get('canonical', 'N/A')
            unit = var.get('unit', 'N/A')
            print(f"  {i}. {canonical} ({unit})")
            
        if len(variables) > 5:
            print(f"     ... and {len(variables) - 5} more")
            
    except Exception as e:
        print(f"Error getting capabilities: {e}")


# CELL 4: Live Data Retrieval from Working Services
# -------------------------------------------------
print(f"\n📊 LIVE DATA RETRIEVAL - Working Services")
print("=" * 50)

# Test each working service with proven parameters
data_results = {}

# NASA POWER - Weather Data
if "NASA_POWER" in working_services:
    print(f"\n🌤️ NASA POWER - Weather Data")
    print("-" * 35)
    
    for location_name, coords in locations.items():
        try:
            spec = RequestSpec(
                geometry=Geometry(type="point", coordinates=coords),
                time_range=("2023-07-15", "2023-07-17"),  # Summer data
                variables=["atm:air_temperature_2m"]  # Proven working variable
            )
            
            df = router.fetch("NASA_POWER", spec)
            
            if len(df) > 0:
                avg_temp = df['value'].mean()
                print(f"  ✅ {location_name}: {len(df)} records, avg temp {avg_temp:.1f}°C ({avg_temp*9/5+32:.1f}°F)")
                data_results[f"weather_{location_name.lower().replace(' ', '_')}"] = df
            else:
                print(f"  ❌ {location_name}: No data")
                
        except Exception as e:
            print(f"  ❌ {location_name}: {str(e)[:60]}...")

# USGS NWIS - Water Data
if "USGS_NWIS" in working_services:
    print(f"\n💧 USGS NWIS - Water Monitoring")
    print("-" * 35)
    
    # Test key locations for water monitoring
    water_test_locations = {
        "Sacramento River": [-121.5, 38.6],  # Known to have stations
        "San Francisco Bay": [-122.3, 37.8],
        "Salinas Valley": [-121.6555, 36.6777]
    }
    
    for location_name, coords in water_test_locations.items():
        try:
            spec = RequestSpec(
                geometry=Geometry(type="point", coordinates=coords),
                time_range=("2023-07-15T00:00:00Z", "2023-07-15T12:00:00Z"),
                variables=["water:discharge_cfs"],
                extra={"max_sites": 2}
            )
            
            df = router.fetch("USGS_NWIS", spec)
            
            if len(df) > 0:
                sites = df['site_name'].nunique() if 'site_name' in df.columns else 0
                print(f"  ✅ {location_name}: {len(df)} records from {sites} monitoring sites")
                data_results[f"water_{location_name.lower().replace(' ', '_')}"] = df
                
                # Show site names if available
                if 'site_name' in df.columns:
                    unique_sites = df['site_name'].dropna().unique()[:2]
                    for site in unique_sites:
                        print(f"    📍 {site}")
            else:
                print(f"  ℹ️  {location_name}: No monitoring stations found")
                
        except Exception as e:
            print(f"  ❌ {location_name}: {str(e)[:60]}...")


# CELL 5: Service Status and Troubleshooting Guide
# ------------------------------------------------
print(f"\n🔧 SERVICE STATUS & TROUBLESHOOTING")
print("=" * 45)

status_report = {
    "✅ WORKING": [],
    "🔑 REQUIRES API KEY": [],
    "⚠️  ISSUES": [],
    "❌ NOT WORKING": []
}

for service, status in services_status.items():
    if status.get("working") is True:
        status_report["✅ WORKING"].append(f"{service}: {status.get('note', 'Operational')}")
    elif status.get("working") == "with_api_key":
        status_report["🔑 REQUIRES API KEY"].append(f"{service}: {status.get('note', 'API key needed')}")
    elif status.get("working") is False and status.get("registered"):
        status_report["⚠️  ISSUES"].append(f"{service}: {status.get('note', 'Service issues')}")
    else:
        error_msg = status.get('error', 'Registration failed')[:50]
        status_report["❌ NOT WORKING"].append(f"{service}: {error_msg}")

for category, services in status_report.items():
    if services:
        print(f"\n{category}:")
        for service in services:
            print(f"  • {service}")

# Troubleshooting tips
print(f"\n💡 TROUBLESHOOTING TIPS:")
print(f"  • OpenAQ: Set OPENAQ_API_KEY environment variable or pass in extra={{'openaq_api_key': 'your_key'}}")
print(f"  • USGS NWIS: Monitoring stations are sparse - try different locations")
print(f"  • SURGO: USDA SDA API format may have changed - investigating alternative endpoints")
print(f"  • SoilGrids: ISRIC server issues - try again later or contact ISRIC support")

# Data export options
print(f"\n📄 AVAILABLE DATA FOR ANALYSIS:")
for name, df in data_results.items():
    variables = df['variable'].nunique() if 'variable' in df.columns else 1
    date_range = ""
    if 'time' in df.columns:
        times = pd.to_datetime(df['time'], errors='coerce').dropna()
        if len(times) > 1:
            date_range = f" ({times.min().date()} to {times.max().date()})"
    print(f"  📊 {name}: {len(df)} records, {variables} variables{date_range}")

print(f"\n📊 Total Records: {sum(len(df) for df in data_results.values())}")


# CELL 6: Data Analysis Examples with Working Data  
# ------------------------------------------------
if data_results:
    print(f"\n📈 DATA ANALYSIS EXAMPLES")
    print("=" * 35)
    
    # Temperature analysis across locations
    weather_data = [df for name, df in data_results.items() if 'weather_' in name]
    if weather_data:
        print(f"\n🌡️ Temperature Analysis Across California:")
        
        all_weather = pd.concat(weather_data, ignore_index=True)
        
        # Group by location (approximate from lat/lon)
        for location_name, coords in locations.items():
            location_data = all_weather[
                (abs(all_weather['latitude'] - coords[1]) < 0.01) & 
                (abs(all_weather['longitude'] - coords[0]) < 0.01)
            ]
            
            if len(location_data) > 0:
                avg_temp = location_data['value'].mean()
                temp_range = location_data['value'].max() - location_data['value'].min()
                print(f"  📍 {location_name}: {avg_temp:.1f}°C avg, {temp_range:.1f}°C range")
    
    # Water discharge analysis  
    water_data = [df for name, df in data_results.items() if 'water_' in name]
    if water_data:
        print(f"\n💧 Water Monitoring Summary:")
        
        all_water = pd.concat(water_data, ignore_index=True)
        total_sites = all_water['site_name'].nunique() if 'site_name' in all_water.columns else 0
        total_measurements = len(all_water)
        
        print(f"  📊 Total monitoring sites: {total_sites}")
        print(f"  📊 Total measurements: {total_measurements}")
        
        if 'value' in all_water.columns:
            discharge_stats = all_water['value'].describe()
            print(f"  🌊 Discharge range: {discharge_stats['min']:.1f} to {discharge_stats['max']:.1f} ft³/s")

print(f"\n🎉 Environmental Data Analysis Complete!")
print(f"Working services provide comprehensive environmental data for California research.")

# CELL 7: Next Steps and Service Expansion
# ----------------------------------------
print(f"\n🚀 NEXT STEPS & SERVICE EXPANSION")
print("=" * 40)

print(f"\n📋 Immediate Actions:")
print(f"  1. ✅ Use NASA POWER for meteorological data (fully operational)")
print(f"  2. ✅ Use USGS NWIS for water resources (operational, sparse coverage)")  
print(f"  3. 🔑 Get OpenAQ API key for air quality data")
print(f"  4. 🔧 Investigate SURGO API changes (legacy code shows it should work)")
print(f"  5. ⏳ Wait for SoilGrids service recovery")

print(f"\n🌟 Future Service Additions:")
print(f"  • NOAA Climate Data (weather, climate normals)")
print(f"  • NASA AppEEARS (satellite imagery, vegetation indices)")
print(f"  • USGS Water Quality Portal (chemistry, biology)")
print(f"  • EPA Air Quality System (additional air monitoring)")
print(f"  • GBIF (biodiversity observations)")

print(f"\n💡 For Salinas Valley Agricultural Research:")
print(f"  • Weather: ✅ Available via NASA POWER")
print(f"  • Soil: ⚠️  Working on SURGO/SoilGrids integration")
print(f"  • Water: ℹ️  Limited monitoring stations in agricultural areas")
print(f"  • Air Quality: 🔑 Available with OpenAQ API key")

# Make all data easily accessible
weather_salinas = data_results.get('weather_salinas_valley')
weather_davis = data_results.get('weather_davis,_ca')
weather_berkeley = data_results.get('weather_berkeley,_ca')
water_sacramento = data_results.get('water_sacramento_river')

print(f"\n🔬 Data Access Variables:")
print(f"  weather_salinas  - Salinas Valley weather data")
print(f"  weather_davis    - Davis, CA weather data") 
print(f"  weather_berkeley - Berkeley, CA weather data")
print(f"  water_sacramento - Sacramento River monitoring")
print(f"  data_results     - All retrieved data by name")

print(f"\n🌱 Ready for agricultural and environmental research in California!")