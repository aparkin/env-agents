# env-agents Implementation Plan

**Based on Service Assessment:** September 6, 2025  
**Target:** Production-ready environmental data infrastructure  
**Timeline:** 6 weeks (3 phases)

---

## 🎯 Implementation Strategy

### **Core Principles**
1. **Service-specific caching** for critical metadata and parameters
2. **Robust error handling** with multi-tier fallbacks
3. **API key management** via environment variables + constructor overrides
4. **Production patterns** from ECOGNITA agents
5. **Semantic consistency** via enhanced TermBroker integration

---

## 📋 Phase 1: Quick Wins (Weeks 1-2)

### **Week 1: US EIA Energy Data Adapter**

**Target:** `env_agents/adapters/energy/eia_adapter.py`

```python
class EIAAdapter(BaseAdapter):
    DATASET = "US_EIA"
    SOURCE_URL = "https://api.eia.gov/v2/"
    API_KEY = os.environ.get('EIA_API_KEY', 'iwg624GgGLvgU4gcc8GWFSRy6qJeVrPaGEFJgxo5')
    
    # Service-specific cache
    CACHE_FILE = "cache/eia_datasets.json"
    CACHE_TTL = 604800  # 7 days
```

**Implementation Tasks:**
- [ ] Create EIA adapter with electricity/natural gas endpoints
- [ ] Implement route discovery (`/v2/` → datasets → facets)
- [ ] Add parameter harvesting from API structure  
- [ ] Service-specific caching for dataset metadata
- [ ] Unit tests with provided API key
- [ ] Integration with env-agents router

**Key Features:**
- Electricity market data (RTO regions, generation, capacity)
- Natural gas production and consumption
- Rich metadata from v2 API structure
- Geographic aggregation support

---

### **Week 2: EPA AQS Air Quality Enhancement**

**Target:** Enhance `legacy/extra_adapters.py` → `env_agents/adapters/air/aqs_adapter.py`

```python
class EPAAQSAdapter(BaseAdapter):
    DATASET = "EPA_AQS"
    SOURCE_URL = "https://aqs.epa.gov/data/api"
    
    # Credentials management
    def __init__(self, email=None, key=None):
        self.email = email or os.environ.get('EPA_AQS_EMAIL', 'aparkin@lbl.gov')
        self.key = key or os.environ.get('EPA_AQS_KEY', 'khakimouse81')
```

**Implementation Tasks:**
- [ ] Port existing implementation from `extra_adapters.py`
- [ ] Add metadata harvesting (classes, parameters, sites)
- [ ] Implement geographic site discovery with caching
- [ ] Add state/county-based queries
- [ ] Cache parameter classes and site inventories  
- [ ] Rich error handling for credential issues

**Key Features:**
- 27 parameter classes including criteria pollutants
- Site-based geographic queries
- Historical air quality trends
- Quality assurance flags and metadata

---

## 📋 Phase 2: Salvage & Integration (Weeks 3-4)

### **Week 3: SoilGrids WCS Implementation**

**Target:** Rewrite `env_agents/adapters/soil/soilgrids_adapter.py`

```python
class SoilGridsWCSAdapter(BaseAdapter):
    DATASET = "ISRIC_SoilGrids_WCS"
    WCS_URL = "https://maps.isric.org/mapserv"
    
    # WCS-specific patterns
    def _get_capabilities(self, map_service):
        """Get WCS capabilities and cache coverage info"""
    
    def _describe_coverage(self, map_service, coverage_id):
        """Get detailed coverage description"""
        
    def _get_coverage(self, map_service, coverage_id, bbox, format="GEOTIFF_INT16"):
        """Retrieve actual soil data"""
```

**Implementation Tasks:**
- [ ] Implement WCS GetCapabilities → DescribeCoverage → GetCoverage flow
- [ ] Map existing property names to WCS coverage IDs
- [ ] Add spatial subsetting with coordinate system handling
- [ ] Cache WCS capabilities XML for offline parameter discovery
- [ ] Support multiple soil properties in single request
- [ ] Fallback to simple REST API for point queries

