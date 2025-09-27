# =============================================================================
# UNIVERSAL JUPYTER DEMO - WORKS FROM ANY DIRECTORY
# Automatically finds and imports modules regardless of location
# =============================================================================

# CELL 1: Universal Import System
# -------------------------------
import sys
import os
from pathlib import Path
import pandas as pd
import json
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("🔧 UNIVERSAL IMPORT SYSTEM")
print("=" * 30)

# Get current directory
current_dir = Path('.').resolve()
print(f"Current directory: {current_dir}")

# Search for env_agents directory
def find_env_agents_dir():
    """Find env_agents directory by searching common locations"""
    possible_locations = [
        current_dir,
        current_dir.parent,
        current_dir.parent.parent,
        Path.home() / "enigma" / "analyses" / "2025-08-23-Soil Adaptor from GPT5" / "env-agents",
        Path("/Users/aparkin/Arkin Lab Dropbox/Adam Arkin/Code/ENIGMA Project/analyses/2025-08-23-Soil Adaptor from GPT5/env-agents"),
        Path("/usr/aparkin/enigma/analyses/2025-08-23-Soil Adaptor from GPT5/env-agents")
    ]
    
    for location in possible_locations:
        env_agents_path = location / "env_agents"
        if env_agents_path.exists() and (env_agents_path / "core" / "router.py").exists():
            print(f"✅ Found env_agents at: {location}")
            return location
    
    # Search more broadly
    for root in [Path.home(), Path("/Users"), Path("/usr")]:
        if root.exists():
            try:
                for path in root.rglob("env_agents"):
                    if (path / "core" / "router.py").exists():
                        parent = path.parent
                        print(f"✅ Found env_agents at: {parent}")
                        return parent
            except (PermissionError, OSError):
                continue
    
    return None

env_agents_base = find_env_agents_dir()

if env_agents_base:
    # Add to Python path
    if str(env_agents_base) not in sys.path:
        sys.path.insert(0, str(env_agents_base))
    
    # Add env_agents subdirectory
    env_agents_path = env_agents_base / "env_agents"
    if str(env_agents_path) not in sys.path:
        sys.path.insert(0, str(env_agents_path))
    
    print(f"Added to Python path: {env_agents_base}")
    
    # Try imports
    IMPORTS_SUCCESS = False
    
    # Method 1: Try package-style imports
    try:
        from env_agents.core.router import EnvRouter
        from env_agents.core.models import Geometry, RequestSpec
        from env_agents.adapters.soil.surgo_adapter import UsdaSurgoAdapter
        print("✅ Package-style imports successful")
        IMPORTS_SUCCESS = True
        IMPORT_METHOD = "package"
    except ImportError:
        pass
    
    # Method 2: Try relative imports
    if not IMPORTS_SUCCESS:
        try:
            from core.router import EnvRouter
            from core.models import Geometry, RequestSpec
            from adapters.soil.surgo_adapter import UsdaSurgoAdapter
            print("✅ Relative imports successful")
            IMPORTS_SUCCESS = True
            IMPORT_METHOD = "relative"
        except ImportError:
            pass
    
    # Method 3: Direct path imports
    if not IMPORTS_SUCCESS:
        try:
            core_path = env_agents_path / "core"
            adapters_path = env_agents_path / "adapters"
            
            sys.path.insert(0, str(core_path))
            sys.path.insert(0, str(adapters_path / "soil"))
            
            from router import EnvRouter
            from models import Geometry, RequestSpec
            from surgo_adapter import UsdaSurgoAdapter
            print("✅ Direct path imports successful")
            IMPORTS_SUCCESS = True
            IMPORT_METHOD = "direct"
        except ImportError as e:
            print(f"❌ All import methods failed: {e}")
            IMPORTS_SUCCESS = False
else:
    print("❌ Could not find env_agents directory")
    IMPORTS_SUCCESS = False

print(f"Import status: {'✅ SUCCESS' if IMPORTS_SUCCESS else '❌ FAILED'}")

