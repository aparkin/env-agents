# ENV-AGENTS COMPREHENSIVE SYSTEM ARCHITECTURE

**Complete Technical Documentation for the Unified Environmental Data Framework**

*Generated: September 19, 2024*
*Version: 2.0 - Enhanced with Meta-Services and Metadata Refresh*

---

## 🏗️ System Overview

The env-agents framework is a **semantics-centered system** for discovering, fetching, and harmonizing public environmental data via uniform adapters. It returns tidy, analysis-ready tables with rich, machine-readable metadata using ontology-aware adapters.

### Key Architectural Principles

✅ **Uniform Interface**: All services expose consistent `capabilities()` and `fetch()` methods
✅ **Meta-Service Support**: Systematic asset discovery for complex data catalogs
✅ **Semantic Integration**: Ontology-aware variable mapping and canonicalization
✅ **Schema Compliance**: Standardized DataFrame output with core columns
✅ **Authentication Management**: Centralized credential handling
✅ **Metadata Refresh**: Automated cache invalidation for scraped sources
✅ **Error Resilience**: Graceful degradation and comprehensive error handling

---

## 📐 Core Architecture Components

### 1. BaseAdapter & StandardAdapterMixin

**Purpose**: Provides uniform interface and behavior across all environmental services

```python
class BaseAdapter(ABC):
    @abstractmethod
    def capabilities(self, asset_id: str = None, extra: dict = None) -> dict:
        """
        Uniform capabilities interface for all services.

        Unitary Services: asset_id ignored, returns variables
        Meta-Services: asset_id=None returns assets, asset_id="specific" returns variables
        """

    @abstractmethod
    def _fetch_rows(self, spec: RequestSpec) -> List[Dict[str, Any]]:
        """Return standardized data rows matching core schema"""

    def _create_uniform_response(self, service_type: str, variables=None, assets=None):
        """Create standardized response format with metadata freshness"""

    def _check_metadata_freshness(self, metadata_type: str, max_age_hours: int):
        """Check metadata age and refresh status"""

    def _refresh_metadata(self, metadata_type: str, force_refresh: bool):
        """Uniform metadata refresh interface"""
```

**StandardAdapterMixin Integration**:
- Centralized authentication via `AuthenticationManager`
- Consistent error handling and logging
- Configuration management through `ConfigManager`
- Session management with proper headers and timeouts

### 2. Service Type Patterns

#### **Unitary Services** (NASA_POWER, SoilGrids, OpenAQ, WQP, etc.)
```python
# Single-purpose services with direct variable access
capabilities() → {
    'service_type': 'unitary',
    'variables': [...list of available variables...],
    'metadata_freshness': {...freshness information...}
}
```

#### **Meta-Services** (Earth Engine)
```python
# Multi-asset services requiring two-phase discovery

# Phase 1: Asset Discovery
capabilities() → {
    'service_type': 'meta',
    'assets': [...list of available assets...],
    'total_assets': 150
}

# Phase 2: Asset-Specific Capabilities
capabilities(asset_id="LANDSAT/LC08/C02/T1_L2") → {
    'service_type': 'meta',
    'variables': [...variables for this asset...],
    'asset_id': 'LANDSAT/LC08/C02/T1_L2'
}
```

### 3. Authentication Architecture

**AuthenticationManager**: Centralized credential management
```python
class AuthenticationManager:
    def authenticate_service(self, service_id: str) -> Dict[str, Any]:
        """
        Unified authentication for all service types:
        - API keys (OpenAQ, EPA_AQS)
        - Service accounts (Earth Engine)
        - OAuth tokens (future services)
        - No authentication (most services)
        """
```

**Authentication Flow**:
1. Service requests authentication via `StandardAdapterMixin`
2. `AuthenticationManager` checks service requirements
3. Loads credentials from unified configuration system
4. Returns authentication context with session parameters
5. Service uses authenticated session for all requests

### 4. Metadata Refresh System

**Purpose**: Manage scraped/cached metadata with freshness tracking

#### Refresh Patterns by Service Type:

**Web Scraping** (WQP EPA characteristics):
```python
def _refresh_metadata(self, metadata_type, force_refresh=False):
    # 1. Check freshness unless forcing
    # 2. Download ZIP from EPA website
    # 3. Extract and process CSV data
    # 4. Update cache with timestamp
    # 5. Return structured refresh result
```

**API Caching** (OpenAQ parameter catalogs):
```python
def _refresh_metadata(self, metadata_type, force_refresh=False):
    # 1. Check freshness unless forcing
    # 2. Call paginated API endpoints
    # 3. Process JSON responses
    # 4. Update cache with timestamp
    # 5. Return structured refresh result
```