**Key Features:**
- Global 250m resolution soil properties
- Multiple depth layers (0-5cm, 5-15cm, etc.)
- Confidence layers and metadata
- Efficient spatial queries via WCS

---

### **Week 4: NOAA Climate Data Integration**

**Target:** Port ECOGNITA patterns → `env_agents/adapters/climate/noaa_cdo_adapter.py`

```python
class NOAAClimateAdapter(BaseAdapter):
    DATASET = "NOAA_CDO"
    SOURCE_URL = "https://www.ncdc.noaa.gov/cdo-web/api/v2"
    
    # Rate limiting from ECOGNITA agent
    def _rate_limit(self):
        """Implement 0.2s between requests"""
    
    # Geographic station selection
    def find_closest_stations(self, lat, lon, n=5):
        """Port geopy distance calculations"""
```

**Implementation Tasks:**
- [ ] Port ECOGNITA weather agent rate limiting patterns
- [ ] Implement station discovery with geographic proximity
- [ ] Add dataset enumeration (GHCND, NORMAL, etc.)
- [ ] Robust timeout/retry logic for slow endpoints
- [ ] Cache station lists by geographic region
- [ ] Integration with existing NASA POWER for coverage gaps

**Key Features:**
- Historical daily weather (GHCND dataset)
- Station-based geographic queries  
- Multiple data types (TMAX, TMIN, PRCP, etc.)
- Complement NASA POWER with ground-truth data

---

## 📋 Phase 3: Advanced Services (Weeks 5-6)

### **Week 5: Biodiversity & Marine Data**

**GBIF Adapter:** `env_agents/adapters/biodiversity/gbif_adapter.py`
- [ ] Port from `extra_adapters.py` with enhanced metadata
- [ ] Add taxonomic hierarchy support via enumeration APIs
- [ ] Implement occurrence data with rich filtering
- [ ] Cache species lists and taxonomic classifications

**NOAA Buoys Adapter:** `env_agents/adapters/marine/noaa_buoys_adapter.py`  
- [ ] Real-time buoy data parsing from text format
- [ ] Station discovery and metadata extraction
- [ ] Time series data with proper temporal alignment
- [ ] Support for meteorological and oceanographic parameters

---

### **Week 6: Water Quality & Geographic Data**

**USGS WQP Integration:** Port ECOGNITA robust implementation
- [ ] Copy excellent multi-tier fallback strategy
- [ ] Fix content negotiation issues (use CSV format)
- [ ] Implement geographic subdivision for large queries
- [ ] Rich diagnostic reporting for query failures

**OpenStreetMap Overpass:** `env_agents/adapters/geographic/osm_adapter.py`
- [ ] Overpass QL query builder for environmental features
- [ ] Tag-based metadata extraction
- [ ] Geographic feature classification
- [ ] Support for complex spatial relationships

---

## 🏗️ Infrastructure Components

### **Service-Specific Caching System**

```python
# env_agents/core/cache.py
class ServiceCache:
    def __init__(self, service_name, ttl_seconds=604800):
        self.cache_dir = Path("cache")
        self.cache_file = self.cache_dir / f"{service_name}_cache.json"
        self.ttl = ttl_seconds
    
    def get_or_fetch(self, key, fetch_func):
        """Get from cache or fetch and cache"""
        
    def invalidate(self, key=None):
        """Invalidate cache entries"""
```

**Cache Strategy:**
- `cache/epa_aqs_parameters.json` - Parameter classes (weekly refresh)
- `cache/noaa_stations_<region_hash>.json` - Station lists by bbox  
- `cache/soilgrids_capabilities.xml` - WCS capabilities (monthly)
- `cache/eia_datasets.json` - Available datasets (weekly)
- `cache/gbif_species_<taxonomy_hash>.json` - Species lists by region

---

### **Enhanced API Key Management**

```python
# env_agents/core/auth.py
class CredentialManager:
    @staticmethod
    def get_credentials(service_name):
        """Load credentials from environment with fallbacks"""
        
    @staticmethod  
    def validate_credentials(service_name, creds):
        """Test credentials with simple API call"""
```

