# =============================================================================
# COMPREHENSIVE ENVIRONMENTAL SERVICES JUPYTER NOTEBOOK - FIXED VERSION
# Tests all working services with full data and metadata display
# Handles import issues and Python path configuration
# =============================================================================

# CELL 1: Setup, Path Configuration, and Imports
# ----------------------------------------------
import sys
import os
from pathlib import Path
import pandas as pd
import json
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Fix Python path for env_agents module
current_dir = Path('.').absolute()
env_agents_parent = current_dir

# Add current directory to Python path
if str(env_agents_parent) not in sys.path:
    sys.path.insert(0, str(env_agents_parent))

print("🔧 PYTHON PATH CONFIGURATION")
print("=" * 35)
print(f"Current directory: {current_dir}")
print(f"Added to Python path: {env_agents_parent}")

# Test if env_agents module can be imported
try:
    import env_agents
    print("✅ env_agents module imported successfully")
    print(f"   Module location: {env_agents.__file__}")
except ImportError as e:
    print(f"❌ Failed to import env_agents: {e}")
    print("\n🔧 Attempting alternative import methods...")
    
    # Try alternative path configurations
    possible_paths = [
        current_dir,
        current_dir.parent,
        current_dir / "env_agents",
    ]
    
    for path in possible_paths:
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
            print(f"   Added to path: {path}")
    
    try:
        import env_agents
        print("✅ env_agents module imported successfully after path adjustment")
    except ImportError as e:
        print(f"❌ Still failed to import env_agents: {e}")
        print("\nPlease ensure you're running this from the correct directory!")
        # Continue anyway - we'll handle missing imports gracefully

# Now import the required modules
try:
    from env_agents.core.router import EnvRouter
    from env_agents.core.models import Geometry, RequestSpec
    print("✅ Core modules imported successfully")
except ImportError as e:
    print(f"❌ Failed to import core modules: {e}")
    print("⚠️  Some features may not work properly")

