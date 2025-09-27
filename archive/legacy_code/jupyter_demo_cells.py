# =============================================================================
# JUPYTER NOTEBOOK CELLS - Environmental Data Services Demo
# Copy each cell block below into separate Jupyter notebook cells
# =============================================================================

# CELL 1: Setup and Imports
# -------------------------
import sys
from pathlib import Path
import pandas as pd
import json
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Add the env_agents path (adjust if needed)
sys.path.insert(0, str(Path('.').absolute()))

from env_agents.core.router import EnvRouter
from env_agents.core.models import Geometry, RequestSpec

# Salinas, California coordinates (agricultural heart of California)
SALINAS_CA = [-121.6555, 36.6777]
print("🥬 Environmental Data Services - Salinas, California Demo")


# CELL 2: Service Registration
# ----------------------------
# Initialize router and register all services
router = EnvRouter(base_dir=".")
services = {}

print("📋 Registering Environmental Data Services...")

# NASA POWER - Weather/Climate Data
try:
    from env_agents.adapters.power.adapter import NasaPowerDailyAdapter
    power_adapter = NasaPowerDailyAdapter()
    router.register(power_adapter)
    services["NASA_POWER"] = power_adapter
    print("  ✅ NASA POWER - Daily weather & climate data")
except Exception as e:
    print(f"  ❌ NASA POWER failed: {e}")

# USGS NWIS - Water Resources
try:
    from env_agents.adapters.nwis.adapter import UsgsNwisLiveAdapter
    nwis_adapter = UsgsNwisLiveAdapter()
    router.register(nwis_adapter)
    services["USGS_NWIS"] = nwis_adapter
    print("  ✅ USGS NWIS - Water resources monitoring")
except Exception as e:
    print(f"  ❌ USGS NWIS failed: {e}")

# USDA SURGO - US Soil Survey
try:
    from env_agents.adapters.soil.surgo_adapter import UsdaSurgoAdapter
    surgo_adapter = UsdaSurgoAdapter()
    router.register(surgo_adapter)
    services["USDA_SURGO"] = surgo_adapter
    print("  ✅ USDA SURGO - US soil survey data")
except Exception as e:
    print(f"  ❌ USDA SURGO failed: {e}")

# ISRIC SoilGrids - Global Soil Data
try:
    from env_agents.adapters.soil.soilgrids_adapter import IsricSoilGridsAdapter
    soilgrids_adapter = IsricSoilGridsAdapter()
    router.register(soilgrids_adapter)
    services["ISRIC_SoilGrids"] = soilgrids_adapter
    print("  ✅ ISRIC SoilGrids - Global soil properties")
except Exception as e:
    print(f"  ❌ ISRIC SoilGrids failed: {e}")

# OpenAQ - Air Quality (optional - requires API key)
try:
    from env_agents.adapters.openaq.adapter import OpenaqV3Adapter
    openaq_adapter = OpenaqV3Adapter()
    router.register(openaq_adapter)
    services["OpenAQ"] = openaq_adapter
    print("  ✅ OpenAQ - Air quality monitoring (requires API key)")
except Exception as e:
    print(f"  ❌ OpenAQ failed: {e}")

print(f"\n📊 Total Services Registered: {len(services)}")


# CELL 3: Explore Service Capabilities
# ------------------------------------
def show_service_capabilities(service_name, adapter):
    """Display service capabilities clearly"""
    print(f"\n🔍 {service_name} Capabilities")
    print("=" * 50)
    
    try:
        caps = adapter.capabilities()
        
        # Basic service info
        print(f"Dataset: {caps.get('dataset')}")
        print(f"Supported Geometry: {caps.get('geometry', [])}")
        print(f"Requires API Key: {caps.get('requires_api_key', False)}")
        print(f"Requires Time Range: {caps.get('requires_time_range', False)}")
        
        # Show available variables
        variables = caps.get('variables', [])
        print(f"\n📊 Available Variables ({len(variables)}):")
        
        for i, var in enumerate(variables[:8], 1):  # Show first 8
            canonical = var.get('canonical', 'N/A')
            unit = var.get('unit', 'N/A')
            description = var.get('description', '')[:60]
            print(f"  {i}. {canonical}")
            print(f"     Unit: {unit} | {description}")
        
        if len(variables) > 8:
            print(f"     ... and {len(variables) - 8} more variables")
            
        # Additional info
        notes = caps.get('notes', '')
        if notes:
            print(f"\n📝 Service Notes: {notes[:100]}...")
            
    except Exception as e:
        print(f"❌ Error: {e}")

# Show capabilities for each service
for name, adapter in services.items():
    show_service_capabilities(name, adapter)


# CELL 4: Fetch Weather Data (NASA POWER)
# ---------------------------------------
print("🌤️ Fetching Weather Data for Salinas Valley")
print("=" * 50)

