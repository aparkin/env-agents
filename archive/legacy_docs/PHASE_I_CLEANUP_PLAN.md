# ENV-AGENTS PHASE I: CORE DATA RETRIEVAL TOOL CLEANUP PLAN

**Version**: Phase I - Pre-ECOGNITA  
**Focus**: Clean, robust data retrieval with rich metadata and capability discovery  
**Target**: Production-ready extensible data source framework

## 📊 CRITICAL ISSUES IDENTIFIED

### 🔴 **High Priority Issues**
1. **Data Retrieval Reliability**: 67% government failure rate, 0% Earth Engine success
2. **Metadata Inconsistency**: 21.4% government, 35.7% Earth Engine completeness
3. **Schema Standardization**: Inconsistent variable structures across services
4. **Error Handling**: Silent failures, no fallback mechanisms
5. **Documentation Fragmentation**: Multiple overlapping architecture documents

### 🟡 **Medium Priority Issues**
1. **Capability Discovery**: Search only works on service names, not capabilities
2. **Provenance Tracking**: Limited service metadata and data lineage
3. **Test Organization**: Scattered test files with overlapping functionality
4. **Configuration Management**: Inconsistent credential and service setup

## 🏗️ PHASE I ARCHITECTURE - FOCUSED CORE

### **Core Principle: Extensible Data Source Framework**
```
┌─────────────────┐
│   Data Sources  │ ← Government APIs, Earth Engine, Future: S3, APIs, etc.
└─────────────────┘
         │
┌─────────────────┐
│ Service Registry│ ← Rich metadata, capabilities, schemas
└─────────────────┘
         │
┌─────────────────┐
│ Discovery Engine│ ← Semantic search, capability matching
└─────────────────┘
         │
┌─────────────────┐
│ Data Router     │ ← Unified interface, error handling, caching
└─────────────────┘
         │
┌─────────────────┐
│ Standard Output │ ← Consistent DataFrame + rich metadata
└─────────────────┘
```

## 🛠️ CLEANUP TASKS

### **Task 1: Consolidate Documentation (Week 1)**

#### 1.1 Document Cleanup
- [ ] **Archive outdated docs**: Move 7 obsolete .md files to `/docs/archive/`
- [ ] **Create single source of truth**: New `README.md` with clear package overview
- [ ] **Standardize API documentation**: Auto-generated from docstrings
- [ ] **Create deployment guide**: Single setup and configuration guide

#### 1.2 New Documentation Structure
```
env-agents/
├── README.md                    # Main package overview and quickstart
├── docs/
│   ├── API.md                  # Auto-generated API documentation  
│   ├── DEPLOYMENT.md           # Setup, installation, credentials
│   ├── EXTENDING.md            # Adding new data sources
│   └── archive/                # Old documentation
│       ├── ARCHITECTURE.md
│       ├── ENHANCED_ARCHITECTURE.md
│       └── [other old docs]
```

### **Task 2: Standardize Metadata Schema (Week 1-2)**

#### 2.1 Rich Metadata Framework
```python
# env_agents/core/metadata_schema.py
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime

@dataclass
class ServiceCapability:
    """Describes what a service can provide"""
    domains: List[str]              # ['water', 'soil', 'air', 'climate']
    variables: List[Dict[str, Any]] # Structured variable descriptions
    temporal_coverage: str          # "1990-present", "2000-2023" 
    spatial_coverage: str           # "Global", "Continental US", "Europe"
    resolution: Dict[str, str]      # {"temporal": "daily", "spatial": "1km"}
    data_formats: List[str]         # ["time_series", "raster", "point"]

@dataclass  
class ServiceMetadata:
    """Complete service description"""
    service_id: str
    title: str
    description: str
    provider: str
    source_url: str
    license: str
    version: str
    last_updated: datetime
    
    # Technical details
    capabilities: ServiceCapability
    rate_limits: Optional[Dict[str, Any]]
    authentication: Dict[str, Any]  # {"required": bool, "type": "api_key|oauth"}
    
    # Quality metrics
    reliability_score: float        # 0.0-1.0 based on historical success
    data_quality_score: float       # 0.0-1.0 based on completeness/accuracy
    
    # Provenance
    registry_source: str            # "manual", "harvested", "inferred"
    last_validated: datetime
```

#### 2.2 Schema Enforcement
- [ ] **Implement metadata validation**: All services must provide complete metadata
- [ ] **Create metadata templates**: Easy onboarding for new services
- [ ] **Add quality scoring**: Automatic reliability tracking

### **Task 3: Fix Data Retrieval Reliability (Week 2-3)**

#### 3.1 Robust Error Handling
```python
# env_agents/core/resilient_fetcher.py
class ResilientDataFetcher:
    """Handles retries, fallbacks, and error recovery"""
    
    async def fetch_with_fallbacks(
        self, 
        service_id: str,
        primary_request: RequestSpec,
        fallback_locations: List[Location] = None,
        retry_config: RetryConfig = None
    ) -> DataResult:
        """
        1. Try primary request
        2. If location fails, try fallback locations
        3. If parameters fail, try parameter variations
        4. Return detailed error report if all fail
        """
```

#### 3.2 Service Health Monitoring
```python
# env_agents/core/service_health.py
class ServiceHealthTracker:
    """Tracks service reliability and performance"""
    
    def record_request(self, service_id: str, success: bool, response_time: float)
    def get_service_health(self, service_id: str) -> ServiceHealth
    def get_recommended_fallbacks(self, failed_service: str) -> List[str]
```