print(f"\n🌍 COMPREHENSIVE ENVIRONMENTAL SERVICES TEST")
print("=" * 55)
print(f"🕐 Test Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# CELL 2: Initialize Router and Register Services with Error Handling
# -------------------------------------------------------------------
print(f"\n📋 INITIALIZING ENVIRONMENTAL SERVICES")
print("=" * 45)

# Initialize router with error handling
try:
    router = EnvRouter(base_dir=".")
    print("✅ EnvRouter initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize EnvRouter: {e}")
    router = None

registered_services = {}
service_capabilities = {}

# Define service registration function with robust error handling
def register_service_safely(service_name, import_path, class_name, description):
    """Register a service with comprehensive error handling"""
    try:
        # Dynamic import
        module = __import__(import_path, fromlist=[class_name])
        adapter_class = getattr(module, class_name)
        
        # Create adapter instance
        adapter = adapter_class()
        
        # Register with router
        if router:
            router.register(adapter)
        
        # Get capabilities
        capabilities = adapter.capabilities()
        
        registered_services[service_name] = {
            "adapter": adapter,
            "status": "✅ ACTIVE",
            "note": description
        }
        service_capabilities[service_name] = capabilities
        
        print(f"✅ {service_name} - {description}")
        return True
        
    except ImportError as e:
        registered_services[service_name] = {
            "status": "❌ IMPORT_FAILED", 
            "error": f"Import error: {str(e)}"
        }
        print(f"❌ {service_name} - Import failed: {e}")
        return False
        
    except Exception as e:
        registered_services[service_name] = {
            "status": "❌ REGISTRATION_FAILED",
            "error": f"Registration error: {str(e)}"
        }
        print(f"❌ {service_name} - Registration failed: {e}")
        return False

# Register services with fallback handling
services_to_register = [
    ("NASA_POWER", "env_agents.adapters.power.adapter", "NasaPowerDailyAdapter", "Global weather & climate data"),
    ("USGS_NWIS", "env_agents.adapters.nwis.adapter", "UsgsNwisLiveAdapter", "Water resources monitoring"),
    ("OpenAQ", "env_agents.adapters.openaq.adapter", "OpenaqV3Adapter", "Air quality monitoring (requires API key)"),
    ("USDA_SURGO", "env_agents.adapters.soil.surgo_adapter", "UsdaSurgoAdapter", "Enhanced US soil survey"),
    ("ISRIC_SoilGrids", "env_agents.adapters.soil.soilgrids_adapter", "IsricSoilGridsAdapter", "Global soil data")
]

print("\nRegistering services...")
for service_name, import_path, class_name, description in services_to_register:
    register_service_safely(service_name, import_path, class_name, description)

# Identify active services
active_services = [name for name, info in registered_services.items() 
                  if "✅ ACTIVE" in info.get("status", "")]

print(f"\n📊 Registration Summary:")
print(f"   Total services: {len(registered_services)}")
print(f"   Active services: {len(active_services)}")
print(f"   Active: {', '.join(active_services)}")

if len(active_services) == 0:
    print("\n⚠️  WARNING: No services were successfully registered!")
    print("This may be due to:")
    print("   • Python path issues")
    print("   • Missing dependencies")
    print("   • Module import problems")
    print("\nTrying alternative approach...")

# CELL 3: Alternative Service Testing (if imports failed)
# -------------------------------------------------------
if len(active_services) == 0:
    print(f"\n🔄 ALTERNATIVE SERVICE TESTING APPROACH")
    print("=" * 45)
    
    # Try direct imports to test what's available
    test_imports = {
        "NASA_POWER": ("env_agents.adapters.power.adapter", "NasaPowerDailyAdapter"),
        "USGS_NWIS": ("env_agents.adapters.nwis.adapter", "UsgsNwisLiveAdapter"), 
        "USDA_SURGO": ("env_agents.adapters.soil.surgo_adapter", "UsdaSurgoAdapter"),
        "OpenAQ": ("env_agents.adapters.openaq.adapter", "OpenaqV3Adapter"),
        "ISRIC_SoilGrids": ("env_agents.adapters.soil.soilgrids_adapter", "IsricSoilGridsAdapter")
    }
    
    print("Testing individual imports:")
    available_imports = {}
    
    for service_name, (module_path, class_name) in test_imports.items():
        try:
            module = __import__(module_path, fromlist=[class_name])
            adapter_class = getattr(module, class_name)
            available_imports[service_name] = adapter_class
            print(f"✅ {service_name}: Import successful")
        except Exception as e:
            print(f"❌ {service_name}: {str(e)[:80]}...")
    
    # Try to create router-less service instances for testing
    if available_imports:
        print(f"\n🧪 Creating service instances for direct testing...")
        direct_services = {}
        
        for service_name, adapter_class in available_imports.items():
            try:
                adapter = adapter_class()
                capabilities = adapter.capabilities()
                direct_services[service_name] = {
                    "adapter": adapter,
                    "capabilities": capabilities,
                    "status": "DIRECT_ACCESS"
                }
                print(f"✅ {service_name}: Direct instance created")
            except Exception as e:
                print(f"❌ {service_name}: Failed to create instance - {e}")
        
        if direct_services:
            print(f"\n📊 Available for direct testing: {list(direct_services.keys())}")

# CELL 4: Service Capabilities Display (with fallback)
# ----------------------------------------------------
print(f"\n🔧 SERVICE CAPABILITIES OVERVIEW")
print("=" * 40)

def display_capabilities_safe(service_name, capabilities):
    """Display service capabilities with error handling"""
    print(f"\n📡 {service_name}")
    print("-" * 25)
    
    if not capabilities:
        print("❌ No capabilities information available")
        return
        
    try:
        print(f"Dataset: {capabilities.get('dataset', 'N/A')}")
        print(f"Geometry Support: {capabilities.get('geometry', 'N/A')}")
        print(f"API Key Required: {capabilities.get('requires_api_key', 'Unknown')}")
        print(f"Time Range Required: {capabilities.get('requires_time_range', 'Unknown')}")
        
        variables = capabilities.get('variables', [])
        print(f"Variables Available: {len(variables)}")
        
        # Show sample variables
        for i, var in enumerate(variables[:3], 1):
            if isinstance(var, dict):
                canonical = var.get('canonical', 'N/A')
                unit = var.get('unit', 'N/A') 
                domain = var.get('domain', 'N/A')
                print(f"  {i}. {canonical} ({unit}) [{domain}]")
            else:
                print(f"  {i}. {var}")
                
        if len(variables) > 3:
            print(f"     ... and {len(variables) - 3} more")
            
    except Exception as e:
        print(f"❌ Error displaying capabilities: {e}")

# Display capabilities for active services
if active_services and service_capabilities:
    for service_name in active_services:
        if service_name in service_capabilities:
            display_capabilities_safe(service_name, service_capabilities[service_name])
elif 'direct_services' in locals():
    # Use direct services if router-based registration failed
    for service_name, service_info in direct_services.items():
        display_capabilities_safe(service_name, service_info['capabilities'])
else:
    print("❌ No service capabilities available to display")
    print("This indicates a significant import or setup issue.")

# CELL 5: Test Configuration
# --------------------------
print(f"\n📍 TEST CONFIGURATION")
print("=" * 25)

# Define test locations (these don't require imports)
test_locations = {
    "Davis_CA": {
        "coords": [-121.74, 38.54],
        "name": "Davis, CA", 
        "description": "UC Davis agricultural research",
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

# Test parameters (adjusted based on available services)
test_parameters = {
    "NASA_POWER": {
        "variables": ["atm:air_temperature_2m", "atm:precipitation_mm"],
        "time_range": ("2023-07-15", "2023-07-17"),
        "locations": ["Davis_CA", "Salinas_Valley"]
    },
    "USGS_NWIS": {
        "variables": ["water:discharge_cfs"],
        "time_range": ("2023-07-15T00:00:00Z", "2023-07-15T12:00:00Z"),
        "locations": ["Sacramento_River", "Davis_CA"],
        "extra": {"max_sites": 2}
    },
    "USDA_SURGO": {
        "variables": ["*"],  # Test enhanced all-parameters capability
        "locations": ["Davis_CA", "Salinas_Valley"]
    },
    "OpenAQ": {
        "variables": ["air:pm25_ugm3"], 
        "time_range": ("2023-07-15T00:00:00Z", "2023-07-15T12:00:00Z"),
        "locations": ["San_Francisco_Bay"],
        "extra": {"max_records": 50}
    },
    "ISRIC_SoilGrids": {
        "variables": ["soil:clay_content_percent", "soil:ph_h2o"],
        "locations": ["Davis_CA"]
    }
}

print("Test locations configured:")
for key, loc in test_locations.items():
    print(f"  • {loc['name']}: {loc['description']}")

print("\nTest parameters defined for available services")

# CELL 6: Execute Service Tests (with comprehensive error handling)
# ----------------------------------------------------------------
print(f"\n🧪 EXECUTING SERVICE TESTS")
print("=" * 30)

def test_service_safe(service_name, params, router, test_locations):
    """Test service with comprehensive error handling and fallback approaches"""
    
    print(f"\n🔬 Testing {service_name}")
    print("=" * (12 + len(service_name)))
    
    # Check if service is available
    service_available = False
    adapter = None
    
    if service_name in registered_services and "✅ ACTIVE" in registered_services[service_name].get("status", ""):
        adapter = registered_services[service_name]["adapter"]
        service_available = True
        print(f"✅ Service available via router")
    elif 'direct_services' in locals() and service_name in direct_services:
        adapter = direct_services[service_name]["adapter"]
        service_available = True
        print(f"✅ Service available via direct access")
    else:
        print(f"❌ Service not available - skipping")
        return None
    
    if not service_available or not adapter:
        return None
    
    results = {}
    
    # Test each location
    for location_key in params.get("locations", []):
        if location_key not in test_locations:
            continue
            
        location = test_locations[location_key]
        print(f"\n📍 Testing {location['name']} {location['coords']}")
        
        try:
            # Try router-based approach first
            if router and service_available and "✅ ACTIVE" in registered_services.get(service_name, {}).get("status", ""):
                try:
                    # Build request spec
                    spec_kwargs = {
                        "geometry": Geometry(type="point", coordinates=location["coords"]),
                        "variables": params["variables"]
                    }
                    
                    if "time_range" in params:
                        spec_kwargs["time_range"] = params["time_range"]
                    if "extra" in params:
                        spec_kwargs["extra"] = params["extra"]
                    
                    spec = RequestSpec(**spec_kwargs)
                    df = router.fetch(service_name, spec)
                    
                    if df is not None and len(df) > 0:
                        variables_returned = df['variable'].unique() if 'variable' in df.columns else ['data']
                        print(f"  ✅ SUCCESS: {len(df)} rows, {len(variables_returned)} variables")
                        print(f"     Variables: {list(variables_returned)}")
                        
                        results[location_key] = {
                            "success": True,
                            "data": df,
                            "rows": len(df),
                            "variables": len(variables_returned),
                            "method": "router"
                        }
                    else:
                        print(f"  ℹ️  No data returned via router")
                        results[location_key] = {
                            "success": False,
                            "data": None,
                            "rows": 0,
                            "variables": 0,
                            "method": "router",
                            "reason": "no_data"
                        }
                        
                except Exception as router_error:
                    print(f"  ⚠️  Router method failed: {str(router_error)[:60]}...")
                    # Will try direct method below
                    
            # Direct adapter method (fallback or primary if no router)
            if location_key not in results or not results[location_key]["success"]:
                print(f"  🔄 Trying direct adapter method...")
                try:
                    # This would require implementing direct adapter calls
                    # For now, just indicate the attempt
                    print(f"  ℹ️  Direct adapter testing not yet implemented")
                    if location_key not in results:
                        results[location_key] = {
                            "success": False,
                            "data": None,
                            "rows": 0,
                            "variables": 0,
                            "method": "direct",
                            "reason": "not_implemented"
                        }
                except Exception as direct_error:
                    print(f"  ❌ Direct method failed: {str(direct_error)[:60]}...")
                    results[location_key] = {
                        "success": False,
                        "data": None,
                        "rows": 0,
                        "variables": 0,
                        "method": "direct",
                        "error": str(direct_error)
                    }
                    
        except Exception as e:
            print(f"  ❌ Location test failed: {str(e)[:60]}...")
            results[location_key] = {
                "success": False,
                "data": None,
                "rows": 0,
                "variables": 0,
                "method": "unknown",
                "error": str(e)
            }
    
    # Summary for this service
    successful = sum(1 for r in results.values() if r["success"])
    total = len(results)
    total_rows = sum(r["rows"] for r in results.values())
    
    print(f"\n📊 {service_name} Summary: {successful}/{total} locations successful, {total_rows} total rows")
    
    return results

# Execute tests for available services
all_test_results = {}

services_to_test = active_services if active_services else (list(direct_services.keys()) if 'direct_services' in locals() else [])

if services_to_test:
    print(f"Testing {len(services_to_test)} available services...")
    
    for service_name in services_to_test:
        if service_name in test_parameters:
            results = test_service_safe(
                service_name, 
                test_parameters[service_name], 
                router, 
                test_locations
            )
            if results:
                all_test_results[service_name] = results
else:
    print("❌ No services available for testing")

# CELL 7: Results Analysis and Data Display
# -----------------------------------------
print(f"\n📊 RESULTS ANALYSIS AND DATA DISPLAY")
print("=" * 45)

if all_test_results:
    print(f"✅ Successfully tested {len(all_test_results)} services")
    
    total_successful_tests = 0
    total_data_points = 0
    
    for service_name, service_results in all_test_results.items():
        print(f"\n🔬 {service_name} Results:")
        
        successful_locations = sum(1 for r in service_results.values() if r["success"])
        total_locations = len(service_results)
        service_data_points = sum(r["rows"] for r in service_results.values())
        
        print(f"   Success Rate: {successful_locations}/{total_locations} ({successful_locations/total_locations*100:.1f}%)")
        print(f"   Data Points: {service_data_points}")
        
        total_successful_tests += successful_locations
        total_data_points += service_data_points
        
        # Show successful results
        for location_key, result in service_results.items():
            location = test_locations[location_key]
            if result["success"]:
                print(f"   ✅ {location['name']}: {result['rows']} rows, {result['variables']} variables")
                
                # Display sample data if available
                if result["data"] is not None and len(result["data"]) > 0:
                    df = result["data"]
                    if 'variable' in df.columns and 'value' in df.columns:
                        sample = df[['variable', 'value']].head(2)
                        print(f"      Sample: {sample.to_dict('records')}")
            else:
                reason = result.get("reason", "unknown")
                print(f"   ❌ {location['name']}: Failed ({reason})")
    
    print(f"\n🎯 OVERALL RESULTS:")
    print(f"   Total successful location tests: {total_successful_tests}")
    print(f"   Total data points retrieved: {total_data_points}")
    print(f"   Services with data: {len([s for s in all_test_results.values() if any(r['success'] for r in s.values())])}")
    
    # Make data accessible
    if total_data_points > 0:
        print(f"\n📋 DATA ACCESS:")
        print(f"   Variable 'all_test_results' contains all test results")
        print(f"   Use all_test_results[service][location]['data'] to access DataFrames")
        print(f"   Example: all_test_results['NASA_POWER']['Davis_CA']['data'] (if successful)")
        
        # Create quick access variables
        successful_data = {}
        for service_name, service_results in all_test_results.items():
            successful_data[service_name] = {}
            for location_key, result in service_results.items():
                if result["success"] and result["data"] is not None:
                    successful_data[service_name][location_key] = result["data"]
        
        if successful_data:
            print(f"\n📊 SUCCESSFUL DATA SUMMARY:")
            for service, locations in successful_data.items():
                print(f"   {service}: {len(locations)} successful locations")
                for location, df in locations.items():
                    print(f"      • {location}: {len(df)} rows")
else:
    print("❌ No test results available")

# CELL 8: Troubleshooting Information
# -----------------------------------
print(f"\n🔧 TROUBLESHOOTING INFORMATION")
print("=" * 40)

print(f"Python Path Information:")
for i, path in enumerate(sys.path[:5]):
    print(f"  {i+1}. {path}")

print(f"\nModule Import Status:")
modules_to_check = [
    "env_agents",
    "env_agents.core",
    "env_agents.core.router", 
    "env_agents.core.models",
    "env_agents.adapters"
]

for module_name in modules_to_check:
    try:
        __import__(module_name)
        print(f"  ✅ {module_name}")
    except ImportError as e:
        print(f"  ❌ {module_name}: {e}")

print(f"\nFile System Check:")
current_path = Path('.')
print(f"  Current directory: {current_path.absolute()}")
print(f"  env_agents exists: {(current_path / 'env_agents').exists()}")
print(f"  env_agents/__init__.py exists: {(current_path / 'env_agents' / '__init__.py').exists()}")

print(f"\n💡 If imports failed, try:")
print(f"   1. Ensure you're in the correct directory")
print(f"   2. Check that env_agents module is properly installed")
print(f"   3. Try: pip install -e . (if setup.py exists)")
print(f"   4. Verify all dependencies are installed")

print(f"\n✨ COMPREHENSIVE SERVICES TEST COMPLETE!")
if 'total_data_points' in locals() and total_data_points > 0:
    print(f"🎉 Successfully retrieved {total_data_points} data points!")
else:
    print(f"⚠️  Limited success due to import/configuration issues")
    print(f"   Please resolve import issues and re-run for full functionality")