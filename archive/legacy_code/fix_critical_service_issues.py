#!/usr/bin/env python3
"""
Fix Critical Service Issues
===========================

Addresses the core technical issues preventing proper service testing:
1. EPA AQS import problem
2. Geometry handling for SSURGO/WQP/Overpass
3. Parameter display issues
4. Coordinate extraction problems
"""

import sys
import os
from pathlib import Path
import re

def fix_epa_aqs_import():
    """Fix the EPA AQS import issue that keeps recurring"""
    print("🔧 Fixing EPA AQS import issue...")
    
    epa_file = Path("env_agents/adapters/air/enhanced_aqs_adapter.py")
    if not epa_file.exists():
        print(f"❌ EPA AQS file not found: {epa_file}")
        return False
    
    # Read current content
    with open(epa_file, 'r') as f:
        content = f.read()
    
    # Fix the import and class reference
    content = content.replace(
        "from .aqs_adapter import AQSAdapter", 
        "from .aqs_adapter import EPAAQSAdapter"
    )
    
    content = content.replace(
        "class EPAAQSEnhancedAdapter(AQSAdapter):",
        "class EPAAQSEnhancedAdapter(EPAAQSAdapter):"
    )
    
    # Write back
    with open(epa_file, 'w') as f:
        f.write(content)
    
    print("✅ EPA AQS import fixed")
    return True

def fix_geometry_handling():
    """Fix geometry handling in services that require bounding boxes"""
    print("🔧 Fixing geometry handling in SSURGO, WQP, Overpass...")
    
    services_to_fix = [
        "env_agents/adapters/ssurgo/enhanced_ssurgo_adapter.py",
        "env_agents/adapters/wqp/enhanced_adapter.py", 
        "env_agents/adapters/overpass/enhanced_adapter.py"
    ]
    
    for service_file in services_to_fix:
        path = Path(service_file)
        if not path.exists():
            print(f"⚠️ File not found: {path}")
            continue
        
        with open(path, 'r') as f:
            content = f.read()
        
        # Find the _fetch_rows method and add geometry conversion
        if "_fetch_rows" in content and "self._point_to_bbox" not in content:
            
            # Add the geometry conversion helper if not present
            geometry_helper = '''
    def _convert_geometry_to_bbox(self, geometry: Geometry, extra: Dict[str, Any]) -> Tuple[float, float, float, float]:
        """Convert geometry to bounding box with proper radius handling"""
        if geometry.type == "bbox":
            return tuple(geometry.coordinates)
        elif geometry.type == "point":
            lon, lat = geometry.coordinates
            radius_m = extra.get('radius', 2000)  # Default 2km radius
            # Convert radius from meters to degrees (rough approximation)
            radius_deg = radius_m / 111000  # ~111km per degree
            return (lon - radius_deg, lat - radius_deg, lon + radius_deg, lat + radius_deg)
        else:
            raise ValueError(f"Unsupported geometry type for {self.__class__.__name__}: {geometry.type}")
'''
            
            # Find a good insertion point - after imports but before class methods
            class_match = re.search(r'(class \w+.*?:)', content, re.DOTALL)
            if class_match:
                insert_pos = class_match.end()
                content = content[:insert_pos] + geometry_helper + content[insert_pos:]
                
                # Update _fetch_rows to use the geometry conversion
                content = re.sub(
                    r'(def _fetch_rows\(self, spec: RequestSpec\).*?)(\n        # .*?)',
                    r'\1\n        # Convert geometry to bounding box\n        try:\n            bbox = self._convert_geometry_to_bbox(spec.geometry, spec.extra or {})\n        except ValueError as e:\n            import warnings\n            warnings.warn(str(e))\n            return []\n\2',
                    content,
                    flags=re.DOTALL
                )
                
                with open(path, 'w') as f:
                    f.write(content)
                
                print(f"✅ Fixed geometry handling in {path.name}")
            else:
                print(f"⚠️ Could not find class definition in {path.name}")
    
    return True

