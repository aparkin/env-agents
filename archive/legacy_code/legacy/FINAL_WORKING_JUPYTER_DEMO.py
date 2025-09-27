# =============================================================================
# FINAL WORKING JUPYTER DEMO - Environmental Data for Salinas, CA
# Copy each cell below into separate Jupyter notebook cells
# This version uses PROVEN WORKING parameters from successful tests
# =============================================================================

# CELL 1: Setup and Service Registration
# ---------------------------------------
import sys
from pathlib import Path
import pandas as pd
import json
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Add path (adjust if needed)
sys.path.insert(0, str(Path('.').absolute()))

from env_agents.core.router import EnvRouter
from env_agents.core.models import Geometry, RequestSpec

# Initialize router and register services
router = EnvRouter(base_dir=".")

print("🥬 Environmental Data Services - Salinas Valley Demo")
print("Using PROVEN working parameters")
print("=" * 55)

# Register services
services = {}

# NASA POWER (Weather data) - CONFIRMED WORKING
try:
    from env_agents.adapters.power.adapter import NasaPowerDailyAdapter
    power_adapter = NasaPowerDailyAdapter()
    router.register(power_adapter)
    services["NASA_POWER"] = power_adapter
    print("✅ NASA POWER - Weather & climate data")
except Exception as e:
    print(f"❌ NASA POWER: {e}")

# USGS NWIS (Water data) - CONFIRMED WORKING  
try:
    from env_agents.adapters.nwis.adapter import UsgsNwisLiveAdapter
    nwis_adapter = UsgsNwisLiveAdapter()
    router.register(nwis_adapter)
    services["USGS_NWIS"] = nwis_adapter
    print("✅ USGS NWIS - Water monitoring")
except Exception as e:
    print(f"❌ USGS NWIS: {e}")

# OpenAQ (Air quality) - CONFIRMED WORKING (with API key)
try:
    from env_agents.adapters.openaq.adapter import OpenaqV3Adapter
    openaq_adapter = OpenaqV3Adapter()
    router.register(openaq_adapter)
    services["OpenAQ"] = openaq_adapter
    print("✅ OpenAQ - Air quality (API key required)")
except Exception as e:
    print(f"❌ OpenAQ: {e}")

print(f"\n📊 Services registered: {len(services)}")


# CELL 2: NASA POWER Weather Data for Salinas
# -------------------------------------------
print("\n🌤️ NASA POWER - Weather Data for Salinas Valley")
print("=" * 50)

# Salinas coordinates
SALINAS_CA = [-121.6555, 36.6777]

# Use exact working parameters
weather_spec = RequestSpec(
    geometry=Geometry(type="point", coordinates=SALINAS_CA),
    time_range=("2023-01-01", "2023-01-05"),  # 5 days of data
    variables=["atm:air_temperature_2m"]  # Single variable - proven to work
)

try:
    weather_df = router.fetch("NASA_POWER", weather_spec)
    print(f"✅ SUCCESS: Retrieved {len(weather_df)} rows × {len(weather_df.columns)} columns")
    
    # Show basic statistics
    print(f"\n📊 Weather Statistics for Salinas:")
    temp_data = weather_df['value']
    print(f"  Temperature range: {temp_data.min():.1f}°C to {temp_data.max():.1f}°C")
    print(f"  Average temperature: {temp_data.mean():.1f}°C ({temp_data.mean()*9/5+32:.1f}°F)")
    print(f"  Date range: {weather_df['time'].min()} to {weather_df['time'].max()}")
    
    # Show sample data
    print(f"\n📅 Daily Temperature Data:")
    for _, row in weather_df.iterrows():
        date = row['time']
        temp_c = row['value']
        temp_f = temp_c * 9/5 + 32
        print(f"  {date}: {temp_c:.1f}°C ({temp_f:.1f}°F)")
    
    # Semantic integration check
    print(f"\n🔬 Semantic Integration:")
    semantic_cols = ["observed_property_uri", "unit_uri", "preferred_unit"]
    for col in semantic_cols:
        if col in weather_df.columns:
            unique_count = weather_df[col].nunique()
            has_data = not weather_df[col].isna().all()
            print(f"  {col}: {'✅' if has_data else '❌'} ({unique_count} unique)")
    