weather_spec = RequestSpec(
    geometry=Geometry(type="point", coordinates=SALINAS_CA),
    time_range=("2023-07-15", "2023-07-20"),  # Mid-July harvest season
    variables=["atm:air_temperature_2m", "atm:precip_total"]
)

try:
    weather_df = router.fetch("NASA_POWER", weather_spec)
    print(f"📊 Retrieved: {len(weather_df)} rows × {len(weather_df.columns)} columns")
    
    # Show sample data
    if not weather_df.empty:
        print("\n📈 Weather Data Sample:")
        display_cols = ["time", "variable", "value", "unit"]
        print(weather_df[display_cols].head())
        
        # Show temperature trend
        temp_data = weather_df[weather_df["variable"] == "atm:air_temperature_2m"]
        if not temp_data.empty:
            avg_temp = temp_data["value"].mean()
            print(f"\n🌡️ Average Temperature: {avg_temp:.1f}°C ({avg_temp*9/5+32:.1f}°F)")
    
    print("\n🔬 Semantic Columns:")
    semantic_cols = ["observed_property_uri", "unit_uri", "preferred_unit"]
    for col in semantic_cols:
        if col in weather_df.columns:
            values = weather_df[col].dropna().unique()
            print(f"  {col}: {len(values)} unique values")
            
except Exception as e:
    print(f"❌ Weather data error: {e}")
    weather_df = None


# CELL 5: Fetch Soil Data (USDA SURGO)
# ------------------------------------
print("\n🌱 Fetching Soil Data for Salinas Valley Agricultural Land")
print("=" * 55)

soil_spec = RequestSpec(
    geometry=Geometry(type="point", coordinates=SALINAS_CA),
    variables=["soil:clay_percent", "soil:sand_percent", "soil:organic_matter", "soil:ph"]
)

try:
    soil_df = router.fetch("USDA_SURGO", soil_spec)
    print(f"📊 Retrieved: {len(soil_df)} rows × {len(soil_df.columns)} columns")
    
    if not soil_df.empty:
        print("\n🌾 Soil Properties:")
        for _, row in soil_df.head(3).iterrows():
            variable = row.get("variable", "Unknown")
            value = row.get("value", "N/A")
            unit = row.get("unit", "")
            depth_top = row.get("depth_top_cm", "N/A")
            depth_bottom = row.get("depth_bottom_cm", "N/A")
            print(f"  {variable}: {value} {unit} (depth: {depth_top}-{depth_bottom}cm)")
            
    # Show unique soil variables found
    if "variable" in soil_df.columns:
        variables = soil_df["variable"].unique()
        print(f"\n📊 Soil Variables Found: {list(variables)}")
        
except Exception as e:
    print(f"❌ Soil data error: {e}")
    soil_df = None


# CELL 6: Fetch Water Data (USGS NWIS)
# ------------------------------------
print("\n💧 Fetching Water Monitoring Data near Salinas River")
print("=" * 50)

water_spec = RequestSpec(
    geometry=Geometry(type="point", coordinates=SALINAS_CA),
    time_range=("2023-07-15T00:00:00Z", "2023-07-15T12:00:00Z"),
    variables=["water:discharge_cfs", "water:temperature"],
    extra={"max_sites": 2}
)

try:
    water_df = router.fetch("USGS_NWIS", water_spec)
    print(f"📊 Retrieved: {len(water_df)} rows × {len(water_df.columns)} columns")
    
    if not water_df.empty:
        print("\n🌊 Water Monitoring Sample:")
        display_cols = ["time", "site_name", "variable", "value", "unit"]
        available_cols = [col for col in display_cols if col in water_df.columns]
        print(water_df[available_cols].head())
        
        # Show monitoring sites
        if "site_name" in water_df.columns:
            sites = water_df["site_name"].dropna().unique()
            print(f"\n📍 Monitoring Sites: {list(sites)}")
    else:
        print("ℹ️  No water monitoring stations found near Salinas")
        print("    (This is common - USGS stations are sparse in some areas)")
        
except Exception as e:
    print(f"❌ Water data error: {e}")
    water_df = None