**Environment Variables:**
```bash
# Add to CLAUDE.md for user documentation
export EIA_API_KEY="iwg624GgGLvgU4gcc8GWFSRy6qJeVrPaGEFJgxo5"
export EPA_AQS_EMAIL="aparkin@lbl.gov" 
export EPA_AQS_KEY="khakimouse81"
export NOAA_EMAIL="aparkin@berkeley.edu"
export NOAA_KEY="UnVwOicsdoEYnXWkSADRiQueKDGDFRWU"
```

---

### **Robust Query Patterns**

```python
# env_agents/core/robust_query.py
class RobustQueryMixin:
    async def multi_tier_query(self, primary_params, fallback_strategies):
        """Implement ECOGNITA-style fallback queries"""
        
    def provide_diagnostics(self, query_result, filters_applied):
        """Rich diagnostic reporting"""
```

**Pattern Implementation:**
1. **Primary Query** - All filters applied
2. **Fallback 1** - Remove temporal filters, filter locally  
3. **Fallback 2** - Remove parameter filters for diagnostics
4. **Rich Diagnostics** - Explain which filters excluded data
5. **Error Recovery** - Graceful degradation with partial results

---

## 📊 Testing & Validation

### **Integration Tests**

```python
# tests/integration/test_service_suite.py
@pytest.mark.integration
class TestServiceSuite:
    def test_eia_electricity_data(self):
        """Test EIA electricity market data"""
        
    def test_epa_aqs_air_quality(self):
        """Test EPA AQS with provided credentials"""
        
    def test_soilgrids_wcs_coverage(self):
        """Test SoilGrids WCS GetCoverage"""
```

**Test Locations:**
- Berkeley, CA: `(-122.27, 37.87)` - Urban test case
- Central Valley: `(-121.0, 36.5)` - Agricultural test case  
- Great Lakes: `(-88.0, 45.0)` - Water quality test case

---

### **Performance Benchmarks**

**Target Metrics:**
- Initial query response: <5 seconds
- Cached metadata access: <100ms  
- Large region queries: <30 seconds
- API error recovery: <2 retries
- Cache hit ratio: >80% for metadata

---

## 🎯 Success Criteria

### **Phase 1 Complete (Week 2)**
- [ ] US EIA adapter functional with metadata caching
- [ ] EPA AQS adapter enhanced with geographic queries
- [ ] 4 total working services in env-agents
- [ ] API key management standardized
- [ ] Service-specific caching implemented

### **Phase 2 Complete (Week 4)**  
- [ ] SoilGrids working via WCS approach
- [ ] NOAA Climate integrated with robust patterns
- [ ] 6 total working services
- [ ] Geographic optimization implemented
- [ ] Error handling meets ECOGNITA standards

### **Phase 3 Complete (Week 6)**
- [ ] 8+ working services with full metadata
- [ ] USGS WQP integration with multi-tier fallbacks
- [ ] Download-cache-serve pattern for large datasets
- [ ] Production-ready for ecognita integration
- [ ] Comprehensive test coverage

**Final Architecture:**
```
env-agents/
├── adapters/
│   ├── air/aqs_adapter.py           # EPA air quality
│   ├── biodiversity/gbif_adapter.py # Species occurrences  
│   ├── climate/noaa_cdo_adapter.py  # Weather stations
│   ├── energy/eia_adapter.py        # Energy data
│   ├── geographic/osm_adapter.py    # OpenStreetMap features
│   ├── marine/noaa_buoys_adapter.py # Real-time marine data
│   ├── power/adapter.py             # NASA POWER (existing)
│   ├── soil/soilgrids_adapter.py    # Global soil data (WCS)
│   └── water/wqp_adapter.py         # Water quality portal
├── cache/                           # Service-specific caches
├── core/
│   ├── auth.py                      # Credential management
│   ├── cache.py                     # Caching infrastructure  
│   ├── robust_query.py              # Multi-tier query patterns
│   └── router.py                    # Enhanced routing
└── tests/integration/               # Comprehensive test suite
```

This implementation provides a production-ready foundation for intelligent environmental data agents with robust error handling, intelligent caching, and excellent metadata integration.