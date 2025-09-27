#!/usr/bin/env python3
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
    
    print(f"\n✅ {service_name} diagnostic complete\n")
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
        print(f"\n❌ Broken Services ({len(broken_services)}/{len(results)}):")
        for service in broken_services:
            print(f"  - {service}")
    
    success_rate = len(working_services) / len(results)
    print(f"\n📊 Overall Success Rate: {success_rate:.1%}")
    
    if success_rate >= 0.8:
        print("🎉 Framework is ready for comprehensive testing!")
    elif success_rate >= 0.5:
        print("⚠️ Some issues remain - focus on fixing broken services")
    else:
        print("❌ Major issues detected - framework needs significant fixes")

if __name__ == "__main__":
    main()
