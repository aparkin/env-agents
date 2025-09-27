# =============================================================================
# COMPREHENSIVE ENVIRONMENTAL SERVICES JUPYTER NOTEBOOK
# Tests all working services with full data and metadata display
# =============================================================================

# CELL 1: Setup and Imports
# -------------------------
import sys
from pathlib import Path
import pandas as pd
import json
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Add path for local modules
sys.path.insert(0, str(Path('.').absolute()))

from env_agents.core.router import EnvRouter
from env_agents.core.models import Geometry, RequestSpec

print("🌍 COMPREHENSIVE ENVIRONMENTAL SERVICES TEST")
print("=" * 60)
print(f"🕐 Test Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# CELL 2: Initialize Router and Register All Services
# ---------------------------------------------------
print(f"\n📋 INITIALIZING ENVIRONMENTAL SERVICES")
print("=" * 45)

router = EnvRouter(base_dir=".")
registered_services = {}
service_capabilities = {}

# NASA POWER - Meteorological Data
try:
    from env_agents.adapters.power.adapter import NasaPowerDailyAdapter
    power_adapter = NasaPowerDailyAdapter()
    router.register(power_adapter)
    registered_services["NASA_POWER"] = {
        "adapter": power_adapter, 
        "status": "✅ ACTIVE", 
        "note": "Global weather & climate data"
    }
    service_capabilities["NASA_POWER"] = power_adapter.capabilities()
    print("✅ NASA POWER - Daily weather & climate data")
except Exception as e:
    registered_services["NASA_POWER"] = {"status": "❌ FAILED", "error": str(e)}
    print(f"❌ NASA POWER: {e}")

# USGS NWIS - Water Resources  
try:
    from env_agents.adapters.nwis.adapter import UsgsNwisLiveAdapter
    nwis_adapter = UsgsNwisLiveAdapter()
    router.register(nwis_adapter)
    registered_services["USGS_NWIS"] = {
        "adapter": nwis_adapter,
        "status": "✅ ACTIVE", 
        "note": "Water monitoring (location-dependent)"
    }
    service_capabilities["USGS_NWIS"] = nwis_adapter.capabilities()
    print("✅ USGS NWIS - Water resources monitoring")
except Exception as e:
    registered_services["USGS_NWIS"] = {"status": "❌ FAILED", "error": str(e)}
    print(f"❌ USGS NWIS: {e}")

# OpenAQ - Air Quality
try:
    from env_agents.adapters.openaq.adapter import OpenaqV3Adapter
    openaq_adapter = OpenaqV3Adapter()
    router.register(openaq_adapter)
    registered_services["OpenAQ"] = {
        "adapter": openaq_adapter,
        "status": "⚠️  REQUIRES API KEY", 
        "note": "Air quality monitoring"
    }
    service_capabilities["OpenAQ"] = openaq_adapter.capabilities()
    print("⚠️  OpenAQ - Air quality monitoring (requires API key)")
except Exception as e:
    registered_services["OpenAQ"] = {"status": "❌ FAILED", "error": str(e)}
    print(f"❌ OpenAQ: {e}")

# USDA SURGO - Enhanced Soil Survey
try:
    from env_agents.adapters.soil.surgo_adapter import UsdaSurgoAdapter
    surgo_adapter = UsdaSurgoAdapter()
    router.register(surgo_adapter)
    registered_services["USDA_SURGO"] = {
        "adapter": surgo_adapter,
        "status": "✅ ACTIVE (ENHANCED)", 
        "note": "US soil survey with discovery & metadata support"
    }
    service_capabilities["USDA_SURGO"] = surgo_adapter.capabilities()
    print("✅ USDA SURGO - Enhanced US soil survey")
except Exception as e:
    registered_services["USDA_SURGO"] = {"status": "❌ FAILED", "error": str(e)}
    print(f"❌ USDA SURGO: {e}")

# ISRIC SoilGrids - Global Soil
try:
    from env_agents.adapters.soil.soilgrids_adapter import IsricSoilGridsAdapter
    soilgrids_adapter = IsricSoilGridsAdapter()
    router.register(soilgrids_adapter)
    registered_services["ISRIC_SoilGrids"] = {
        "adapter": soilgrids_adapter,
        "status": "⚠️  SERVER ISSUES", 
        "note": "Global soil data (intermittent)"
    }
    service_capabilities["ISRIC_SoilGrids"] = soilgrids_adapter.capabilities()
    print("⚠️  ISRIC SoilGrids - Global soil data")
except Exception as e:
    registered_services["ISRIC_SoilGrids"] = {"status": "❌ FAILED", "error": str(e)}
    print(f"❌ ISRIC SoilGrids: {e}")

active_services = [name for name, info in registered_services.items() 
                  if "✅ ACTIVE" in info.get("status", "")]

print(f"\n📊 Registration Summary: {len(active_services)} fully active services")
print(f"Active services: {', '.join(active_services)}")

# CELL 3: Service Capabilities Overview
# -------------------------------------
print(f"\n🔧 SERVICE CAPABILITIES OVERVIEW")
print("=" * 40)

def display_service_capabilities(service_name, caps):
    print(f"\n📡 {service_name}")
    print("-" * 30)
    
    if not caps:
        print("❌ No capabilities available")
        return
        
    print(f"Dataset: {caps.get('dataset', 'N/A')}")
    print(f"Geometry: {caps.get('geometry', 'N/A')}")  
    print(f"API Key Required: {caps.get('requires_api_key', False)}")
    print(f"Time Range Required: {caps.get('requires_time_range', 'N/A')}")
    
    variables = caps.get('variables', [])
    print(f"Variables Available: {len(variables)}")
    
    # Show sample variables with units
    for i, var in enumerate(variables[:5], 1):
        canonical = var.get('canonical', 'N/A')
        unit = var.get('unit', 'N/A')
        domain = var.get('domain', 'N/A')
        print(f"  {i}. {canonical} ({unit}) [{domain}]")
        
    if len(variables) > 5:
        print(f"     ... and {len(variables) - 5} more variables")
    
    # Additional metadata
    if 'spatial_resolution' in caps:
        print(f"Spatial Resolution: {caps['spatial_resolution']}")
    if 'temporal_coverage' in caps:
        print(f"Temporal Coverage: {caps['temporal_coverage']}")

# Display capabilities for each active service
for service_name in active_services:
    if service_name in service_capabilities:
        display_service_capabilities(service_name, service_capabilities[service_name])

# CELL 4: Define Test Locations and Parameters
# --------------------------------------------
print(f"\n📍 TEST LOCATIONS AND PARAMETERS")
print("=" * 40)

# Strategic test locations across different environments
test_locations = {
    "Davis_CA": {
        "coords": [-121.74, 38.54],
        "name": "Davis, CA",
        "description": "UC Davis agricultural research area", 
        "environment": "agricultural"
    },
    "Salinas_Valley": {
        "coords": [-121.6555, 36.6777], 
        "name": "Salinas Valley, CA",
        "description": "Major agricultural region",
        "environment": "agricultural"
    },
    "San_Francisco_Bay": {
        "coords": [-122.3, 37.8],
        "name": "San Francisco Bay, CA", 
        "description": "Urban coastal environment",
        "environment": "urban_coastal"
    },
    "Sacramento_River": {
        "coords": [-121.5, 38.6],
        "name": "Sacramento River, CA",
        "description": "Major water system",
        "environment": "riverine"
    }
}

# Service-specific test parameters
test_parameters = {
    "NASA_POWER": {
        "variables": ["atm:air_temperature_2m", "atm:precipitation_mm", "atm:solar_radiation"],
        "time_range": ("2023-07-15", "2023-07-17"),  # Summer data
        "locations": ["Davis_CA", "Salinas_Valley", "San_Francisco_Bay"]
    },
    "USGS_NWIS": {
        "variables": ["water:discharge_cfs", "water:temperature_celsius"],
        "time_range": ("2023-07-15T00:00:00Z", "2023-07-15T12:00:00Z"),
        "locations": ["Sacramento_River", "San_Francisco_Bay", "Davis_CA"],
        "extra": {"max_sites": 3}
    },
    "OpenAQ": {
        "variables": ["air:pm25_ugm3", "air:pm10_ugm3", "air:no2_ugm3"],
        "time_range": ("2023-07-15T00:00:00Z", "2023-07-15T12:00:00Z"),
        "locations": ["San_Francisco_Bay", "Davis_CA"],
        "extra": {"max_records": 100}
    },
    "USDA_SURGO": {
        "variables": ["*"],  # Test enhanced all-parameters capability
        "locations": ["Davis_CA", "Salinas_Valley"]
    },
    "ISRIC_SoilGrids": {
        "variables": ["soil:clay_content_percent", "soil:ph_h2o", "soil:organic_carbon_percent"],
        "locations": ["Davis_CA", "Salinas_Valley"]
    }
}

print("Test locations defined:")
for key, loc in test_locations.items():
    print(f"  • {loc['name']}: {loc['description']} ({loc['environment']})")

# CELL 5: Execute Comprehensive Service Tests  
# -------------------------------------------
print(f"\n🧪 EXECUTING COMPREHENSIVE SERVICE TESTS")
print("=" * 50)

# Storage for all results
all_results = {}
metadata_summary = {}

def test_service(service_name, service_params, router, test_locations):
    """Test a single service with comprehensive data collection"""
    
    print(f"\n🔬 Testing {service_name}")
    print("=" * (10 + len(service_name)))
    
    if service_name not in active_services:
        print(f"⚠️  {service_name} not active - skipping")
        return None, None
    
    results = {}
    service_metadata = {
        "service_name": service_name,
        "test_timestamp": datetime.now().isoformat(),
        "locations_tested": [],
        "variables_requested": service_params.get("variables", []),
        "parameters_used": service_params
    }
    
    for location_key in service_params["locations"]:
        location = test_locations[location_key]
        print(f"\n📍 Location: {location['name']} {location['coords']}")
        
        try:
            # Build request spec
            spec_params = {
                "geometry": Geometry(type="point", coordinates=location["coords"]),
                "variables": service_params["variables"]
            }
            
            # Add time range if specified
            if "time_range" in service_params:
                spec_params["time_range"] = service_params["time_range"]
            
            # Add extra parameters if specified
            if "extra" in service_params:
                spec_params["extra"] = service_params["extra"]
            
            spec = RequestSpec(**spec_params)
            
            # Execute query
            df = router.fetch(service_name, spec)
            
            if df is not None and len(df) > 0:
                # Successful data retrieval
                variables_returned = df['variable'].unique() if 'variable' in df.columns else ['unknown']
                unique_vars = len(variables_returned)
                total_rows = len(df)
                
                print(f"  ✅ SUCCESS: {total_rows} rows, {unique_vars} variables")
                print(f"     Variables: {list(variables_returned)}")
                
                # Data quality analysis
                if 'value' in df.columns:
                    values = df['value'].dropna()
                    if len(values) > 0:
                        print(f"     Value range: {values.min():.3f} to {values.max():.3f}")
                        print(f"     Valid values: {len(values)}/{total_rows} ({len(values)/total_rows*100:.1f}%)")
                
                # Time coverage analysis  
                if 'time' in df.columns:
                    times = pd.to_datetime(df['time'], errors='coerce').dropna()
                    if len(times) > 0:
                        time_span = times.max() - times.min()
                        print(f"     Time span: {times.min().date()} to {times.max().date()}")
                        print(f"     Duration: {time_span}")
                
                # Store results
                results[location_key] = {
                    "success": True,
                    "data": df,
                    "rows": total_rows,
                    "variables": unique_vars,
                    "variables_list": list(variables_returned),
                    "location": location,
                    "data_quality": {
                        "valid_values": len(values) if 'value' in df.columns else 0,
                        "total_rows": total_rows,
                        "completeness": len(values)/total_rows if 'value' in df.columns and total_rows > 0 else 0
                    }
                }
                
                service_metadata["locations_tested"].append({
                    "location": location_key,
                    "coordinates": location["coords"], 
                    "success": True,
                    "rows_returned": total_rows,
                    "variables_returned": unique_vars
                })
                
            else:
                print(f"  ℹ️  No data returned")
                results[location_key] = {
                    "success": False, 
                    "data": None,
                    "rows": 0,
                    "variables": 0,
                    "location": location,
                    "reason": "no_data"
                }
                
                service_metadata["locations_tested"].append({
                    "location": location_key,
                    "coordinates": location["coords"],
                    "success": False,
                    "reason": "no_data"
                })
                
        except Exception as e:
            error_msg = str(e)
            print(f"  ❌ ERROR: {error_msg[:100]}...")
            
            results[location_key] = {
                "success": False,
                "data": None, 
                "rows": 0,
                "variables": 0,
                "location": location,
                "error": error_msg,
                "reason": "exception"
            }
            
            service_metadata["locations_tested"].append({
                "location": location_key,
                "coordinates": location["coords"],
                "success": False,
                "error": error_msg[:200]
            })
    
    # Service summary
    successful_locations = sum(1 for r in results.values() if r["success"])
    total_locations = len(results)
    total_data_rows = sum(r["rows"] for r in results.values())
    
    print(f"\n📊 {service_name} Summary:")
    print(f"   Successful locations: {successful_locations}/{total_locations}")
    print(f"   Total data rows: {total_data_rows}")
    
    service_metadata["summary"] = {
        "successful_locations": successful_locations,
        "total_locations": total_locations,  
        "total_data_rows": total_data_rows,
        "success_rate": successful_locations / total_locations if total_locations > 0 else 0
    }
    
    return results, service_metadata

# Test each active service
for service_name in active_services:
    if service_name in test_parameters:
        service_results, service_meta = test_service(
            service_name, 
            test_parameters[service_name], 
            router, 
            test_locations
        )
        
        if service_results:
            all_results[service_name] = service_results
            metadata_summary[service_name] = service_meta

# CELL 6: Comprehensive Data Display and Analysis
# -----------------------------------------------
print(f"\n📊 COMPREHENSIVE DATA DISPLAY AND ANALYSIS")
print("=" * 55)

def display_service_data(service_name, service_results, detailed=True):
    """Display comprehensive data for a service"""
    
    print(f"\n🌟 {service_name} - COMPLETE DATA ANALYSIS")
    print("=" * (len(service_name) + 30))
    
    if not service_results:
        print("❌ No results available")
        return
    
    # Aggregate statistics
    total_rows = sum(r["rows"] for r in service_results.values())
    successful_locations = sum(1 for r in service_results.values() if r["success"])
    total_locations = len(service_results)
    
    print(f"📈 AGGREGATE STATISTICS:")
    print(f"   • Successful locations: {successful_locations}/{total_locations}")
    print(f"   • Total data points: {total_rows}")
    print(f"   • Average rows per location: {total_rows/successful_locations if successful_locations > 0 else 0:.1f}")
    
    # Display data for each location
    for location_key, result in service_results.items():
        location = result["location"]
        print(f"\n📍 LOCATION: {location['name']}")
        print(f"   🌐 Coordinates: {location['coords']}")  
        print(f"   🏞️  Environment: {location['environment']}")
        
        if result["success"]:
            df = result["data"]
            print(f"   ✅ Status: SUCCESS ({result['rows']} rows, {result['variables']} variables)")
            print(f"   📊 Variables: {', '.join(result['variables_list'])}")
            print(f"   📈 Data Quality: {result['data_quality']['completeness']*100:.1f}% complete")
            
            if detailed and df is not None:
                print(f"\n   📋 SAMPLE DATA:")
                
                # Display key columns with proper formatting
                display_cols = []
                if 'variable' in df.columns: display_cols.append('variable')
                if 'value' in df.columns: display_cols.append('value') 
                if 'unit' in df.columns: display_cols.append('unit')
                if 'time' in df.columns: display_cols.append('time')
                if 'latitude' in df.columns: display_cols.append('latitude')
                if 'longitude' in df.columns: display_cols.append('longitude')
                
                # Add service-specific columns
                if service_name == "USDA_SURGO":
                    if 'depth_top_cm' in df.columns: display_cols.append('depth_top_cm')
                    if 'depth_bottom_cm' in df.columns: display_cols.append('depth_bottom_cm')
                elif service_name == "USGS_NWIS":
                    if 'site_name' in df.columns: display_cols.append('site_name')
                elif service_name == "OpenAQ":
                    if 'location_name' in df.columns: display_cols.append('location_name')
                
                if display_cols:
                    sample_data = df[display_cols].head(3)
                    for idx, row in sample_data.iterrows():
                        print(f"      Row {idx+1}:")
                        for col in display_cols:
                            value = row[col]
                            if col == 'value' and pd.notna(value):
                                print(f"        {col}: {value:.3f}")
                            elif col == 'time' and pd.notna(value):
                                print(f"        {col}: {value}")
                            else:
                                print(f"        {col}: {value}")
                
                # Statistical summary for numerical data
                if 'value' in df.columns:
                    values = df['value'].dropna()
                    if len(values) > 0:
                        print(f"\n   📊 VALUE STATISTICS:")
                        print(f"      Count: {len(values)}")
                        print(f"      Mean: {values.mean():.3f}")
                        print(f"      Std: {values.std():.3f}")
                        print(f"      Min: {values.min():.3f}")
                        print(f"      Max: {values.max():.3f}")
                        print(f"      Median: {values.median():.3f}")
                
                # Metadata analysis
                print(f"\n   🔍 METADATA SUMMARY:")
                metadata_cols = ['dataset', 'source_url', 'license', 'retrieval_timestamp']
                for col in metadata_cols:
                    if col in df.columns:
                        unique_vals = df[col].nunique()
                        if unique_vals == 1:
                            print(f"      {col}: {df[col].iloc[0]}")
                        else:
                            print(f"      {col}: {unique_vals} unique values")
                
                # Provenance information
                if 'provenance' in df.columns and not df['provenance'].isna().all():
                    prov_sample = df['provenance'].dropna().iloc[0] if len(df['provenance'].dropna()) > 0 else None
                    if prov_sample and isinstance(prov_sample, dict):
                        print(f"\n   🔗 PROVENANCE SAMPLE:")
                        for key, value in prov_sample.items():
                            if isinstance(value, dict):
                                print(f"      {key}: {len(value)} items")
                            else:
                                print(f"      {key}: {str(value)[:50]}")
        else:
            print(f"   ❌ Status: FAILED")
            if "error" in result:
                print(f"   🚨 Error: {result['error'][:100]}...")
            if "reason" in result:
                print(f"   💭 Reason: {result['reason']}")

# Display comprehensive results for each service
for service_name, service_results in all_results.items():
    display_service_data(service_name, service_results, detailed=True)

# CELL 7: Cross-Service Metadata Analysis
# ---------------------------------------
print(f"\n🔍 CROSS-SERVICE METADATA ANALYSIS")
print("=" * 45)

print(f"📋 Service Test Summary:")
for service_name, meta in metadata_summary.items():
    summary = meta["summary"]
    print(f"\n🔬 {service_name}:")
    print(f"   Success Rate: {summary['success_rate']*100:.1f}%")
    print(f"   Total Rows: {summary['total_data_rows']}")
    print(f"   Locations: {summary['successful_locations']}/{summary['total_locations']}")
    print(f"   Variables Requested: {len(meta['variables_requested'])}")

# Aggregate cross-service statistics
total_services_tested = len(metadata_summary)
total_successful_tests = sum(meta["summary"]["successful_locations"] for meta in metadata_summary.values())
total_data_points = sum(meta["summary"]["total_data_rows"] for meta in metadata_summary.values())
overall_success_rate = sum(meta["summary"]["success_rate"] for meta in metadata_summary.values()) / len(metadata_summary)

print(f"\n🌟 OVERALL PERFORMANCE:")
print(f"   • Services tested: {total_services_tested}")
print(f"   • Total successful location tests: {total_successful_tests}")
print(f"   • Total data points retrieved: {total_data_points}")
print(f"   • Average success rate: {overall_success_rate*100:.1f}%")

# CELL 8: Export Data and Generate Summary Report
# -----------------------------------------------
print(f"\n💾 DATA EXPORT AND SUMMARY REPORT")
print("=" * 45)

# Create exportable datasets
export_summary = {
    "test_metadata": {
        "timestamp": datetime.now().isoformat(),
        "services_tested": list(all_results.keys()),
        "locations_tested": list(test_locations.keys()),
        "total_data_points": total_data_points,
        "overall_success_rate": overall_success_rate
    },
    "service_results": {},
    "data_availability": {}
}

# Process data for export
for service_name, service_results in all_results.items():
    export_summary["service_results"][service_name] = {}
    
    for location_key, result in service_results.items():
        location_summary = {
            "success": result["success"],
            "rows": result["rows"], 
            "variables": result["variables"],
            "location_name": result["location"]["name"],
            "coordinates": result["location"]["coords"]
        }
        
        if result["success"] and result["data"] is not None:
            # Create simplified data export
            df = result["data"]
            location_summary["sample_data"] = df.head(3).to_dict('records') if len(df) > 0 else []
            location_summary["variables_list"] = result["variables_list"]
            location_summary["data_quality"] = result["data_quality"]
        
        export_summary["service_results"][service_name][location_key] = location_summary

# Data availability matrix
availability_matrix = {}
for service_name in all_results.keys():
    availability_matrix[service_name] = {}
    for location_key in test_locations.keys():
        if location_key in all_results[service_name]:
            availability_matrix[service_name][location_key] = all_results[service_name][location_key]["success"]
        else:
            availability_matrix[service_name][location_key] = False

export_summary["data_availability"] = availability_matrix

# Make data accessible for further analysis
print("✅ Data export completed")
print(f"📊 Available variables for analysis:")
print(f"   • all_results: Complete results with DataFrames")
print(f"   • metadata_summary: Service metadata and statistics")  
print(f"   • export_summary: Simplified export-ready data")
print(f"   • availability_matrix: Service×Location success matrix")

# Create availability summary table
print(f"\n📋 DATA AVAILABILITY MATRIX:")
print("Service" + " " * 15 + "".join([f"{loc[:8]:>10}" for loc in test_locations.keys()]))
print("-" * (20 + 10 * len(test_locations)))
for service in availability_matrix:
    row = f"{service[:15]:<15}"
    for location in test_locations.keys():
        status = "✅" if availability_matrix[service].get(location, False) else "❌"
        row += f"{status:>10}"
    print(row)

print(f"\n🎉 COMPREHENSIVE TESTING COMPLETE!")
print(f"📊 {total_data_points} total data points retrieved from {total_services_tested} services")
print(f"🌟 Ready for environmental data analysis and research!")

# CELL 9: Quick Access Data Samples
# ---------------------------------
print(f"\n🔬 QUICK ACCESS DATA SAMPLES")
print("=" * 35)

# Create quick access variables for immediate use
weather_data = []
water_data = []
soil_data = []
air_data = []

for service_name, service_results in all_results.items():
    for location_key, result in service_results.items():
        if result["success"] and result["data"] is not None:
            df = result["data"].copy()
            df['source_service'] = service_name
            df['test_location'] = location_key
            
            if service_name == "NASA_POWER":
                weather_data.append(df)
            elif service_name == "USGS_NWIS":
                water_data.append(df)  
            elif service_name in ["USDA_SURGO", "ISRIC_SoilGrids"]:
                soil_data.append(df)
            elif service_name == "OpenAQ":
                air_data.append(df)

# Combine into master datasets
if weather_data:
    combined_weather = pd.concat(weather_data, ignore_index=True)
    print(f"🌤️  weather_data: {len(combined_weather)} total weather records")
    
if water_data:
    combined_water = pd.concat(water_data, ignore_index=True) 
    print(f"💧 water_data: {len(combined_water)} total water records")
    
if soil_data:
    combined_soil = pd.concat(soil_data, ignore_index=True)
    print(f"🌱 soil_data: {len(combined_soil)} total soil records")
    
if air_data:
    combined_air = pd.concat(air_data, ignore_index=True)
    print(f"🌬️  air_data: {len(combined_air)} total air quality records")

print(f"\n📋 READY FOR ANALYSIS:")
print(f"• Use 'combined_weather', 'combined_water', 'combined_soil', 'combined_air' for domain analysis")
print(f"• Use 'all_results[service][location][\"data\"]' for specific service×location data")
print(f"• Use 'metadata_summary' for service performance analysis")
print(f"• All data includes full provenance and metadata for reproducible research")

print(f"\n✨ Environmental data retrieval and analysis system ready!")