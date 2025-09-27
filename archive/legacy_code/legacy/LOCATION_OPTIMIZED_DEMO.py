# =============================================================================
# LOCATION-OPTIMIZED COMPREHENSIVE DEMO
# Uses service-specific locations for maximum success rates
# =============================================================================

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Import handling (assumes your namespace fix is applied)
from env_agents.core.router import EnvRouter
from env_agents.core.models import Geometry, RequestSpec
from env_agents.adapters.power.adapter import NasaPowerDailyAdapter
from env_agents.adapters.nwis.adapter import UsgsNwisLiveAdapter
from env_agents.adapters.soil.surgo_adapter import UsdaSurgoAdapter
from env_agents.adapters.openaq.adapter import OpenaqV3Adapter

print("🌍 LOCATION-OPTIMIZED ENVIRONMENTAL SERVICES DEMO")
print("=" * 60)
print(f"🕐 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Initialize router
router = EnvRouter(base_dir=".")

# Register all adapters
adapters = [
    ("NASA_POWER", NasaPowerDailyAdapter()),
    ("USGS_NWIS", UsgsNwisLiveAdapter()),  
    ("USDA_SURGO", UsdaSurgoAdapter()),
    ("OpenAQ", OpenaqV3Adapter())
]

registered_services = []
for name, adapter in adapters:
    try:
        router.register(adapter)
        registered_services.append(name)
        print(f"✅ {name} registered")
    except Exception as e:
        print(f"⚠️  {name} registration failed: {str(e)[:50]}...")

print(f"\n📊 Active Services: {len(registered_services)}")

# =============================================================================
# SERVICE-SPECIFIC OPTIMIZED LOCATIONS
# =============================================================================

# NASA POWER: Known good locations with reliable data
nasa_locations = {
    "Iowa_Farmland": [-93.5, 42.0],      # Iowa - major agricultural area
    "Kansas_Wheat": [-98.5, 39.0],       # Kansas - wheat belt
    "Nebraska_Corn": [-96.5, 41.0]       # Nebraska - corn belt
}

# USGS NWIS: Known active USGS gage stations
usgs_locations = {
    "Mississippi_StLouis": [-90.2, 38.6],    # Major river gage
    "Colorado_River_TX": [-98.5, 30.3],      # Texas Colorado River
    "Hudson_River_NY": [-73.9, 42.7]         # Hudson River gage
}

# SURGO: California agricultural areas (known working)
surgo_locations = {
    "Davis_CA": [-121.74, 38.54],
    "Salinas_Valley": [-121.6555, 36.6777],
    "Central_Valley": [-120.5, 37.0]
}

# OpenAQ: Major cities with air quality monitoring
openaq_locations = {
    "Los_Angeles": [-118.2, 34.0],
    "San_Francisco": [-122.4, 37.8],
    "Sacramento": [-121.5, 38.5]
}

# =============================================================================
# OPTIMIZED TESTING WITH BETTER PARAMETERS
# =============================================================================

results = {}

# Test NASA POWER with agricultural focus and recent dates
if "NASA_POWER" in registered_services:
    print(f"\n🌤️  TESTING NASA POWER - AGRICULTURAL WEATHER")
    print("=" * 50)
    
    # Use recent dates (NASA POWER likes recent data better)
    end_date = datetime.now() - timedelta(days=7)  # 1 week ago
    start_date = end_date - timedelta(days=30)     # 30-day period
    
    nasa_results = []
    for location_name, coords in nasa_locations.items():
        try:
            print(f"📍 {location_name} {coords}")
            
            spec = RequestSpec(
                geometry=Geometry(type="point", coordinates=coords),
                variables=["atm:t2m", "atm:precip"],  # Just 2 key variables
                time_range=(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
            )
            
            df = router.fetch("NASA_POWER", spec)
            
            if df is not None and len(df) > 0:
                vars_found = df['variable'].unique()
                print(f"  ✅ {len(df)} rows, {len(vars_found)} variables")
                nasa_results.append((location_name, df))
            else:
                print(f"  ℹ️  No data returned")
                
        except Exception as e:
            print(f"  ❌ Error: {str(e)[:60]}...")
    
    results["NASA_POWER"] = nasa_results

# Test USGS NWIS at known gage locations
if "USGS_NWIS" in registered_services:
    print(f"\n🌊 TESTING USGS NWIS - RIVER GAGES")
    print("=" * 40)
    
    usgs_results = []
    for location_name, coords in usgs_locations.items():
        try:
            print(f"📍 {location_name} {coords}")
            
            # Request recent data (last 7 days)
            spec = RequestSpec(
                geometry=Geometry(type="point", coordinates=coords),
                variables=["water:discharge_cfs"],  # Just discharge
                time_range=((datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"), datetime.now().strftime("%Y-%m-%d"))
            )
            
            df = router.fetch("USGS_NWIS", spec)
            
            if df is not None and len(df) > 0:
                vars_found = df['variable'].unique()
                print(f"  ✅ {len(df)} rows, {len(vars_found)} variables")
                usgs_results.append((location_name, df))
            else:
                print(f"  ℹ️  No data returned")
                
        except Exception as e:
            print(f"  ❌ Error: {str(e)[:60]}...")
    
    results["USGS_NWIS"] = usgs_results

# Test SURGO (known working)
if "USDA_SURGO" in registered_services:
    print(f"\n🌱 TESTING USDA SURGO - SOIL SURVEY")
    print("=" * 40)
    
    surgo_results = []
    for location_name, coords in surgo_locations.items():
        try:
            print(f"📍 {location_name} {coords}")
            
            spec = RequestSpec(
                geometry=Geometry(type="point", coordinates=coords),
                variables=["*"]  # All soil properties
            )
            
            df = router.fetch("USDA_SURGO", spec)
            
            if df is not None and len(df) > 0:
                vars_found = df['variable'].unique()
                print(f"  ✅ {len(df)} rows, {len(vars_found)} variables")
                surgo_results.append((location_name, df))
            else:
                print(f"  ℹ️  No data returned")
                
        except Exception as e:
            print(f"  ❌ Error: {str(e)[:60]}...")
    
    results["USDA_SURGO"] = surgo_results

# Test OpenAQ at major cities
if "OpenAQ" in registered_services:
    print(f"\n🏭 TESTING OPENAQ - AIR QUALITY")
    print("=" * 35)
    
    openaq_results = []
    for location_name, coords in openaq_locations.items():
        try:
            print(f"📍 {location_name} {coords}")
            
            spec = RequestSpec(
                geometry=Geometry(type="point", coordinates=coords),
                variables=["air:pm25"],  # Just PM2.5
                time_range=((datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"), datetime.now().strftime("%Y-%m-%d"))
            )
            
            df = router.fetch("OpenAQ", spec)
            
            if df is not None and len(df) > 0:
                vars_found = df['variable'].unique()
                print(f"  ✅ {len(df)} rows, {len(vars_found)} variables")
                openaq_results.append((location_name, df))
            else:
                print(f"  ℹ️  No data returned")
                
        except Exception as e:
            print(f"  ❌ Error: {str(e)[:60]}...")
    
    results["OpenAQ"] = openaq_results

# =============================================================================
# OPTIMIZED RESULTS SUMMARY
# =============================================================================

print(f"\n📊 LOCATION-OPTIMIZED RESULTS SUMMARY")
print("=" * 45)

total_data_points = 0
successful_services = 0

for service_name in registered_services:
    if service_name in results:
        service_results = results[service_name]
        service_rows = sum(len(df) for _, df in service_results)
        successful_locations = len(service_results)
        
        if service_rows > 0:
            successful_services += 1
            total_data_points += service_rows
            print(f"✅ {service_name}: {successful_locations} locations, {service_rows} rows")
        else:
            print(f"⚠️  {service_name}: 0 locations successful")
    else:
        print(f"❌ {service_name}: Not tested")

print(f"\n🎯 OVERALL PERFORMANCE:")
print(f"   • Successful services: {successful_services}/{len(registered_services)}")
print(f"   • Total data points: {total_data_points}")

# Create combined datasets for successful services
print(f"\n📋 DATA ACCESS:")
for service_name, service_results in results.items():
    if service_results:
        combined_data = []
        for location_name, df in service_results:
            df_copy = df.copy()
            df_copy['location'] = location_name
            combined_data.append(df_copy)
        
        if combined_data:
            combined_df = pd.concat(combined_data, ignore_index=True)
            variable_name = f"combined_{service_name.lower().replace('_', '')}"
            locals()[variable_name] = combined_df
            print(f"   📊 {variable_name}: {len(combined_df)} rows")

# =============================================================================
# RECOMMENDATIONS FOR NON-WORKING SERVICES
# =============================================================================

print(f"\n🔧 TROUBLESHOOTING RECOMMENDATIONS:")
print("=" * 40)

if "NASA_POWER" in results and not results["NASA_POWER"]:
    print(f"🌤️  NASA POWER Issues:")
    print(f"   • Try different date ranges (NASA has temporal limitations)")
    print(f"   • Check parameter format in NASA adapter")
    print(f"   • Test international locations")

if "USGS_NWIS" in results and not results["USGS_NWIS"]:
    print(f"🌊 USGS NWIS Issues:")
    print(f"   • Need exact USGS gage station coordinates")
    print(f"   • Use USGS Water Data site to find active gages")
    print(f"   • Try major rivers with known monitoring stations")

if "OpenAQ" in results and not results["OpenAQ"]:
    print(f"🏭 OpenAQ Issues:")
    print(f"   • Requires OPENAQ_API_KEY environment variable")
    print(f"   • Check API key validity")
    print(f"   • Verify OpenAQ service availability")

print(f"\n✨ LOCATION-OPTIMIZED DEMO COMPLETE!")
print(f"🎯 Used service-specific locations for maximum success rates!")