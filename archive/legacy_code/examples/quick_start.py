#!/usr/bin/env python3
"""
env-agents Quick Start Example

A minimal example showing basic usage of the env-agents framework.
Run from the env-agents root directory.
"""

import sys
from pathlib import Path

# Add env_agents to path if needed
current_dir = Path(__file__).parent.parent.resolve()
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from env_agents.core.router import EnvRouter
from env_agents.core.models import Geometry, RequestSpec
from env_agents.adapters.power.adapter import NasaPowerDailyAdapter

def main():
    """Run basic env-agents demo"""
    print("🚀 env-agents Quick Start Demo")
    print("=" * 50)
    
    # Initialize router and register adapter
    router = EnvRouter(base_dir=".")
    router.register(NasaPowerDailyAdapter())
    
    # Create request for Berkeley, CA
    spec = RequestSpec(
        geometry=Geometry(type="point", coordinates=[-122.27, 37.87]),
        time_range=("2023-01-01", "2023-01-02"),
        variables=["atm:air_temperature_2m"]
    )
    
    print("📍 Location: Berkeley, CA")
    print("📅 Time range: 2023-01-01 to 2023-01-02")
    print("🌡️  Variable: Air temperature at 2m")
    print()
    
    # Fetch data
    try:
        df = router.fetch("NASA_POWER", spec)
        
        print("✅ Data Retrieved Successfully!")
        print(f"📊 Shape: {len(df)} rows × {len(df.columns)} columns")
        print()
        
        # Show sample data
        print("📋 Sample Data:")
        print("-" * 30)
        if not df.empty:
            print(df[['time', 'variable', 'value', 'unit']].head())
        else:
            print("No data returned")
            
        print()
        print("🔬 Semantic Metadata Available:")
        print(f"   - Schema: {bool(df.attrs.get('schema'))}")
        print(f"   - Capabilities: {bool(df.attrs.get('capabilities'))}")
        print(f"   - Variable Registry: {bool(df.attrs.get('variable_registry'))}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())