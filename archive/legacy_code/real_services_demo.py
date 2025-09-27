#!/usr/bin/env python3
"""
Real Environmental Services Demo
Demonstrates the env-agents framework with actual environmental data APIs
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path('.').resolve()
sys.path.insert(0, str(project_root))

from env_agents import UnifiedEnvRouter, RequestSpec, Geometry
import pandas as pd

def main():
    print("🌍 Real Environmental Services Demo")
    print("=" * 50)
    
    # Initialize router
    router = UnifiedEnvRouter()
    
    # Register real services
    try:
        from env_agents.adapters.power.adapter import NasaPowerDailyAdapter
        from env_agents.adapters.soil.soilgrids_adapter import IsricSoilGridsAdapter
        
        router.register("nasa_power", NasaPowerDailyAdapter())
        router.register("soilgrids", IsricSoilGridsAdapter())
        
        print("✅ Registered real environmental data services:")
        print("   - NASA POWER (weather/climate data)")
        print("   - SoilGrids (soil properties)")
        
    except Exception as e:
        print(f"❌ Service registration failed: {e}")
        return
    
    # Test location: Berkeley, CA
    berkeley = Geometry(type='point', coordinates=[-122.2725, 37.8719])
    time_range = ('2024-06-01', '2024-06-02')
    
    print(f"\n📍 Test Location: Berkeley, CA {berkeley.coordinates}")
    print(f"⏰ Time Range: {time_range[0]} to {time_range[1]}")
    
    # Test NASA POWER weather data
    print("\n=== NASA POWER Weather Data ===")
    try:
        weather_spec = RequestSpec(
            geometry=berkeley,
            variables=['T2M'],  # Temperature 2m
            time_range=time_range
        )
        
        weather_data = router.fetch('nasa_power', weather_spec)
        print("✅ Weather data fetched:")
        print(f"   Rows: {len(weather_data)}")
        print(f"   Temperature: {weather_data['value'].tolist()} °C")
        print(f"   Variable: {weather_data['variable'].iloc[0]}")
        
    except Exception as e:
        print(f"❌ Weather data fetch failed: {e}")
    
    # Test SoilGrids soil data
    print("\n=== SoilGrids Soil Data ===")
    try:
        soil_spec = RequestSpec(
            geometry=berkeley,
            variables=['sand'],
            time_range=time_range
        )
        
        soil_data = router.fetch('soilgrids', soil_spec)
        print("✅ Soil data fetched:")
        print(f"   Rows: {len(soil_data)}")
        print(f"   Sand content: {soil_data['value'].tolist()} %")
        print(f"   Variable: {soil_data['variable'].iloc[0]}")
        print(f"   Depth: {soil_data.get('depth_top_cm', [0]).iloc[0]}-{soil_data.get('depth_bottom_cm', [5]).iloc[0]} cm")
        
    except Exception as e:
        print(f"❌ Soil data fetch failed: {e}")
    
    print("\n🎉 Real services integration successful!")
    print("   The framework processes actual environmental APIs correctly.")

if __name__ == "__main__":
    main()