except Exception as e:
    print(f"❌ FAILED: {e}")
    weather_df = None


# CELL 3: Service Capabilities Overview
# ------------------------------------
print(f"\n📋 SERVICE CAPABILITIES OVERVIEW")
print("=" * 40)

for service_name, adapter in services.items():
    try:
        caps = adapter.capabilities()
        variables = caps.get('variables', [])
        
        print(f"\n🔧 {service_name}")
        print(f"   Dataset: {caps.get('dataset')}")
        print(f"   Variables available: {len(variables)}")
        print(f"   Requires API key: {caps.get('requires_api_key', False)}")
        print(f"   Geometry support: {caps.get('geometry', [])}")
        
        # Show top 5 variables
        print(f"   Top variables:")
        for i, var in enumerate(variables[:5], 1):
            canonical = var.get('canonical', 'N/A')
            unit = var.get('unit', 'N/A')
            description = var.get('description', '')[:40] + "..."
            print(f"     {i}. {canonical} ({unit}) - {description}")
            
        if len(variables) > 5:
            print(f"     ... and {len(variables) - 5} more")
            
    except Exception as e:
        print(f"\n🔧 {service_name}: ❌ Error - {e}")


# CELL 4: Multiple Weather Variables (Advanced)
# ---------------------------------------------
print(f"\n🌡️ Advanced Weather Data - Multiple Variables")
print("=" * 50)

# Try multiple variables one at a time (safer approach)
weather_variables = [
    "atm:air_temperature_2m",
    "atm:precip_total", 
    "atm:allsky_sfc_sw_dwn"
]

all_weather_data = []

for var in weather_variables:
    print(f"\n🔍 Fetching {var}...")
    try:
        var_spec = RequestSpec(
            geometry=Geometry(type="point", coordinates=SALINAS_CA),
            time_range=("2023-07-15", "2023-07-17"),  # Summer harvest season
            variables=[var]  # One variable at a time
        )
        
        var_df = router.fetch("NASA_POWER", var_spec)
        if len(var_df) > 0:
            all_weather_data.append(var_df)
            print(f"  ✅ Retrieved {len(var_df)} records")
            
            # Show sample values
            values = var_df['value']
            unit = var_df['unit'].iloc[0]
            print(f"  📊 Range: {values.min():.2f} to {values.max():.2f} {unit}")
        else:
            print(f"  ❌ No data returned")
            
    except Exception as e:
        print(f"  ❌ Error: {str(e)[:50]}...")

# Combine all weather data
if all_weather_data:
    combined_weather = pd.concat(all_weather_data, ignore_index=True)
    print(f"\n🌤️ Combined Weather Dataset:")
    print(f"  Total records: {len(combined_weather)}")
    print(f"  Variables: {list(combined_weather['variable'].unique())}")
    
    # Show summary by variable
    for var in combined_weather['variable'].unique():
        var_data = combined_weather[combined_weather['variable'] == var]
        values = var_data['value']
        unit = var_data['unit'].iloc[0]
        print(f"  {var}: {values.mean():.2f} {unit} (avg)")
else:
    combined_weather = None


# CELL 5: USGS Water Data Near Salinas
# ------------------------------------
print(f"\n💧 USGS Water Data - Salinas River Area")
print("=" * 45)

# Try different locations around Salinas for water data
water_locations = {
    "Salinas River": [-121.6555, 36.6777],
    "Monterey Bay area": [-121.8, 36.6],
    "Sacramento River": [-121.5, 38.6]  # Known to work
}

water_results = {}