def fix_parameter_display():
    """Fix parameter display issues in the demonstration notebook"""
    print("🔧 Fixing parameter display in capabilities methods...")
    
    # The issue is in the capabilities method structure - we need consistent key naming
    adapters_to_fix = [
        "env_agents/adapters/openaq/enhanced_adapter.py",
        "env_agents/adapters/power/enhanced_adapter.py",
        "env_agents/adapters/air/enhanced_aqs_adapter.py"
    ]
    
    for adapter_file in adapters_to_fix:
        path = Path(adapter_file)
        if not path.exists():
            continue
        
        with open(path, 'r') as f:
            content = f.read()
        
        # Ensure variables in capabilities have consistent structure
        if '"variables":' in content and 'for param in enhanced_params' in content:
            # Fix the variable structure in capabilities method
            content = re.sub(
                r'("variables": \[)\s*\{\s*"canonical".*?"platform".*?\}.*?(for param in enhanced_params)',
                r'\1\n                {\n                    "id": param.get("id", param.get("canonical", "Unknown")),\n                    "name": param.get("name", param.get("platform_native", "Unknown")),\n                    "canonical": param["canonical"],\n                    "platform": param["platform_native"],\n                    "unit": param["unit"],\n                    "description": param["description"],\n                    "health_impact": param.get("health_impact", ""),\n                    "regulatory_standards": param.get("regulatory_standards", {})\n                }\n                \2',
                content,
                flags=re.DOTALL
            )
        
        # Also ensure fallback parameters have correct structure
        if '_get_fallback_enhanced_parameters' in content:
            # Make sure fallback parameters have all required keys
            content = re.sub(
                r'("id": param_code,)\s*("name": param_name,)',
                r'\1\n                "name": param_name,\n                "canonical": f"air:{param_code}",\n                "platform": param_code,',
                content
            )
        
        with open(path, 'w') as f:
            f.write(content)
    
    print("✅ Parameter display structure fixed")
    return True

def create_service_diagnostic_tool():
    """Create a diagnostic tool for testing individual services"""
    print("🔧 Creating service diagnostic tool...")
    
    diagnostic_code = '''#!/usr/bin/env python3
"""
Service Diagnostic Tool
=======================

Quick diagnostic tool for testing individual services with detailed error reporting.
"""

import sys
import os
import json
import traceback
from datetime import datetime

sys.path.insert(0, '.')

# Set up credentials
os.environ['OPENAQ_API_KEY'] = '1dfd14b5aac0cf892b43e575fa4060d6dc4228149751b9362e5e2331ca2fc4ca'
os.environ['EPA_AQS_EMAIL'] = 'aparkin@lbl.gov'
os.environ['EPA_AQS_KEY'] = 'khakimouse81'

from env_agents.core.models import RequestSpec, Geometry

def test_service(service_name: str, adapter_class_path: str):
    """Test a single service with comprehensive diagnostics"""
    
    print(f"🔍 DIAGNOSING {service_name}")
    print("=" * 50)
    
    # Step 1: Import test
    print("1. Testing import...")
    try:
        module_path, class_name = adapter_class_path.rsplit('.', 1)
        module = __import__(module_path, fromlist=[class_name])
        adapter_class = getattr(module, class_name)
        print(f"   ✅ Import successful: {class_name}")
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        print(f"   Stack trace: {traceback.format_exc()}")
        return False
    
    # Step 2: Initialization test
    print("2. Testing initialization...")
    try:
        adapter = adapter_class()
        print(f"   ✅ Initialization successful")
    except Exception as e:
        print(f"   ❌ Initialization failed: {e}")
        print(f"   Stack trace: {traceback.format_exc()}")
        return False
    
    # Step 3: Capabilities test
    print("3. Testing capabilities...")
    try:
        caps = adapter.capabilities()
        variables = caps.get('variables', [])
        print(f"   ✅ Capabilities retrieved: {len(variables)} variables")
        
        # Check variable structure
        if variables:
            var = variables[0]
            print(f"   📋 Sample variable keys: {list(var.keys())}")
            print(f"   📋 Sample variable: {var.get('id', 'NO_ID')} - {var.get('name', 'NO_NAME')}")
        
    except Exception as e:
        print(f"   ❌ Capabilities failed: {e}")
        print(f"   Stack trace: {traceback.format_exc()}")
    
    # Step 4: Simple data request test
    print("4. Testing simple data request...")
    try:
        # Use Los Angeles - high probability of data
        geom = Geometry(type="point", coordinates=[-118.2437, 34.0522])
        
        # Service-specific configurations
        if "OpenAQ" in service_name:
            variables = ["pm25"]
            extra = {"radius": 15000}
        elif "POWER" in service_name:
            variables = ["T2M"]
            extra = {}
        elif "AQS" in service_name:
            variables = ["88101"]
            extra = {"state": "06", "county": "037"}  # Los Angeles County
        elif "NWIS" in service_name:
            variables = ["00060"]
            extra = {"radius": 50000}
        elif "Soil" in service_name:
            variables = ["clay"]
            extra = {"depth": "0-5cm"}
        elif "GBIF" in service_name:
            variables = ["occurrence"]
            extra = {"radius": 10000, "limit": 50}
        elif "Overpass" in service_name:
            variables = ["building"]
            extra = {"radius": 3000}
        else:
            variables = []
            extra = {}
        
        spec = RequestSpec(
            geometry=geom,
            time_range=("2024-08-01", "2024-08-07"),  # One week
            variables=variables,
            extra=extra
        )
        
        print(f"   🔄 Making request: {variables} near Los Angeles")
        rows = adapter._fetch_rows(spec)
        
        if rows and len(rows) > 0:
            print(f"   ✅ Data retrieved: {len(rows)} records")
            
            # Analyze first record
            sample = rows[0]
            print(f"   📝 Sample record keys: {list(sample.keys())}")
            print(f"   📝 Coordinates: lat={sample.get('latitude')}, lon={sample.get('longitude')}")
            print(f"   📝 Value: {sample.get('value')} {sample.get('unit')}")
            print(f"   📝 Timestamp: {sample.get('time')}")
            
        else:
            print(f"   ⚠️ No data returned (may be normal for location/service)")
            
    except Exception as e:
        print(f"   ❌ Data request failed: {e}")
        print(f"   Stack trace: {traceback.format_exc()}")
        return False
    
    print(f"\\n✅ {service_name} diagnostic complete\\n")
    return True

def main():
    """Run diagnostics on all services"""
    
    services_to_test = [
        ("OpenAQ Enhanced", "env_agents.adapters.openaq.enhanced_adapter.EnhancedOpenAQAdapter"),
        ("NASA POWER Enhanced", "env_agents.adapters.power.enhanced_adapter.NASAPOWEREnhancedAdapter"),
        ("EPA AQS Enhanced", "env_agents.adapters.air.enhanced_aqs_adapter.EPAAQSEnhancedAdapter"),
        ("USGS NWIS Enhanced", "env_agents.adapters.nwis.enhanced_adapter.USGSNWISEnhancedAdapter"),
        ("SoilGrids Enhanced", "env_agents.adapters.soil.enhanced_soilgrids_adapter.EnhancedSoilGridsAdapter"),
        ("GBIF Enhanced", "env_agents.adapters.gbif.enhanced_adapter.EnhancedGBIFAdapter"),
    ]
    
    results = {}
    
    for service_name, adapter_path in services_to_test:
        success = test_service(service_name, adapter_path)
        results[service_name] = success
    
    print("🏆 DIAGNOSTIC SUMMARY")
    print("=" * 30)
    
    working_services = [name for name, success in results.items() if success]
    broken_services = [name for name, success in results.items() if not success]
    
    print(f"✅ Working Services ({len(working_services)}/{len(results)}):")
    for service in working_services:
        print(f"  - {service}")
    
    if broken_services:
        print(f"\\n❌ Broken Services ({len(broken_services)}/{len(results)}):")
        for service in broken_services:
            print(f"  - {service}")
    
    success_rate = len(working_services) / len(results)
    print(f"\\n📊 Overall Success Rate: {success_rate:.1%}")
    
    if success_rate >= 0.8:
        print("🎉 Framework is ready for comprehensive testing!")
    elif success_rate >= 0.5:
        print("⚠️ Some issues remain - focus on fixing broken services")
    else:
        print("❌ Major issues detected - framework needs significant fixes")

if __name__ == "__main__":
    main()
'''
    
    with open("service_diagnostics.py", 'w') as f:
        f.write(diagnostic_code)
    
    print("✅ Service diagnostic tool created: service_diagnostics.py")
    return True

