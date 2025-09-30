# env-agents Architecture

**System design and component overview**

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Applications                          │
│   (Research, Monitoring, Analysis, ML/AI, Visualization)   │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      env-agents Core                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Request    │  │   Response   │  │   Semantic   │     │
│  │     Spec     │  │   Schema     │  │    Engine    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            BaseAdapter (Abstract Interface)          │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────┬───────────┬────────────┬──────────┬──────────┘
              │           │            │          │
              ▼           ▼            ▼          ▼
┌─────────────────────────────────────────────────────────────┐
│                   Adapter Implementations                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │   NASA   │  │   USGS   │  │  Earth   │  │   GBIF   │   │
│  │  POWER   │  │   NWIS   │  │  Engine  │  │          │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
└───────┼────────────┼─────────────┼──────────────┼──────────┘
        │            │              │              │
        ▼            ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────┐
│                    External Data Sources                     │
│    NASA API    USGS Web Services    Google EE    GBIF API   │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Request Specification (`RequestSpec`)

**Purpose:** Unified interface for specifying data queries

**Location:** `env_agents/core/models.py`

**Key Fields:**
```python
class RequestSpec:
    geometry: Geometry         # Where to fetch data
    time_range: tuple         # When to fetch data
    variables: list           # What variables (optional)
    attributes: dict          # Additional service-specific params
```

**Geometry Types:**
- `point` - Single location (lon, lat)
- `bbox` - Bounding box (west, south, east, north)
- `polygon` - Custom shape (list of coordinates)

### 2. Response Schema (20-column standard)

**Purpose:** Standardized output format from all adapters

**Core Columns:**

**Identity:**
- `observation_id` - Unique ID for each observation
- `dataset` - Source service name
- `source_url` - Data source URL
- `source_version` - API/dataset version
- `license` - Data license
- `retrieval_timestamp` - When fetched

**Location:**
- `geometry_type` - point, bbox, polygon
- `latitude`, `longitude` - Point location
- `geom_wkt` - WKT geometry string

**Time:**
- `time` - ISO timestamp (YYYY-MM-DD or full datetime)

**Measurement:**
- `variable` - Parameter name (prefixed by service)
- `value` - Numeric measurement
- `unit` - Units of measurement

**Quality & Metadata:**
- `qc_flag` - Quality control status
- `attributes` - Service-specific metadata (JSON)
- `provenance` - Processing history

### 3. BaseAdapter (Abstract Interface)

**Purpose:** Contract that all data adapters must implement

**Location:** `env_agents/adapters/base.py`

**Required Methods:**
```python
class BaseAdapter(ABC):
    # Class constants
    DATASET: str              # Service identifier
    SOURCE_URL: str           # Base URL
    SOURCE_VERSION: str       # Version string
    LICENSE: str             # Data license

    # Required methods
    @abstractmethod
    def capabilities(self) -> Dict:
        """Return service capabilities and available variables"""

    @abstractmethod
    def _fetch_rows(self, spec: RequestSpec) -> List[Dict]:
        """Fetch data and return list of row dicts"""

    # Provided methods
    def fetch(self, spec: RequestSpec) -> pd.DataFrame:
        """Public method - calls _fetch_rows and returns DataFrame"""
```

**Pattern:**
- Subclasses implement `_fetch_rows()` with service-specific logic
- Base class provides `fetch()` wrapper that handles DataFrame conversion
- `capabilities()` describes what the service offers

### 4. Adapter Implementations

**Location:** `env_agents/adapters/`

**Current Adapters:**
- `nasa_power.py` - NASA POWER climate data
- `usgs_nwis.py` - USGS stream gauges
- `gbif.py` - Species observations
- `openaq.py` - Air quality sensors
- `water_quality_portal.py` - Water quality samples
- `ssurgo.py` - Soil survey data
- `osm_overpass.py` - OpenStreetMap features
- `earth_engine/production_adapter.py` - Google Earth Engine
- (and more...)

**Common Pattern:**
```python
class MyAdapter(BaseAdapter):
    DATASET = "MY_SERVICE"
    SOURCE_URL = "https://api.example.com"

    def capabilities(self):
        return {
            "variables": [...],
            "spatial_coverage": "Global",
            ...
        }

    def _fetch_rows(self, spec: RequestSpec):
        # 1. Parse geometry and time from spec
        # 2. Query upstream API
        # 3. Transform to standard schema
        # 4. Return list of row dicts
        return rows
```

---

## Data Flow

### 1. User Request

```python
spec = RequestSpec(
    geometry=Geometry(type="point", coordinates=[-122.4, 37.8]),
    time_range=("2021-01-01", "2021-12-31")
)
```

### 2. Adapter Processing

```python
adapter = NASAPowerAdapter()
data = adapter.fetch(spec)
```

**Internal Steps:**
1. `fetch()` validates spec
2. Calls `_fetch_rows(spec)`
3. Adapter queries upstream API
4. Transforms response to standard schema
5. Returns list of row dicts
6. `fetch()` converts to DataFrame
7. Returns to user

### 3. Standardized Output

```python
# DataFrame with 20 standard columns
print(data.shape)  # (365, 20)
print(data.columns)  # ['observation_id', 'dataset', ...]
```

---

## Design Principles

### 1. Adapter Pattern

**Why:** Unified interface to heterogeneous services

**Benefits:**
- Consistent API across all services
- Easy to add new services
- Swap implementations without changing client code

