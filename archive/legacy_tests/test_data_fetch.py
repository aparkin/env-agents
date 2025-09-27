#!/usr/bin/env python3
"""
Simple data fetch test to validate core functionality
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from env_agents.core.router import EnvRouter
from env_agents.core.models import Geometry, RequestSpec

# Test location: Berkeley, CA
BERKELEY = [-122.27, 37.87]

def test_data_fetch():
    print("🧪 Testing Data Fetch")
    print("=" * 30)
    
    # Setup router
    router = EnvRouter(base_dir=".")
    
    # Import and register services
    from env_agents.adapters.nwis.adapter import UsgsNwisLiveAdapter
    from env_agents.adapters.power.adapter import NasaPowerDailyAdapter
    
    router.register(UsgsNwisLiveAdapter())
    router.register(NasaPowerDailyAdapter())
    
    # Test NASA POWER (should work)
    print("\n🔍 Testing NASA POWER...")
    try:
        power_spec = RequestSpec(
            geometry=Geometry(type="point", coordinates=BERKELEY),
            time_range=("2023-01-01", "2023-01-02"),
            variables=["atm:air_temperature_2m"]
        )
        
        df = router.fetch("NASA_POWER", power_spec)
        print(f"✅ NASA POWER: {len(df)} rows, {len(df.columns)} columns")
        
        # Check semantic columns
        semantic_cols = ["observed_property_uri", "unit_uri", "preferred_unit"]
        has_semantic = [col for col in semantic_cols if col in df.columns]
        print(f"   Semantic columns: {has_semantic}")
        
    except Exception as e:
        print(f"❌ NASA POWER failed: {e}")
    
    # Test NWIS (might need different parameters)
    print("\n🔍 Testing USGS NWIS...")
    try:
        nwis_spec = RequestSpec(
            geometry=Geometry(type="point", coordinates=[-121.5, 38.6]),  # Sacramento area
            time_range=("2023-01-01T00:00:00Z", "2023-01-01T06:00:00Z"),
            variables=["water:discharge_cfs"],
            extra={"max_sites": 1}
        )
        
        df = router.fetch("USGS_NWIS", nwis_spec)
        print(f"✅ USGS NWIS: {len(df)} rows, {len(df.columns)} columns")
        
        # Check semantic columns  
        semantic_cols = ["observed_property_uri", "unit_uri", "preferred_unit"]
        has_semantic = [col for col in semantic_cols if col in df.columns]
        print(f"   Semantic columns: {has_semantic}")
        
    except Exception as e:
        print(f"❌ USGS NWIS failed: {e}")

if __name__ == "__main__":
    test_data_fetch()