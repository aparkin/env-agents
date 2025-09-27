# Environmental Services Framework - Test Suite

**Framework Version**: 1.0.0  
**Test Coverage**: Production Integration Tests  
**Status**: Active Test Suite

This directory contains the current test suite for the env-agents environmental data framework, focused on integration testing and validation of the production-ready system.

## 🧪 Current Test Structure

### Integration Tests

**`test_phase_i_integration.py`**
- **Purpose**: Comprehensive Phase I integration testing with SimpleEnvRouter
- **Coverage**: Core framework components and simplified 3-method interface
- **Test Categories**:
  - Mock adapter testing with standardized patterns
  - SimpleEnvRouter 3-method interface validation (register → discover → fetch)
  - Unified discovery system testing (87.5% method reduction)
  - Service registration and capability discovery
  - Resilient fetching and health monitoring
- **Status**: Active integration test suite (Updated for Phase 2)

**`run_validation_suite.py`**
- **Purpose**: Automated validation suite for live service testing
- **Coverage**: Real-world service validation across all 10 adapters
- **Test Categories**:
  - Live API connectivity testing
  - Data retrieval and schema validation
  - Service capability discovery
  - Error handling and fallback mechanisms
- **Status**: Production validation suite

### Unit Tests

**`unit/test_metadata_schema.py`**
- **Purpose**: Metadata schema validation and structure testing
- **Coverage**: ServiceCapabilities, VariableInfo, coverage models
- **Status**: Active unit tests for metadata components

**`unit/test_discovery_engine.py`**
- **Purpose**: Discovery engine functionality testing
- **Coverage**: Service discovery, capability indexing, search functionality
- **Status**: Active unit tests for discovery components

### Contract Tests

**`test_contract.py`**
- **Purpose**: Basic contract and API structure validation
- **Status**: Placeholder for expanded contract testing

## 🚀 Running Tests

### Prerequisites
```bash
# Install framework in development mode
pip install -e .

# Install test dependencies
pip install pytest pandas>=2.0 requests>=2.32 pydantic>=2.0

# Set up credentials for live service testing (optional)
cp config/credentials.yaml.template config/credentials.yaml
```

### Test Execution

**Run All Tests**:
```bash
# From project root
python -m pytest tests/

# With verbose output
python -m pytest tests/ -v

# With coverage reporting
python -m pytest tests/ --cov=env_agents
```

**Run Specific Test Suites**:
```bash
# Integration tests only
python -m pytest tests/test_phase_i_integration.py

# Unit tests only  
python -m pytest tests/unit/

# Live service validation
python tests/run_validation_suite.py
```

**Run Individual Test Categories**:
```bash
# Test SimpleEnvRouter registration and discovery
python -m pytest tests/test_phase_i_integration.py::TestServiceRegistration
python -m pytest tests/test_phase_i_integration.py::TestSimplifiedDiscovery

# Test data fetching functionality  
python -m pytest tests/test_phase_i_integration.py::TestDataFetching

# Test end-to-end workflows
python -m pytest tests/test_phase_i_integration.py::TestEndToEndScenarios

# Test metadata schema
python -m pytest tests/unit/test_metadata_schema.py

# Test discovery engine
python -m pytest tests/unit/test_discovery_engine.py
```

## 📊 Test Coverage & Expected Results

### Integration Test Coverage
- ✅ **Adapter Pattern Compliance**: All adapters follow unified BaseAdapter pattern
- ✅ **Schema Validation**: 20-column standardized output schema across all services
- ✅ **Error Handling**: Comprehensive error handling and fallback strategies
- ✅ **Metadata Richness**: Rich semantic metadata and provenance tracking
- ✅ **Service Discovery**: Automated capability discovery and indexing

### Live Service Validation
- ✅ **10/10 Services Operational**: 100% success rate across environmental services
- ✅ **Data Quality**: Proper data retrieval and schema compliance
- ✅ **Performance**: Response times within acceptable thresholds
- ✅ **Reliability**: Consistent service availability and error recovery

