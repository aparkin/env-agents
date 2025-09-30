# Quick Start Guide

**Get environmental data in 5 minutes**

---

## Your First Query

Let's fetch weather data for San Francisco using NASA POWER (no API key required):

```python
from env_agents.core.models import RequestSpec, Geometry
from env_agents.adapters.nasa_power import NASAPowerAdapter

# Step 1: Create an adapter
adapter = NASAPowerAdapter()

# Step 2: Define what you want
spec = RequestSpec(
    geometry=Geometry(
        type="point",
        coordinates=[-122.4, 37.8]  # San Francisco [longitude, latitude]
    ),
    time_range=("2021-06-01", "2021-06-30")  # June 2021
)

# Step 3: Fetch the data
data = adapter.fetch(spec)

# Step 4: Explore the results
print(f"Retrieved {len(data)} observations")
print(data[['time', 'variable', 'value', 'unit']].head(10))
```

**Output:**
```
Retrieved 180 observations
         time            variable  value   unit
0  2021-06-01  nasa:T2M           18.5   degC
1  2021-06-01  nasa:PRECTOTCORR    0.2   mm/day
2  2021-06-01  nasa:RH2M          75.3   %
...
```

---

## Understanding the Data

Every observation returns **20 standardized columns**:

### Core Identity
- `observation_id` - Unique identifier
- `dataset` - Source service (e.g., "NASA_POWER")
- `source_url` - Data source URL
- `retrieval_timestamp` - When data was fetched

### Location
- `latitude`, `longitude` - Point location
- `geometry_type` - "point", "bbox", or "polygon"
- `geom_wkt` - WKT geometry string

### Time
- `time` - ISO timestamp (YYYY-MM-DD or full datetime)

### Measurement
- `variable` - Parameter name (e.g., "nasa:T2M" for temperature)
- `value` - Numeric measurement
- `unit` - Units (e.g., "degC", "mm/day")

### Quality & Metadata
- `qc_flag` - Quality control status
- `attributes` - Service-specific metadata (dict)

---

## Try Different Services

### GBIF - Species Observations

```python
from env_agents.adapters.gbif import GBIFAdapter

adapter = GBIFAdapter()
spec = RequestSpec(
    geometry=Geometry(type="bbox", coordinates=[-122.5, 37.7, -122.3, 37.9]),
    time_range=("2020-01-01", "2023-12-31")
)

species_data = adapter.fetch(spec)
print(f"Found {len(species_data)} species observations")
print(species_data['attributes'].apply(lambda x: x.get('species')).value_counts().head())
```

### USGS NWIS - Stream Gauge Data

```python
from env_agents.adapters.usgs_nwis import USGSNWISAdapter

adapter = USGSNWISAdapter()
spec = RequestSpec(
    geometry=Geometry(type="point", coordinates=[-122.4, 37.8]),
    time_range=("2021-01-01", "2021-12-31")
)

stream_data = adapter.fetch(spec)
print(f"Retrieved {len(stream_data)} stream measurements")
```

### Earth Engine - Satellite Imagery

**Note:** Requires Earth Engine authentication (see [Credentials Guide](CREDENTIALS.md))

```python
from env_agents.adapters.earth_engine.production_adapter import ProductionEarthEngineAdapter

# MODIS NDVI (vegetation index)
adapter = ProductionEarthEngineAdapter(
    asset_id="MODIS/061/MOD13Q1",
    scale=250
)

spec = RequestSpec(
    geometry=Geometry(type="point", coordinates=[-122.4, 37.8]),
    time_range=("2021-01-01", "2021-12-31")
)

ndvi_data = adapter.fetch(spec)
print(f"Retrieved {len(ndvi_data)} satellite observations")
```

---

## Common Patterns

### 1. Checking Service Capabilities

```python
# What variables does NASA POWER provide?
adapter = NASAPowerAdapter()
capabilities = adapter.capabilities()

print(f"Available variables: {len(capabilities['variables'])}")
for var in capabilities['variables'][:5]:
    print(f"  - {var['name']}: {var['description']}")
```

### 2. Handling Multiple Locations

```python
import pandas as pd

locations = [
    {"name": "San Francisco", "coords": [-122.4, 37.8]},
    {"name": "Los Angeles", "coords": [-118.2, 34.1]},
    {"name": "Seattle", "coords": [-122.3, 47.6]}
]

all_data = []
for loc in locations:
    spec = RequestSpec(
        geometry=Geometry(type="point", coordinates=loc["coords"]),
        time_range=("2021-06-01", "2021-06-30")
    )
    data = adapter.fetch(spec)
    data['location_name'] = loc['name']
    all_data.append(data)

combined = pd.concat(all_data, ignore_index=True)
print(f"Total observations: {len(combined)}")
```

### 3. Filtering by Variable

```python
# Get only temperature data
data = adapter.fetch(spec)
temp_data = data[data['variable'].str.contains('T2M')]
print(temp_data[['time', 'value', 'unit']])
```

### 4. Time Series Analysis

```python
import pandas as pd
import matplotlib.pyplot as plt

data = adapter.fetch(spec)
temp_data = data[data['variable'] == 'nasa:T2M'].copy()
temp_data['time'] = pd.to_datetime(temp_data['time'])

plt.plot(temp_data['time'], temp_data['value'])
plt.ylabel('Temperature (°C)')
plt.title('San Francisco Temperature - June 2021')
plt.show()
```

---

## Geometry Types

### Point (Single Location)

```python
Geometry(type="point", coordinates=[-122.4, 37.8])
```

### Bounding Box (Rectangular Area)

```python
Geometry(type="bbox", coordinates=[-122.5, 37.7, -122.3, 37.9])
# [west, south, east, north]
```

### Polygon (Custom Shape)

```python
Geometry(type="polygon", coordinates=[
    [-122.5, 37.7],
    [-122.3, 37.7],
    [-122.3, 37.9],
    [-122.5, 37.9],
    [-122.5, 37.7]  # Close the polygon
])
```

---

## Time Ranges

### Date Strings

```python
time_range=("2021-06-01", "2021-06-30")
```

### ISO Timestamps

```python
time_range=("2021-06-01T00:00:00Z", "2021-06-30T23:59:59Z")
```

### None (Service Default)

```python
time_range=None  # Uses service's default range
```

---

## Next Steps

✅ **You're ready to explore!**

**Learn more:**
- **[API Reference](API_REFERENCE.md)** - Full API documentation
- **[Services Guide](SERVICES.md)** - Explore all 16+ data sources
- **[Jupyter Notebooks](../notebooks/README.md)** - Interactive tutorials
- **[Credentials Setup](CREDENTIALS.md)** - Configure authenticated services

**Common tasks:**
- [Add a new service](EXTENDING_SERVICES.md)
- [Run production pipeline](operations/PANGENOME_PIPELINE.md)
- [Manage databases](operations/DATABASE_MANAGEMENT.md)

---

## Getting Help

- **Documentation:** Browse [docs/README.md](README.md)
- **Examples:** Check [examples/](../examples/)
- **Issues:** Report bugs on GitHub
- **Contributing:** See [CONTRIBUTING.md](../CONTRIBUTING.md)