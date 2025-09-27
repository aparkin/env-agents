# API Reference

**env-agents v2.0** provides a unified interface for environmental data integration through a simple 3-method pattern.

## Core Interface: SimpleEnvRouter

The primary interface for environmental data access.

### Constructor

```python
from env_agents.core import SimpleEnvRouter

router = SimpleEnvRouter(base_dir=".")
```

**Parameters:**
- `base_dir` (str): Project directory for credentials and registry files

### Method 1: register(adapter) → bool

Register an environmental data adapter.

```python
from env_agents.adapters import NASA_POWER, WQP

router.register(NASA_POWER())
router.register(WQP())
```

**Parameters:**
- `adapter` (BaseAdapter): Adapter instance implementing BaseAdapter interface

**Returns:**
- `bool`: True if registration successful

### Method 2: discover(query=None, **filters) → Union[List[str], Dict]

Find services and capabilities.

```python
# List all services
services = router.discover()
# → ['NASA_POWER', 'WQP']

# Search for temperature data
temp_services = router.discover(query="temperature")
# → {'services': ['NASA_POWER', 'WQP'], 'total_variables': 26}

# Service-specific discovery
nasa_vars = router.discover(service="NASA_POWER", limit=5)
```

**Parameters:**
- `query` (str, optional): Search term for variables
- `service` (str, optional): Specific service to query
- `limit` (int, optional): Limit results (default: 20)
- `domain` (str, optional): Domain filter ("climate", "water", etc.)

**Returns:**
- `List[str]`: Service names (if no filters)
- `Dict`: Detailed discovery results with variables and metadata

### Method 3: fetch(service, spec) → pandas.DataFrame

Retrieve environmental data.

```python
from env_agents.core.models import RequestSpec, Geometry

# Define request
spec = RequestSpec(
    geometry=Geometry(type="point", coordinates=[-122.4194, 37.7749]),
    time_range=("2024-08-01", "2024-08-03"),
    variables=["T2M", "PRECTOTCORR"]
)

# Fetch data
df = router.fetch('NASA_POWER', spec)
# → pandas.DataFrame with 6 observations
```

**Parameters:**
- `service` (str): Service name from registered adapters
- `spec` (RequestSpec): Data request specification

**Returns:**
- `pandas.DataFrame`: Standardized data with 24 core columns

## Data Models

### RequestSpec

Standardized request specification for all services.

```python
from env_agents.core.models import RequestSpec, Geometry

spec = RequestSpec(
    geometry=Geometry(type="point", coordinates=[-122.4, 37.7]),
    time_range=("2024-01-01", "2024-01-31"),
    variables=["temperature", "precipitation"],
    extra={"timeout": 60}
)
```

**Parameters:**
- `geometry` (Geometry): Spatial specification
- `time_range` (Tuple[str, str]): ISO date range
- `variables` (List[str], optional): Variable names to retrieve
- `extra` (Dict, optional): Service-specific parameters

### Geometry

Spatial geometry specification.

```python
# Point
point = Geometry(type="point", coordinates=[-122.4, 37.7])

# Bounding box
bbox = Geometry(type="bbox", coordinates=[-123, 37, -122, 38])
```

**Types:**
- `"point"`: Single coordinate pair `[longitude, latitude]`
- `"bbox"`: Bounding box `[min_lon, min_lat, max_lon, max_lat]`

## Output Schema

All services return DataFrames with standardized 24-column schema:

### Identity Columns
- `observation_id`: Unique identifier
- `dataset`: Service name (e.g., "NASA_POWER")
- `source_url`: Data source URL
- `source_version`: API version
- `license`: Data license

### Spatial Columns
- `geometry_type`: "point", "polygon", etc.
- `latitude`, `longitude`: Decimal degrees
- `geom_wkt`: Well-Known Text geometry
- `spatial_id`: Location identifier
- `site_name`: Human-readable location
- `admin`: Administrative region
- `elevation_m`: Elevation in meters

### Temporal Columns
- `time`: ISO 8601 timestamp
- `temporal_coverage`: Time period description
- `retrieval_timestamp`: When data was fetched

### Data Columns
- `variable`: Standardized variable name
- `value`: Numeric value
- `unit`: Measurement unit
- `depth_top_cm`, `depth_bottom_cm`: Depth range
- `qc_flag`: Quality control flag

### Metadata Columns
- `attributes`: Native service attributes (JSON)
- `provenance`: Data lineage information

## Available Services

env-agents v2.0 includes 10 canonical environmental data services:

| Service | Variables | Coverage | Authentication |
|---------|-----------|----------|----------------|
| **NASA_POWER** | 6 weather/solar | Global | API Key |
| **WQP** | 22,736 water quality | US/International | None |
| **EARTH_ENGINE** | 100+ satellite assets | Global | Service Account |
| **EPA_AQS** | 9 air quality | US | API Key |
| **USGS_NWIS** | 15 streamflow/groundwater | US | None |
| **SoilGrids** | 15 soil properties | Global | None |
| **OpenAQ** | 40 air quality | Global | API Key |
| **GBIF** | 8 biodiversity | Global | None |
| **OSM_Overpass** | 70 infrastructure | Global | None |
| **SSURGO** | 10 soil survey | US | None |

**Total: 22,921+ environmental variables**

## Error Handling

All methods raise descriptive exceptions:

```python
from env_agents.core.errors import FetchError

try:
    df = router.fetch('SERVICE_NAME', spec)
except FetchError as e:
    print(f"Data retrieval failed: {e}")
```

## Authentication

Services requiring API keys use template-based credential management:

1. Copy credential template:
```bash
cp config/templates/credentials.yaml.template config/credentials.yaml
```

2. Add your API keys to `config/credentials.yaml`

3. Never commit credential files (protected by .gitignore)

See [CREDENTIALS.md](CREDENTIALS.md) for detailed setup instructions.

## Quick Start Example

```python
from env_agents.core import SimpleEnvRouter
from env_agents.adapters import NASA_POWER
from env_agents.core.models import RequestSpec, Geometry

# 1. Initialize
router = SimpleEnvRouter(base_dir=".")

# 2. Register services
router.register(NASA_POWER())

# 3. Discover capabilities
services = router.discover()
print(f"Available: {services}")

# 4. Fetch data
spec = RequestSpec(
    geometry=Geometry(type="point", coordinates=[-122.4, 37.7]),
    time_range=("2024-08-01", "2024-08-03"),
    variables=["T2M", "PRECTOTCORR"]
)

df = router.fetch('NASA_POWER', spec)
print(f"Retrieved {len(df)} observations")
```

For complete examples, see `examples/quick_start.py` and the notebook tutorials.