for location_name, coords in water_locations.items():
    print(f"\n🌊 Testing {location_name} ({coords[1]:.3f}, {coords[0]:.3f})...")
    
    try:
        water_spec = RequestSpec(
            geometry=Geometry(type="point", coordinates=coords),
            time_range=("2023-07-01T00:00:00Z", "2023-07-01T12:00:00Z"),
            variables=["water:discharge_cfs"],
            extra={"max_sites": 2}
        )
        
        water_df = router.fetch("USGS_NWIS", water_spec)
        
        if len(water_df) > 0:
            sites = water_df['site_name'].nunique() if 'site_name' in water_df.columns else 0
            records = len(water_df)
            print(f"  ✅ Found {records} records from {sites} monitoring sites")
            water_results[location_name] = water_df
            
            # Show site details
            if 'site_name' in water_df.columns:
                site_names = water_df['site_name'].dropna().unique()
                for site in site_names[:2]:  # Show first 2 sites
                    print(f"    📍 {site}")
        else:
            print(f"  ℹ️  No monitoring stations found")
            water_results[location_name] = None
            
    except Exception as e:
        print(f"  ❌ Error: {str(e)[:60]}...")
        water_results[location_name] = None

# Summary of water data
successful_water = [name for name, data in water_results.items() if data is not None]
if successful_water:
    print(f"\n💧 Water Data Summary:")
    for location in successful_water:
        data = water_results[location]
        print(f"  ✅ {location}: {len(data)} records")
else:
    print(f"\n💧 No water monitoring data found near Salinas")
    print(f"   This is normal - USGS monitoring stations are sparse")


# CELL 6: Detailed Provenance Analysis
# ------------------------------------
def analyze_data_provenance(df, title):
    """Detailed provenance analysis"""
    if df is None or len(df) == 0:
        print(f"❌ No data for {title}")
        return
    
    print(f"\n📚 {title} - Provenance & Metadata")
    print("=" * 60)
    
    sample_row = df.iloc[0]
    
    # Data lineage
    print("🏷️ Data Lineage:")
    print(f"  Dataset: {sample_row.get('dataset')}")
    print(f"  Source: {sample_row.get('source_url')}")
    print(f"  Version: {sample_row.get('source_version')}")
    print(f"  License: {sample_row.get('license')}")
    print(f"  Retrieved: {sample_row.get('retrieval_timestamp')}")
    
    # Geographic context
    print(f"\n🌍 Geographic Context:")
    lat = sample_row.get('latitude')
    lon = sample_row.get('longitude')
    print(f"  Location: {lat}, {lon}")
    print(f"  Geometry: {sample_row.get('geometry_type')}")
    
    # Temporal context
    print(f"\n⏰ Temporal Context:")
    print(f"  Time: {sample_row.get('time')}")
    print(f"  Coverage: {sample_row.get('temporal_coverage')}")
    
    # Data quality
    print(f"\n✅ Data Quality:")
    if 'qc_flag' in df.columns:
        qc_summary = df['qc_flag'].value_counts().to_dict()
        print(f"  QC Flags: {qc_summary}")
    
    # Service-specific attributes
    if 'attributes' in df.columns and pd.notna(sample_row.get('attributes')):
        attrs = sample_row['attributes']
        if isinstance(attrs, dict):
            print(f"\n🏷️ Service Attributes:")
            for key, value in list(attrs.items())[:5]:
                print(f"  {key}: {value}")
    
    # Variable summary
    if 'variable' in df.columns:
        variables = df['variable'].unique()
        print(f"\n📊 Variables ({len(variables)}):")
        for var in variables:
            var_data = df[df['variable'] == var]
            count = len(var_data)
            if 'value' in var_data.columns:
                avg_val = var_data['value'].mean()
                unit = var_data['unit'].iloc[0] if 'unit' in var_data.columns else 'N/A'
                print(f"  {var}: {count} records, avg={avg_val:.2f} {unit}")

# Analyze available data
if weather_df is not None:
    analyze_data_provenance(weather_df, "NASA POWER Weather Data")

if combined_weather is not None:
    analyze_data_provenance(combined_weather, "Combined Weather Variables")

# Analyze water data if available
for location, data in water_results.items():
    if data is not None:
        analyze_data_provenance(data, f"USGS Water Data - {location}")