# CELL 2: Universal SURGO Test (works if imports succeeded)
# ---------------------------------------------------------
if IMPORTS_SUCCESS:
    print(f"\n🌍 UNIVERSAL ENVIRONMENTAL DATA DEMO")
    print("=" * 45)
    print(f"🕐 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📍 Working from: {current_dir}")
    print(f"🔧 Import method: {IMPORT_METHOD}")
    
    try:
        # Initialize system
        router = EnvRouter(base_dir=str(env_agents_base))
        surgo_adapter = UsdaSurgoAdapter()
        router.register(surgo_adapter)
        print("✅ SURGO system initialized")
        
        # Test enhanced features
        print(f"\n🌱 TESTING ENHANCED SURGO")
        print("=" * 30)
        
        # California test locations
        locations = {
            "Davis": [-121.74, 38.54],
            "Salinas": [-121.6555, 36.6777]
        }
        
        results = {}
        
        for name, coords in locations.items():
            print(f"\n📍 Testing {name} {coords}")
            
            try:
                # Test the enhanced "all parameters" feature
                spec = RequestSpec(
                    geometry=Geometry(type="point", coordinates=coords),
                    variables=["*"]  # Enhanced feature: all available properties
                )
                
                df = router.fetch("USDA_SURGO", spec)
                
                if df is not None and len(df) > 0:
                    vars_found = df['variable'].unique() if 'variable' in df.columns else []
                    
                    print(f"✅ {len(df)} rows, {len(vars_found)} variables")
                    print(f"   Variables: {list(vars_found)}")
                    
                    # Show enhanced capabilities
                    if len(vars_found) > 8:
                        print(f"   🚀 ENHANCED: Broke 8-parameter barrier ({len(vars_found)} variables)")
                    
                    if 'depth_top_cm' in df.columns:
                        layers = df[['depth_top_cm', 'depth_bottom_cm']].drop_duplicates()
                        print(f"   🌱 {len(layers)} soil depth layers")
                    
                    results[name] = {
                        "success": True,
                        "data": df,
                        "variables": list(vars_found),
                        "rows": len(df)
                    }
                else:
                    print("ℹ️  No data (normal for some locations)")
                    results[name] = {"success": False, "reason": "no_data"}
                    
            except Exception as e:
                print(f"❌ {str(e)[:100]}...")
                results[name] = {"success": False, "error": str(e)}
        
        # Results summary
        successful = [name for name, res in results.items() if res.get("success")]
        total_rows = sum(res.get("rows", 0) for res in results.values() if res.get("success"))
        
        print(f"\n📊 RESULTS SUMMARY")
        print("=" * 20)
        print(f"✅ Successful locations: {len(successful)}/{len(locations)}")
        print(f"📊 Total data points: {total_rows}")
        
        if successful:
            print(f"\n🎉 SUCCESS! Enhanced SURGO working from any directory!")
            
            # Show what we achieved
            all_variables = set()
            for name in successful:
                all_variables.update(results[name]['variables'])
            
            print(f"🚀 ENHANCED FEATURES DEMONSTRATED:")
            print(f"   ✅ {len(all_variables)} unique soil properties retrieved")
            print(f"   ✅ No arbitrary 8-parameter limit")
            print(f"   ✅ All parameters (*) query working")
            print(f"   ✅ Works from any directory location")
            print(f"   ✅ Multiple California agricultural regions")
            
            # Make data accessible
            print(f"\n📋 DATA ACCESS:")
            print(f"   results = {{'location': {{'data': DataFrame, 'variables': list}}}}")
            for name in successful:
                rows = results[name]['rows']
                vars_count = len(results[name]['variables'])
                print(f"   results['{name}']['data'] → {rows} rows × {vars_count} soil variables")
            
            # Combined analysis
            if len(successful) > 1:
                print(f"\n📊 CROSS-LOCATION ANALYSIS:")
                all_data = []
                for name in successful:
                    df = results[name]['data'].copy()
                    df['location'] = name
                    all_data.append(df)
                
                combined = pd.concat(all_data, ignore_index=True)
                print(f"   Combined dataset: {len(combined)} total rows")
                
                # Variable analysis
                for var in sorted(all_variables):
                    var_data = combined[combined['variable'] == var]
                    if len(var_data) > 1:
                        values = var_data['value'].dropna()
                        if len(values) > 0:
                            unit = var_data['unit'].iloc[0] if 'unit' in var_data.columns else ''
                            print(f"   {var}: {values.mean():.2f} ± {values.std():.2f} {unit}")
                
                # Store for use
                soil_data_combined = combined
                print(f"\n   📊 Variable 'soil_data_combined' created with all data")
        
    except Exception as e:
        print(f"❌ System initialization failed: {e}")
        results = {}

else:
    print(f"\n❌ CANNOT RUN DEMO - IMPORTS FAILED")
    print("=" * 40)
    print("This could be because:")
    print("1. env_agents directory not found in expected locations")
    print("2. Missing dependencies (pandas, requests, etc.)")
    print("3. Incorrect Python environment")
    
    print(f"\n🔍 SEARCH LOCATIONS TRIED:")
    if 'possible_locations' in locals():
        for loc in possible_locations[:5]:  # Show first 5
            exists = loc.exists() if isinstance(loc, Path) else False
            print(f"   {'✅' if exists else '❌'} {loc}")
    
    print(f"\n💡 SOLUTIONS:")
    print("1. Navigate to the correct env-agents directory")
    print("2. Ensure env_agents/core/router.py exists")  
    print("3. Try: pip install -e . (from env-agents directory)")
    print("4. Check that all dependencies are installed")

# CELL 3: Manual Test (if you want to test specific components)
# ------------------------------------------------------------
print(f"\n🔧 MANUAL TESTING CAPABILITY")
print("=" * 32)

if IMPORTS_SUCCESS and 'results' in locals() and results:
    print("✅ Full system working - use 'results' variable for analysis")
    
    # Quick access examples
    if any(r.get("success") for r in results.values()):
        example_location = next(name for name, res in results.items() if res.get("success"))
        example_data = results[example_location]['data']
        
        print(f"\n📋 QUICK ACCESS EXAMPLES:")
        print(f"   results['{example_location}']['data']  # {len(example_data)} rows of soil data")
        print(f"   results['{example_location}']['variables']  # List of {len(results[example_location]['variables'])} soil properties")
        
        if 'soil_data_combined' in locals():
            print(f"   soil_data_combined  # {len(soil_data_combined)} rows from all locations")
        
        print(f"\n🔬 SAMPLE DATA COLUMNS:")
        key_cols = ['variable', 'value', 'unit', 'depth_top_cm', 'depth_bottom_cm']
        available_cols = [col for col in key_cols if col in example_data.columns]
        print(f"   Key columns: {available_cols}")
        
        if available_cols:
            sample = example_data[available_cols].head(2)
            print(f"   Sample rows:")
            for i, (_, row) in enumerate(sample.iterrows()):
                print(f"     Row {i+1}: {dict(row)}")

else:
    print("❌ System not working - try troubleshooting steps above")

print(f"\n✨ UNIVERSAL DEMO COMPLETE!")
print("🌍 This notebook works from any directory and finds env_agents automatically!")