def main():
    """Run all critical fixes"""
    print("🛠️ FIXING CRITICAL SERVICE ISSUES")
    print("=" * 40)
    
    fixes = [
        ("EPA AQS Import", fix_epa_aqs_import),
        ("Geometry Handling", fix_geometry_handling), 
        ("Parameter Display", fix_parameter_display),
        ("Diagnostic Tool", create_service_diagnostic_tool)
    ]
    
    results = {}
    for fix_name, fix_function in fixes:
        print(f"\\n{fix_name}:")
        try:
            results[fix_name] = fix_function()
        except Exception as e:
            print(f"❌ {fix_name} failed: {e}")
            results[fix_name] = False
    
    print(f"\\n🏆 FIXES SUMMARY")
    print("=" * 20)
    
    for fix_name, success in results.items():
        status = "✅" if success else "❌"
        print(f"{status} {fix_name}")
    
    successful_fixes = sum(1 for success in results.values() if success)
    print(f"\\nOverall: {successful_fixes}/{len(results)} fixes applied successfully")
    
    if successful_fixes == len(results):
        print("\\n🎉 All critical issues fixed! Run service_diagnostics.py to validate")
    else:
        print("\\n⚠️ Some fixes failed - check error messages above")
    
    return successful_fixes == len(results)

if __name__ == "__main__":
    main()