# CELL 7: Detailed Provenance Analysis
# ------------------------------------
def analyze_provenance(df, service_name):
    """Analyze and display data provenance clearly"""
    print(f"\n📚 {service_name} - Data Provenance & Metadata")
    print("=" * 55)
    
    if df is None or df.empty:
        print("❌ No data available for provenance analysis")
        return
    
    first_row = df.iloc[0]
    
    # Data lineage
    print("🏷️ Data Lineage:")
    print(f"  Dataset: {first_row.get('dataset', 'N/A')}")
    print(f"  Source URL: {first_row.get('source_url', 'N/A')}")
    print(f"  Version: {first_row.get('source_version', 'N/A')}")
    print(f"  License: {first_row.get('license', 'N/A')}")
    print(f"  Retrieved: {first_row.get('retrieval_timestamp', 'N/A')}")
    
    # Spatial context
    print(f"\n🌍 Spatial Context:")
    print(f"  Location: {first_row.get('latitude', 'N/A')}, {first_row.get('longitude', 'N/A')}")
    print(f"  Geometry: {first_row.get('geometry_type', 'N/A')}")
    if pd.notna(first_row.get('site_name')):
        print(f"  Site: {first_row.get('site_name')}")
    
    # Temporal context
    print(f"\n⏰ Temporal Context:")
    print(f"  Time: {first_row.get('time', 'N/A')}")
    print(f"  Coverage: {first_row.get('temporal_coverage', 'N/A')}")
    
    # Quality information
    print(f"\n✅ Data Quality:")
    qc_flags = df["qc_flag"].value_counts() if "qc_flag" in df.columns else {}
    print(f"  QC Flags: {dict(qc_flags)}")
    
    # Service-specific attributes
    if "attributes" in df.columns and pd.notna(first_row.get("attributes")):
        print(f"\n🏷️ Service Attributes:")
        attrs = first_row["attributes"]
        if isinstance(attrs, dict):
            for key, value in list(attrs.items())[:5]:  # Show first 5
                print(f"  {key}: {value}")

# Analyze provenance for each successful data retrieval
for name, df in [("Weather", weather_df), ("Soil", soil_df), ("Water", water_df)]:
    if df is not None:
        analyze_provenance(df, name)


# CELL 8: Data Summary and Export
# -------------------------------
print("\n📊 FINAL SUMMARY - Salinas Valley Environmental Data")
print("=" * 60)

# Collect all successful dataframes
all_data = {
    "Weather (NASA POWER)": weather_df,
    "Soil (USDA SURGO)": soil_df, 
    "Water (USGS NWIS)": water_df
}

successful = 0
total_rows = 0

for data_type, df in all_data.items():
    if df is not None and not df.empty:
        successful += 1
        total_rows += len(df)
        variables = df["variable"].nunique() if "variable" in df.columns else 0
        print(f"  ✅ {data_type}: {len(df)} rows, {variables} variables")
        
        # Show variable summary
        if "variable" in df.columns:
            vars_list = df["variable"].unique()
            print(f"      Variables: {list(vars_list)}")
    else:
        print(f"  ❌ {data_type}: No data retrieved")

print(f"\n🎯 Overall Results:")
print(f"  Services Queried: {len(all_data)}")
print(f"  Successful Retrievals: {successful}")
print(f"  Total Data Points: {total_rows}")
print(f"  Location: Salinas, CA ({SALINAS_CA[1]:.3f}, {SALINAS_CA[0]:.3f})")

# Make data easily accessible for further analysis
print(f"\n💡 Data Available for Analysis:")
print(f"  weather_df - NASA POWER weather data")
print(f"  soil_df    - USDA SURGO soil properties") 
print(f"  water_df   - USGS NWIS water monitoring")

# Optional: Save to files
save_data = input("\n💾 Save data to CSV files? (y/n): ").lower().startswith('y')
if save_data:
    if weather_df is not None:
        weather_df.to_csv("salinas_weather_data.csv", index=False)
        print("  ✅ Saved: salinas_weather_data.csv")
    if soil_df is not None:
        soil_df.to_csv("salinas_soil_data.csv", index=False)
        print("  ✅ Saved: salinas_soil_data.csv")
    if water_df is not None:
        water_df.to_csv("salinas_water_data.csv", index=False)
        print("  ✅ Saved: salinas_water_data.csv")

print("\n🌱 Analysis complete! Ready for agricultural and environmental research.")


# BONUS CELL 9: Quick Data Visualization (optional)
# -------------------------------------------------
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    
    print("\n📈 Quick Data Visualizations")
    print("=" * 35)
    
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    
    # Weather data plot
    if weather_df is not None:
        temp_data = weather_df[weather_df["variable"] == "atm:air_temperature_2m"]
        if not temp_data.empty:
            temp_data = temp_data.copy()
            temp_data["date"] = pd.to_datetime(temp_data["time"])
            axes[0].plot(temp_data["date"], temp_data["value"], 'o-')
            axes[0].set_title("Temperature in Salinas Valley")
            axes[0].set_ylabel("Temperature (°C)")
            axes[0].tick_params(axis='x', rotation=45)
    
    # Soil data plot
    if soil_df is not None:
        soil_summary = soil_df.groupby("variable")["value"].mean()
        if not soil_summary.empty:
            soil_summary.plot(kind='bar', ax=axes[1])
            axes[1].set_title("Average Soil Properties")
            axes[1].set_ylabel("Percentage/Value")
            axes[1].tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plt.show()
    
except ImportError:
    print("📊 Install matplotlib and seaborn for visualizations:")
    print("   pip install matplotlib seaborn")