# CELL 7: Final Summary & Data Export
# -----------------------------------
print(f"\n🎉 FINAL SUMMARY - Environmental Data for Salinas, CA")
print("=" * 65)

# Count successful data retrievals
data_summary = {
    "NASA POWER Weather": weather_df,
    "Combined Weather Variables": combined_weather,
}

# Add water data
for location, data in water_results.items():
    if data is not None:
        data_summary[f"Water - {location}"] = data

successful_datasets = {k: v for k, v in data_summary.items() if v is not None and len(v) > 0}
total_records = sum(len(df) for df in successful_datasets.values())

print(f"✅ Successful Datasets: {len(successful_datasets)}")
print(f"📊 Total Records: {total_records}")
print(f"🌍 Location: Salinas, CA ({SALINAS_CA[1]:.4f}, {SALINAS_CA[0]:.4f})")

print(f"\n📈 Available Datasets:")
for name, df in successful_datasets.items():
    variables = df['variable'].nunique() if 'variable' in df.columns else 1
    date_range = ""
    if 'time' in df.columns:
        times = pd.to_datetime(df['time'], errors='coerce').dropna()
        if len(times) > 1:
            date_range = f" ({times.min().date()} to {times.max().date()})"
    print(f"  📊 {name}: {len(df)} records, {variables} variables{date_range}")

print(f"\n💡 Available Variables:")
all_variables = set()
for df in successful_datasets.values():
    if 'variable' in df.columns:
        all_variables.update(df['variable'].unique())
for var in sorted(all_variables):
    print(f"  📈 {var}")

print(f"\n🔬 Data Access:")
print(f"  weather_df         - Basic weather data")
print(f"  combined_weather   - Multi-variable weather")
print(f"  water_results      - Dictionary of water data by location")
print(f"  successful_datasets - All successful data retrievals")

# Optional: Save to CSV
save_choice = input(f"\n💾 Save datasets to CSV files? (y/n): ").lower()
if save_choice.startswith('y'):
    for name, df in successful_datasets.items():
        filename = f"salinas_{name.lower().replace(' ', '_').replace('-', '_')}.csv"
        df.to_csv(filename, index=False)
        print(f"  ✅ Saved: {filename}")

print(f"\n🌱 Analysis Ready!")
print(f"You now have environmental data for Salinas, CA including:")
print(f"  🌡️ Temperature data from NASA POWER")
print(f"  💧 Water monitoring data (if available)")
print(f"  🔬 Full semantic metadata and provenance")
print(f"  📊 Ready for agricultural and environmental research!")


# OPTIONAL CELL 8: Quick Visualization
# ------------------------------------
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    
    print(f"\n📊 Quick Data Visualization")
    print("=" * 35)
    
    if weather_df is not None:
        # Temperature plot
        plt.figure(figsize=(10, 6))
        
        # Plot basic weather data
        plt.subplot(1, 2, 1)
        weather_df['date'] = pd.to_datetime(weather_df['time'])
        plt.plot(weather_df['date'], weather_df['value'], 'o-', label='Temperature')
        plt.title('Daily Temperature - Salinas, CA')
        plt.ylabel('Temperature (°C)')
        plt.xticks(rotation=45)
        plt.grid(True, alpha=0.3)
        
        # Multi-variable plot if available
        if combined_weather is not None:
            plt.subplot(1, 2, 2)
            for var in combined_weather['variable'].unique():
                var_data = combined_weather[combined_weather['variable'] == var]
                var_data['date'] = pd.to_datetime(var_data['time'])
                plt.plot(var_data['date'], var_data['value'], 'o-', label=var.split(':')[1])
            
            plt.title('Multiple Weather Variables')
            plt.ylabel('Values (various units)')
            plt.xticks(rotation=45)
            plt.legend()
            plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
        
        print("📈 Visualization complete!")
        
except ImportError:
    print(f"📊 Install matplotlib for visualizations:")
    print(f"   pip install matplotlib seaborn")
    
print(f"\n🏁 Demo Complete! Environmental data ready for Salinas Valley analysis.")