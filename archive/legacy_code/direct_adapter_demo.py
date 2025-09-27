#!/usr/bin/env python3
"""
Direct Adapter Demo - Testing Real Environmental Services
Demonstrates that individual adapters work correctly with real APIs
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path('.').resolve()
sys.path.insert(0, str(project_root))

from env_agents import RequestSpec, Geometry
import pandas as pd

def test_nasa_power():
    """Test NASA POWER weather service directly"""
    print("🌡️ Testing NASA POWER Weather Service")
    print("-" * 40)
    
    try:
        from env_agents.adapters.power.adapter import NasaPowerDailyAdapter
        
        # Initialize adapter
        power = NasaPowerDailyAdapter()
        print("✅ NASA POWER adapter loaded")
        
        # Berkeley, CA test location
        berkeley = Geometry(type='point', coordinates=[-122.2725, 37.8719])
        
        # Create request for temperature
        spec = RequestSpec(
            geometry=berkeley,
            variables=['T2M'],  # Temperature 2m above surface
            time_range=('2024-06-01', '2024-06-02')
        )
        
        # Fetch real weather data
        result = power.fetch(spec)
        
        print("✅ Real weather data fetched successfully!")
        print(f"   Location: Berkeley, CA {berkeley.coordinates}")
        print(f"   Rows: {len(result)}")
        print(f"   Temperature values: {result['value'].tolist()} °C")
        print(f"   Date range: {result['time'].min()} to {result['time'].max()}")
        print(f"   Canonical variable: {result['variable'].iloc[0]}")
        
        return True
        
    except Exception as e:
        print(f"❌ NASA POWER test failed: {e}")
        return False

def test_soilgrids():
    """Test SoilGrids soil service directly"""
    print("\n🌱 Testing SoilGrids Soil Service")
    print("-" * 40)
    
    try:
        from env_agents.adapters.soil.soilgrids_adapter import IsricSoilGridsAdapter
        
        # Initialize adapter
        soil = IsricSoilGridsAdapter()
        print("✅ SoilGrids adapter loaded")
        
        # Berkeley, CA test location
        berkeley = Geometry(type='point', coordinates=[-122.2725, 37.8719])
        
        # Create request for sand content
        spec = RequestSpec(
            geometry=berkeley,
            variables=['sand'],
            time_range=('2024-06-01', '2024-06-02')  # Not used for soil data
        )
        
        # Fetch real soil data
        result = soil.fetch(spec)
        
        print("✅ Real soil data fetched successfully!")
        print(f"   Location: Berkeley, CA {berkeley.coordinates}")
        print(f"   Rows: {len(result)}")
        print(f"   Sand content: {result['value'].tolist()} %")
        print(f"   Canonical variable: {result['variable'].iloc[0]}")
        print(f"   Depth: {result.get('depth_top_cm', [0]).iloc[0]}-{result.get('depth_bottom_cm', [5]).iloc[0]} cm")
        
        return True
        
    except Exception as e:
        print(f"❌ SoilGrids test failed: {e}")
        return False

def main():
    print("🌍 Direct Environmental Adapters Demo")
    print("=" * 50)
    print("Testing real environmental data services individually")
    
    # Test each service
    nasa_success = test_nasa_power()
    soil_success = test_soilgrids()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 REAL SERVICES VALIDATION SUMMARY")
    print(f"   NASA POWER Weather: {'✅ WORKING' if nasa_success else '❌ FAILED'}")
    print(f"   SoilGrids Soil:     {'✅ WORKING' if soil_success else '❌ FAILED'}")
    
    if nasa_success and soil_success:
        print("\n🎉 SUCCESS: Framework processes real environmental APIs!")
        print("   ✅ Core data fetching pipeline functional")
        print("   ✅ Real-world API integration validated")
        print("   ✅ Data standardization working")
        print("   ✅ Semantic variable mapping operational")
    else:
        print("\n⚠️  Some services failed - check configurations")
    
    return nasa_success and soil_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)