#### 3.3 Fix Specific Service Issues
- [ ] **SURGO**: Implement proper location validation and parameter handling
- [ ] **Earth Engine**: Fix authentication and data extraction pipeline
- [ ] **EPA_AQS**: Implement proper test mode bypass and location finding
- [ ] **OpenAQ**: Validate API key usage and parameter passing

### **Task 4: Enhanced Discovery Engine (Week 3)**

#### 4.1 Semantic Search Engine  
```python
# env_agents/core/discovery.py
class CapabilityDiscovery:
    """Semantic search across all service capabilities"""
    
    def search_by_domain(self, domain: str) -> List[ServiceMatch]
    def search_by_variable(self, variable_name: str) -> List[ServiceMatch]
    def search_by_location(self, lat: float, lon: float) -> List[ServiceMatch]
    def search_by_time_range(self, start: str, end: str) -> List[ServiceMatch]
    def search_capabilities(self, query: str) -> List[ServiceMatch]
```

#### 4.2 Rich Service Registry
```python
# env_agents/core/service_registry.py
class ServiceRegistry:
    """Centralized registry with rich metadata"""
    
    def register_service(self, metadata: ServiceMetadata)
    def get_service_metadata(self, service_id: str) -> ServiceMetadata
    def discover_services(self, criteria: DiscoveryQuery) -> List[ServiceMatch]
    def validate_service_health(self, service_id: str) -> HealthStatus
```

### **Task 5: Consolidate and Fix Tests (Week 4)**

#### 5.1 Test Structure Cleanup
```
tests/
├── unit/                       # Fast unit tests
│   ├── test_adapters.py       # Individual adapter testing
│   ├── test_metadata.py       # Metadata validation
│   ├── test_discovery.py      # Search functionality
│   └── test_resilience.py     # Error handling
├── integration/               # Service integration tests  
│   ├── test_government_services.py
│   ├── test_earth_engine.py
│   └── test_service_combinations.py
├── reliability/               # Service reliability testing
│   ├── test_service_matrix.py # All services × locations
│   └── test_fallback_scenarios.py
└── notebooks/                 # Clean demo notebooks
    ├── quickstart.ipynb      # 15-minute getting started
    ├── capabilities.ipynb    # Capability discovery demo  
    └── advanced.ipynb        # Advanced usage patterns
```

#### 5.2 Service Validation Matrix
- [ ] **Create robust test locations**: Multiple valid locations per service
- [ ] **Parameter validation**: Test parameter combinations
- [ ] **Error scenario testing**: Network failures, auth issues, invalid parameters
- [ ] **Performance benchmarking**: Response time and success rate tracking

### **Task 6: Code Architecture Cleanup (Week 4-5)**

#### 6.1 Core Module Refactoring
```python
# Clean core structure:
env_agents/
├── core/
│   ├── __init__.py            # Main API exports
│   ├── router.py              # Unified data router (cleaned)
│   ├── metadata_schema.py     # Metadata standards
│   ├── discovery.py           # Capability discovery
│   ├── resilient_fetcher.py   # Error handling
│   ├── service_registry.py    # Service management
│   └── data_models.py         # Request/Response models
├── adapters/
│   ├── base.py               # Base adapter interface
│   ├── government/           # Government API adapters
│   ├── earth_engine/         # Earth Engine adapters  
│   └── examples/             # Template adapters
└── utils/
    ├── credentials.py        # Credential management
    ├── validation.py         # Data validation
    └── testing.py            # Test utilities
```

#### 6.2 Remove Deprecated Code
- [ ] **Archive legacy code**: Move old implementations to `/legacy/`
- [ ] **Remove duplicate functionality**: Consolidate overlapping modules
- [ ] **Standardize import paths**: Clean import structure
- [ ] **Update dependencies**: Remove unused packages

## 🧪 TESTING STRATEGY

### **Reliability Testing Framework**
```python
# New: tests/reliability/service_matrix.py
class ServiceReliabilityMatrix:
    """Test all services with multiple scenarios"""
    
    def test_service_with_multiple_locations(self, service_id: str):
        """Test 5+ different valid locations per service"""
        
    def test_service_parameter_variations(self, service_id: str):
        """Test different parameter combinations"""
        
    def test_service_error_recovery(self, service_id: str):
        """Test error handling and fallbacks"""
```

### **Quality Gates**
- **Data Retrieval Success**: >90% success rate for all services
- **Metadata Completeness**: >95% for all standard fields  
- **Response Time**: <3s for single requests
- **Error Handling**: Graceful degradation for all failure modes

## 📋 EXECUTION TIMELINE

### **Week 1: Foundation**
- Document consolidation and cleanup
- Metadata schema design and implementation
- Remove obsolete files and code

### **Week 2: Reliability** 
- Implement ResilientDataFetcher
- Fix specific service issues (SURGO, Earth Engine, EPA_AQS)
- Add service health monitoring

### **Week 3: Discovery**
- Implement semantic search engine
- Create rich service registry
- Add capability discovery APIs

### **Week 4: Testing**
- Consolidate test suite
- Create service validation matrix
- Build reliability testing framework

### **Week 5: Polish**
- Code architecture cleanup  
- Performance optimization
- Documentation finalization
- Release preparation

## ✅ SUCCESS CRITERIA

1. **>90% data retrieval success rate** across all services
2. **Complete metadata** for all registered services  
3. **Semantic search** finds relevant services by domain/capability
4. **Robust error handling** with meaningful error messages
5. **Clean, documented API** ready for extension
6. **Comprehensive test suite** with reliability monitoring
7. **Single source of truth** documentation

This focused Phase I plan creates a solid foundation for the core data retrieval tool before any ECOGNITA integration.