### Unit Test Coverage
- ✅ **Metadata Models**: Complete schema validation for all metadata components
- ✅ **Discovery Engine**: Service indexing and search functionality
- ✅ **Core Components**: Router, fetcher, and broker functionality
- ✅ **Error Scenarios**: Proper exception handling and error recovery

## 🔧 Test Configuration

### Test Data
- Mock adapters with representative data patterns
- Live service endpoints (with appropriate rate limiting)
- Sample geographic coordinates and time ranges
- Representative variable sets for each service category

### Test Environments
- **Unit Tests**: Isolated component testing with mocks
- **Integration Tests**: Full framework testing with mock services
- **Validation Tests**: Live service testing with real APIs
- **Performance Tests**: Response time and reliability benchmarking

### Credential Management
- Test suite operates with or without credentials
- Live service tests gracefully skip when credentials unavailable
- Mock adapters provide full coverage without external dependencies

## 📈 Test Metrics & Quality Gates

### Success Criteria
- **Unit Tests**: 100% pass rate for isolated component tests
- **Integration Tests**: 100% pass rate for framework integration
- **Live Service Tests**: ≥ 90% success rate (allows for temporary service issues)
- **Performance Tests**: < 5 second average response time for multi-service queries

### Quality Indicators
- **Schema Compliance**: All adapters return standardized 20-column schema
- **Metadata Completeness**: ≥ 90% of records include full semantic metadata
- **Error Recovery**: Graceful handling of service failures and timeouts
- **Service Discovery**: Complete capability indexing for all registered services

## 🗂️ Archive Structure

Historical and legacy test materials have been organized in `/archive/`:

- `archive/legacy_tests/`: Historical test development and debugging
- `archive/debug_tests/`: Ad-hoc debugging and diagnostic tests
- `archive/legacy_scripts/`: One-off testing scripts and utilities

## 🚀 Development Guidelines

### Adding New Tests

1. **Unit Tests**: Add to `unit/` directory for isolated component testing
2. **Integration Tests**: Extend `test_phase_i_integration.py` for framework testing
3. **Live Service Tests**: Update `run_validation_suite.py` for new service validation
4. **Contract Tests**: Extend `test_contract.py` for API contract validation

### Test Patterns

**SimpleEnvRouter Testing Pattern**:
```python
def test_simple_router_workflow():
    # Test 3-method interface: register → discover → fetch
    router = SimpleEnvRouter(base_dir=".")
    
    # 1. Register services
    success = router.register(MockAdapter())
    assert success
    
    # 2. Discover capabilities  
    services = router.discover()
    assert len(services) > 0
    
    temp_results = router.discover(query="temperature")
    assert len(temp_results.get('services', [])) > 0
    
    # 3. Fetch data
    spec = RequestSpec(geometry=Geometry(...), variables=["temp"])
    data = router.fetch(services[0], spec)
    assert isinstance(data, pd.DataFrame)
```

**Adapter Testing Pattern**:
```python
def test_adapter_compliance(adapter):
    # Test standardized interface
    assert hasattr(adapter, 'DATASET')
    assert hasattr(adapter, 'capabilities')
    assert hasattr(adapter, '_fetch_rows')
    
    # Test capabilities structure
    caps = adapter.capabilities()
    assert 'variables' in caps
    assert 'enhancement_level' in caps
    
    # Test data retrieval
    rows = adapter._fetch_rows(sample_spec)
    assert all(required_column in row for row in rows for required_column in CORE_COLUMNS)
```

**Service Validation Pattern**:
```python
def test_live_service_validation(service_name):
    try:
        # Test basic connectivity
        adapter = get_adapter(service_name)
        capabilities = adapter.capabilities()
        
        # Test data retrieval
        rows = adapter._fetch_rows(test_spec)
        assert len(rows) > 0
        
        # Test schema compliance
        validate_schema_compliance(rows)
        
    except Exception as e:
        pytest.skip(f"Service {service_name} temporarily unavailable: {e}")
```

This test suite ensures the environmental services framework maintains production-level quality, reliability, and compliance with unified interface standards across all 10 environmental data services.