### 2. Standardized Schema

**Why:** Analysis-ready data without transformation

**Benefits:**
- Immediate compatibility with pandas/analysis tools
- Cross-service data fusion
- Consistent metadata structure

### 3. Service-Specific Optimization

**Why:** Each API has unique characteristics

**Per-adapter configuration:**
- Rate limiting
- Timeout handling
- Retry strategies
- Caching policies

### 4. Minimal External Dependencies

**Core dependencies:**
- `pandas` - DataFrame operations
- `requests` - HTTP client
- `pydantic` - Data validation
- `shapely` - Geometry operations

**Optional dependencies:**
- `earthengine-api` - Only if using Earth Engine
- Service-specific libs as needed

---

## Production Patterns

### Database Integration

**Pattern:** Adapters + SQLite for persistence

```python
# scripts/acquire_environmental_data.py
for cluster_id in clusters:
    spec = create_spec(cluster)
    rows = adapter._fetch_rows(spec)

    # Store in database
    for row in rows:
        db.insert(cluster_id, row)
```

**Schema:**
- `observations` table with 20 standard columns
- `cluster_id` for spatial grouping
- Indexes on cluster_id, dataset, time

### Rate Limiting

**Per-service configuration:**
```python
SERVICE_CONFIG = {
    "NASA_POWER": {"rate_limit": 10.0},  # 10 second wait
    "USGS_NWIS": {"rate_limit": 1.0},    # 1 second wait
}
```

**Implementation:** Sleep after each query to respect API limits

### Error Handling

**Three-tier strategy:**
```python
try:
    rows = adapter._fetch_rows(spec)
    status = "success"
except ServiceUnavailableError:
    status = "retry_later"  # Temporary failure
except NoDataError:
    status = "no_data"      # Expected - location has no data
except Exception as e:
    status = "failed"       # Unexpected error
    log_error(e)
```

---

## Extending the Framework

### Adding a New Adapter

1. **Create adapter file:** `env_agents/adapters/my_service.py`

2. **Implement BaseAdapter:**
```python
from .base import BaseAdapter

class MyServiceAdapter(BaseAdapter):
    DATASET = "MY_SERVICE"
    SOURCE_URL = "https://api.myservice.com"

    def capabilities(self):
        return {"variables": [...]}

    def _fetch_rows(self, spec):
        # Query API and return rows
        return rows
```

3. **Add to canonical services** (optional):
```python
# adapters/__init__.py
CANONICAL_SERVICES = {
    "MY_SERVICE": MyServiceAdapter,
    ...
}
```

4. **Write tests:**
```python
# tests/test_my_service.py
def test_my_service_adapter():
    adapter = MyServiceAdapter()
    spec = RequestSpec(...)
    data = adapter.fetch(spec)
    assert len(data) > 0
```

See [EXTENDING_SERVICES.md](../EXTENDING_SERVICES.md) for full guide.

---

## File Structure

```
env_agents/
├── core/
│   ├── models.py           # RequestSpec, Geometry
│   ├── config.py           # Configuration management
│   └── __init__.py
│
├── adapters/
│   ├── base.py             # BaseAdapter abstract class
│   ├── nasa_power.py       # NASA POWER adapter
│   ├── usgs_nwis.py        # USGS NWIS adapter
│   ├── gbif.py             # GBIF adapter
│   ├── earth_engine/
│   │   └── production_adapter.py
│   └── ...
│
└── __init__.py
```

---

## Testing Strategy

### Unit Tests

**Test individual adapters:**
```python
def test_nasa_power_capabilities():
    adapter = NASAPowerAdapter()
    caps = adapter.capabilities()
    assert "variables" in caps
```

### Integration Tests

**Test with real APIs:**
```python
def test_nasa_power_fetch():
    adapter = NASAPowerAdapter()
    spec = RequestSpec(...)
    data = adapter.fetch(spec)
    assert len(data) > 0
    assert "value" in data.columns
```

### Contract Tests

**Verify all adapters follow schema:**
```python
def test_adapter_contract(adapter_class):
    adapter = adapter_class()
    data = adapter.fetch(spec)

    # Check required columns
    required = ["observation_id", "dataset", "time", "variable", "value"]
    assert all(col in data.columns for col in required)
```

---

## Performance Considerations

### Earth Engine

- **Sequential execution required** due to quota limits
- **Threading-based timeouts** for hanging queries
- **Rate limiting:** 2-5 seconds between queries
- **Temporal fallback:** Auto-handle missing dates

### Unitary Services

- **Parallel execution possible** (independent rate limits)
- **Service-specific tuning:** Each has optimal rate
- **Retry strategies:** Exponential backoff for transient errors

### Database

- **SQLite for local storage** (millions of observations)
- **Batch inserts** for performance
- **Indexes** on cluster_id, dataset, time

---

## Future Architecture Considerations

### Potential Enhancements

1. **Async/await patterns** for parallel fetching
2. **Caching layer** for repeated queries
3. **Distributed execution** for large-scale workloads
4. **Streaming responses** for huge datasets
5. **Plugin system** for external adapters

### Backward Compatibility

- Core schema is stable (20 columns)
- Adapters can add new services without breaking existing code
- `attributes` field allows service-specific extensions

---

For implementation details, see:
- [Adding New Services](../EXTENDING_SERVICES.md)
- [Local Development](LOCAL_DEVELOPMENT.md)
- [Lessons Learned](LESSONS_LEARNED.md)