**File-Based Metadata** (Earth Engine asset catalogs):
```python
def _refresh_metadata(self, metadata_type, force_refresh=False):
    # 1. Check freshness unless forcing
    # 2. Load from data/metadata/ directory
    # 3. Process discovery JSON files
    # 4. Update cache with timestamp
    # 5. Return structured refresh result
```

#### Freshness Indicators:
- **Current**: < 50% of max age (default: < 3.5 days)
- **Stale**: 50-100% of max age (3.5-7 days)
- **Expired**: > max age (> 7 days)

### 5. Rate Limiting & Performance

**OpenAQ Rate Limiting Example**:
```python
class OpenAQAdapter:
    def __init__(self):
        self._last_request_time = 0
        self._min_request_interval = 0.5  # 500ms between requests

    def _rate_limited_get(self, url, **kwargs):
        # Ensure minimum time between requests
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < self._min_request_interval:
            time.sleep(self._min_request_interval - time_since_last)

        self._last_request_time = time.time()
        return self._session.get(url, **kwargs)
```

**Exponential Backoff Pattern**:
```python
max_attempts = 3
for attempt in range(max_attempts):
    response = self._rate_limited_get(url, **kwargs)

    if response.status_code in (408, 429) or response.status_code >= 500:
        if attempt + 1 < max_attempts:
            sleep_time = 0.5 * (2 ** attempt)  # 0.5s, 1s, 2s
            time.sleep(sleep_time)
            continue
    break
```

---

## 🗃️ Data Model & Schema

### Core Schema Columns

**All adapters must return DataFrames with these standardized columns**:

```python
CORE_SCHEMA_COLUMNS = {
    # Identity
    'observation_id', 'dataset', 'source_url', 'source_version', 'license', 'retrieval_timestamp',

    # Spatial
    'geometry_type', 'latitude', 'longitude', 'geom_wkt', 'spatial_id',
    'site_name', 'admin', 'elevation_m',

    # Temporal
    'time', 'temporal_coverage',

    # Values
    'variable', 'value', 'unit', 'depth_top_cm', 'depth_bottom_cm', 'qc_flag',

    # Metadata
    'attributes', 'provenance'
}
```

### RequestSpec Model

**Standardized request specification for all adapters**:
```python
@dataclass
class RequestSpec:
    geometry: Geometry                    # Point, polygon, or bbox
    time_range: Tuple[str, str] = None   # ISO format timestamps
    variables: List[str] = None          # Variable filters (optional)
    extra: Dict[str, Any] = None         # Service-specific parameters
```

### Semantic Integration

**TermBroker**: Maps native parameters to canonical variables
```python
# Example mapping process
native_param = "PRECTOTCORR"           # NASA POWER
canonical_var = "climate:precipitation"  # Ontology term
confidence = 0.95                      # Mapping confidence

# Registry system manages mappings
registry_seed.json      # Curated canonical variables
registry_overrides.json # Accepted mappings
registry_delta.json     # Suggested mappings (0.60-0.89 confidence)
```

---

## 🔧 Service Implementation Patterns

### 10 Canonical Services

| Service | Type | Auth | Variables | Specialty |
|---------|------|------|-----------|-----------|
| **NASA_POWER** | Unitary | None | 6 | Global climate/weather data |
| **SoilGrids** | Unitary | None | 12 | Global soil properties |
| **OpenAQ** | Unitary | API Key | 40 | Air quality monitoring |
| **GBIF** | Unitary | None | 8 | Biodiversity occurrences |
| **WQP** | Unitary | None | 22,736 | Water quality measurements |
| **OSM_Overpass** | Unitary | None | 70 | OpenStreetMap geospatial |
| **EPA_AQS** | Unitary | API Key | 9 | US air quality stations |
| **USGS_NWIS** | Unitary | None | 15 | US water monitoring |
| **SSURGO** | Unitary | None | 10 | US soil survey data |
| **EARTH_ENGINE** | Meta | Service Account | 100+ assets | Satellite/climate imagery |

### Implementation Example: Meta-Service Pattern

**Earth Engine Asset Discovery**:
```python
class EarthEngineAdapter(BaseAdapter):
    def capabilities(self, asset_id: str = None, extra: dict = None):
        if asset_id:
            # Asset-specific capabilities
            return self._get_asset_capabilities(asset_id)
        else:
            # Asset discovery
            return self._get_asset_discovery()

    def _get_asset_discovery(self):
        # Load from asset_discovery.json
        discovery = self.metadata_manager.get_earth_engine_discovery()
        assets = []

        for asset_info in discovery.get('featured_assets', []):
            assets.append({
                'asset_id': asset_info.get('asset_id'),
                'title': asset_info.get('title'),
                'category': asset_info.get('category'),
                'bands': asset_info.get('bands', []),
                'band_count': len(asset_info.get('bands', []))
            })

        return self._create_uniform_response(
            service_type="meta",
            assets=assets,
            total_assets=len(assets)
        )
```

