#!/usr/bin/env python3
"""
env-agents Quick Start Example - Simplified Interface

Demonstrates the new 3-method SimpleEnvRouter interface:
1. register() - Add environmental services  
2. discover() - Find services and capabilities
3. fetch() - Get environmental data

Perfect for agents and interactive analysis!
"""

import sys
from pathlib import Path

# Add env_agents to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from env_agents.core import SimpleEnvRouter
from env_agents.adapters import NASA_POWER, WQP
from env_agents.core.models import RequestSpec, Geometry

def main():
    """Demonstrate simplified environmental data access"""
    print("🚀 env-agents Framework - Simplified Interface")
    print("=" * 50)
    
    # Initialize router
    router = SimpleEnvRouter(base_dir=".")
    print("✅ Router initialized")
    
    # === 1. REGISTER - Add environmental services ===
    print("\n1️⃣ REGISTER - Adding environmental services...")
    
    router.register(NASA_POWER())
    router.register(WQP()) 
    
    print("✅ Registered environmental services")
    
    # === 2. DISCOVER - Find services and capabilities ===
    print("\n2️⃣ DISCOVER - Exploring available services...")
    
    # List all services
    services = router.discover()
    print(f"📋 Available services: {services}")
    
    # Search for temperature data
    temp_services = router.discover(query="temperature")
    print(f"\n🌡️ Temperature services found: {len(temp_services.get('services', []))}")
    
    for service_id in temp_services.get('services', []):
        result = temp_services['service_results'][service_id]
        print(f"   • {service_id}: {result['filtered_items']} temperature variables")
        
        # Show usage example
        if result.get('usage_examples'):
            print(f"     Usage: {result['usage_examples'][0]}")
    
    # Get detailed capabilities  
    print(f"\n📊 System capabilities:")
    capabilities = router.discover(format="detailed")
    print(f"   • Total variables: {capabilities.get('total_items_across_services', 0)}")
    print(f"   • Domains: {capabilities.get('available_domains', [])}")
    print(f"   • Providers: {capabilities.get('available_providers', [])}")
    
    # Service-specific discovery
    print(f"\n🔍 NASA POWER climate variables:")
    nasa_climate = router.discover(service="NASA_POWER", domain="climate", limit=5)
    nasa_result = nasa_climate['service_results']['NASA_POWER']
    print(f"   Found {nasa_result['filtered_items']} climate variables")
    
    for item in nasa_result['items'][:3]:
        print(f"   • {item['name']} ({item['unit']})")
    
    # === 3. FETCH - Get environmental data ===
    print(f"\n3️⃣ FETCH - Retrieving environmental data...")
    
    # Create data request for San Francisco
    spec = RequestSpec(
        geometry=Geometry(type='point', coordinates=[-122.4194, 37.7749]),
        time_range=('2024-08-01', '2024-08-03'),
        variables=['T2M', 'PRECTOTCORR']  # Temperature, precipitation
    )
    
    print(f"📍 Location: San Francisco Bay Area")
    print(f"📅 Time range: {spec.time_range[0]} to {spec.time_range[1]}")
    print(f"🌡️ Variables: {', '.join(spec.variables)}")
    
    try:
        print(f"\n🔍 Fetching from NASA POWER...")
        df = router.fetch('NASA_POWER', spec)
        
        print(f"✅ Success: {len(df)} observations retrieved")
        
        if not df.empty:
            # Show sample data
            sample = df.iloc[0].to_dict()
            print(f"\n📊 Sample observation:")
            print(f"   Variable: {sample.get('variable', 'N/A')}")
            print(f"   Value: {sample.get('value', 'N/A')} {sample.get('unit', 'N/A')}")
            print(f"   Location: {sample.get('latitude', 0):.4f}, {sample.get('longitude', 0):.4f}")
            print(f"   Time: {sample.get('time', 'N/A')}")
            print(f"   Dataset: {sample.get('dataset', 'N/A')}")
            
            # Show DataFrame structure
            print(f"\n🏗️ DataFrame structure:")
            print(f"   Shape: {df.shape}")
            print(f"   Columns: {list(df.columns)[:8]}...")
            
            # Show metadata
            if hasattr(df, 'attrs') and df.attrs:
                service_info = df.attrs.get('service_info', {})
                print(f"\n📋 Service metadata:")
                print(f"   Provider: {service_info.get('provider', 'Unknown')}")
                print(f"   License: {service_info.get('license', 'Unknown')}")
        
        # === BONUS: Convenience Methods ===
        print(f"\n🔧 Convenience methods:")
        
        # Alternative ways to do the same thing
        services_alt = router.list_services()
        print(f"   list_services(): {len(services_alt)} services")
        
        search_alt = router.search("precipitation", limit=3)
        print(f"   search('precipitation'): {len(search_alt.get('services', []))} services")
        
        print(f"\n🎉 Success! The simplified 3-method interface makes environmental data access easy:")
        print(f"   1. register() - Add services")
        print(f"   2. discover() - Find capabilities") 
        print(f"   3. fetch() - Get data")
        print(f"\n   Perfect for interactive analysis and AI agents! 🤖")
        
        return 0
        
    except Exception as e:
        print(f"❌ Fetch failed: {e}")
        print(f"   (This might be due to API limits or network issues)")
        print(f"\n✅ Interface demonstration completed successfully!")
        return 0

if __name__ == "__main__":
    exit(main())