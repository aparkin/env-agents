#!/usr/bin/env python3
"""
Simple data visibility test showing successful data retrieval and semantic integration
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from env_agents.core.router import EnvRouter
from env_agents.core.models import Geometry, RequestSpec
import pandas as pd

def simple_visibility_test():
    print("🔍 Simple Data Visibility Test")
    print("=" * 50)
    
    # Setup router
    router = EnvRouter(base_dir=".")
    
    # Register NASA POWER (most reliable)
    from env_agents.adapters.power.adapter import NasaPowerDailyAdapter
    power_adapter = NasaPowerDailyAdapter()
    router.register(power_adapter)
    print("✅ NASA POWER registered")
    
    # Test data retrieval
    spec = RequestSpec(
        geometry=Geometry(type="point", coordinates=[-122.27, 37.87]),  # Berkeley, CA
        time_range=("2023-01-01", "2023-01-02"),
        variables=["atm:air_temperature_2m"]
    )
    
    print(f"\n🌤️  Fetching weather data for Berkeley, CA...")
    df = router.fetch("NASA_POWER", spec)
    
    # Basic info
    print(f"📊 Retrieved: {len(df)} rows × {len(df.columns)} columns")
    
    # Show column names and types
    print(f"\n📋 Core Columns:")
    core_cols = ["dataset", "latitude", "longitude", "time", "variable", "value", "unit"]
    for col in core_cols:
        if col in df.columns:
            sample_val = df[col].iloc[0] if not df.empty else "N/A"
            print(f"  {col}: {sample_val}")
    
    # Semantic columns
    print(f"\n🔬 Semantic Integration:")
    semantic_cols = ["observed_property_uri", "unit_uri", "preferred_unit"] 
    for col in semantic_cols:
        if col in df.columns:
            unique_vals = df[col].dropna().unique()
            print(f"  {col}: {len(unique_vals)} unique values")
            if len(unique_vals) > 0:
                print(f"    Sample: {unique_vals[0]}")
        else:
            print(f"  {col}: Not present")
    
    # Show actual data
    print(f"\n📈 Sample Data:")
    if not df.empty:
        # Safe column selection
        display_cols = []
        for col in ["time", "variable", "value", "unit", "latitude", "longitude"]:
            if col in df.columns:
                display_cols.append(col)
        
        if display_cols:
            print(df[display_cols].head(3).to_string(index=False))
    
    # Metadata inspection
    print(f"\n📚 DataFrame Metadata:")
    if hasattr(df, 'attrs') and df.attrs:
        print(f"  Schema: {df.attrs.get('schema', {}).keys()}")
        capabilities = df.attrs.get('capabilities', {})
        if capabilities:
            print(f"  Service capabilities: {len(capabilities.get('variables', []))} variables available")
        registry = df.attrs.get('variable_registry', {})
        if registry:
            print(f"  Registry variables: {len(registry.get('variables', {}))}")
    
    # Provenance sample (safer inspection)
    if "provenance" in df.columns and not df.empty:
        print(f"\n🔍 Provenance Sample:")
        prov = df["provenance"].iloc[0]
        if isinstance(prov, dict):
            for key in ["request_geometry", "request_variables", "execution_time"]:
                if key in prov:
                    print(f"  {key}: {prov[key]}")
        else:
            print(f"  Type: {type(prov)}")
    
    print(f"\n✅ Test completed successfully!")
    return df

if __name__ == "__main__":
    df = simple_visibility_test()
    print(f"\n📋 Full column list ({len(df.columns)}):")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i:2d}. {col}")