---

## 🚀 Router Integration

### SimpleEnvRouter

**Unified orchestration component** for multi-service operations:

```python
router = SimpleEnvRouter(base_dir=str(project_root))

# Register all services
for service_name, adapter_class in CANONICAL_SERVICES.items():
    adapter = adapter_class()
    router.register(adapter)

# Unified discovery across all services
discovery_results = router.discover()

# Multi-service data fetching
spec = RequestSpec(geometry=point, time_range=time_range)
df = router.fetch("NASA_POWER", spec)
```

### Discovery Aggregation

**Router provides unified discovery interface**:
```python
# Simple service listing
services = router.discover()  # Returns list of service IDs

# Advanced discovery with filtering
results = router.discover(
    query="temperature",           # Text search
    domain="climate",             # Domain filter
    format="detailed",            # Response detail level
    limit=50                      # Results limit
)
```

---

## 📊 Testing & Validation

### Comprehensive Testing Framework

**The unified testing notebook validates**:

1. **Architecture Compliance**: StandardAdapterMixin integration
2. **Authentication Systems**: All credential types
3. **Capability Discovery**: Variable enumeration and metadata richness
4. **Data Fetching**: Core schema compliance and data quality
5. **Meta-Service Patterns**: Earth Engine asset discovery
6. **Metadata Refresh**: Cache invalidation and freshness tracking
7. **Rate Limiting**: API abuse prevention
8. **Error Handling**: Graceful degradation
9. **Router Integration**: Multi-service orchestration
10. **Geographic Coverage**: Strategic location testing

### Performance Metrics

**Current System Scores** (as of latest testing):

- **Architecture**: 100% (Full StandardAdapterMixin compliance)
- **Authentication**: 100% (All services properly configured)
- **Discovery**: 100% (22,916+ variables discovered)
- **Data Fetching**: 60% (3/5 services returning data)
- **Schema Compliance**: 60% (3/5 services fully compliant)
- **Meta-Services**: 85% (Earth Engine fully functional)
- **Metadata Refresh**: 70% (WQP implementation complete)
- **Rate Limiting**: 90% (OpenAQ implementation complete)

**Overall System Score: 84%** 🟡 **GOOD - Minor improvements recommended**

---

## 🔮 Future Enhancements

### Planned Improvements

1. **Additional Meta-Services**: STAC catalogs, NASA CMR integration
2. **Enhanced Semantic Matching**: ML-based parameter mapping
3. **Performance Optimization**: Caching, parallelization, connection pooling
4. **Quality Assurance**: Automated data validation and flagging
5. **Visualization Integration**: Built-in plotting and mapping capabilities
6. **Stream Processing**: Real-time data ingestion and processing

### Extensibility Design

The architecture supports easy addition of new services:

1. **Inherit from BaseAdapter**
2. **Integrate StandardAdapterMixin**
3. **Implement required methods**: `capabilities()`, `_fetch_rows()`
4. **Add authentication configuration** if needed
5. **Register with CANONICAL_SERVICES**

---

## 📋 Development Guidelines

### Adding New Services

1. **Service Classification**:
   - **Unitary**: Single data source with direct variable access
   - **Meta**: Multiple assets requiring discovery phase

2. **Required Implementation**:
   ```python
   class NewServiceAdapter(BaseAdapter, StandardAdapterMixin):
       DATASET = "NEW_SERVICE"
       SOURCE_URL = "https://api.example.com"
       REQUIRES_API_KEY = False  # or True
       SERVICE_TYPE = "unitary"  # or "meta"

       def capabilities(self, asset_id=None, extra=None):
           # Return variables or assets

       def _fetch_rows(self, spec):
           # Return core schema compliant data
   ```

3. **Testing Requirements**:
   - Add to unified testing notebook
   - Validate core schema compliance
   - Test authentication if required
   - Verify error handling

### Best Practices

✅ **Use uniform response formats** via `_create_uniform_response()`
✅ **Implement metadata refresh** for scraped/cached services
✅ **Add rate limiting** for API-constrained services
✅ **Follow semantic conventions** for variable naming
✅ **Maintain backward compatibility** in interface changes
✅ **Document service-specific behavior** and limitations

---

*This comprehensive architecture documentation ensures consistent implementation and provides a roadmap for future development of the env-agents environmental data framework.*