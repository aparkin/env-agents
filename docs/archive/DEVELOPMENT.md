# env-agents Development Plan v2.1

**Updated**: September 21, 2025
**Status**: Active Development Phase
**Target**: Production-Ready ECOGNITA Integration

## Executive Summary

This development plan addresses critical issues identified during comprehensive codebase review and establishes a roadmap for achieving robust, uniform environmental data access through the env-agents framework. Key focus areas include resolving adapter reliability issues, unifying interface patterns, and implementing the unified meta/unitary service architecture theory.

## Critical Issues Identified

### 1. SoilGrids Adapter Reliability Crisis ⚠️ **HIGH PRIORITY**
- **Issue**: Consistent 500 server errors with exponential backoff failures
- **Impact**: Complete service unavailability affecting soil property data access
- **Root Cause**: API reliability problems + potentially aggressive retry strategy
- **Solution Path**: Circuit breaker pattern + cached fallback + working external code integration

### 2. WQP Temporal Data Strategy Limitations ⚠️ **MEDIUM PRIORITY**
- **Issue**: Hardcoded historical data strategy (2022) due to data lag assumptions
- **Impact**: No access to recent water quality measurements
- **Root Cause**: Conservative temporal strategy without dynamic availability checking
- **Solution Path**: Adaptive temporal strategy with availability probing

### 3. Meta-Service/Unitary Service Interface Inconsistencies ⚠️ **MEDIUM PRIORITY**
- **Issue**: Different capability response structures across service types
- **Impact**: Complex client code + reduced ECOGNITA integration readiness
- **Root Cause**: Lack of unified interface theory implementation
- **Solution Path**: Implement unified service architecture theory

### 4. Rate Limiting & Error Handling Inconsistencies ⚠️ **LOW PRIORITY**
- **Issue**: Varying retry strategies and rate limiting across adapters
- **Impact**: Reduced reliability + potential API abuse
- **Root Cause**: Implementation before StandardAdapterMixin full utilization
- **Solution Path**: Standardize through enhanced mixin patterns

## Development Phases

### **Phase 1: Critical Reliability Fixes** 🚨 *[IMMEDIATE - Week 1]*

#### 1.1 SoilGrids Adapter Overhaul
**Objective**: Restore SoilGrids functionality with robust fallback strategy

**Tasks**:
- [ ] **Analyze working external SoilGrids code** provided by user
- [ ] **Implement circuit breaker pattern** with configurable failure thresholds
- [ ] **Add cached fallback data** for essential soil properties when API fails
- [ ] **Implement adaptive timeout strategy** (start low, increase on failures)
- [ ] **Add service health monitoring** with automatic degraded mode
- [ ] **Update retry strategy** to be less aggressive (max 3 attempts, longer delays)

**Implementation Pattern**:
```python
class SoilGridsAdapter(BaseAdapter, StandardAdapterMixin):
    def __init__(self):
        super().__init__()
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=300)
        self.cache_manager = FallbackCacheManager()

    def _fetch_rows(self, spec: RequestSpec) -> List[Dict]:
        if self.circuit_breaker.is_open:
            return self._fetch_from_cache(spec)

        try:
            with self.circuit_breaker:
                return self._fetch_from_api(spec)
        except CircuitBreakerOpen:
            return self._fetch_from_cache(spec)
```

**Success Criteria**:
- [ ] SoilGrids adapter returns data successfully in 80%+ of test cases
- [ ] Graceful degradation to cached data when API fails
- [ ] Circuit breaker prevents cascading failures
- [ ] Integration test passes consistently

#### 1.2 WQP Temporal Strategy Enhancement
**Objective**: Implement adaptive temporal data strategy

**Tasks**:
- [ ] **Add data availability probing** before main query
- [ ] **Implement sliding temporal window** (try recent, fall back to historical)
- [ ] **Add temporal data freshness indicators** in response metadata
- [ ] **Optimize station discovery** to prefer stations with recent data
- [ ] **Add configurable temporal fallback** strategy

**Implementation Pattern**:
```python
def _get_optimal_time_range(self, requested_range: Tuple[str, str]) -> Tuple[str, str]:
    """Find optimal time range with actual data availability"""

    # Try user-requested range first
    if self._probe_data_availability(requested_range):
        return requested_range

    # Fall back to sliding windows
    for months_back in [3, 6, 12, 24]:
        end_date = datetime.now() - timedelta(days=30)  # 1 month lag
        start_date = end_date - timedelta(days=months_back * 30)

        fallback_range = (start_date.isoformat(), end_date.isoformat())
        if self._probe_data_availability(fallback_range):
            return fallback_range

    # Final fallback to known good period
    return ("2022-06-01T00:00:00Z", "2022-12-31T23:59:59Z")
```

**Success Criteria**:
- [ ] WQP adapter successfully finds recent data when available
- [ ] Graceful fallback to historical data with clear metadata indicating reason
- [ ] Temporal freshness indicators in all responses
- [ ] 50%+ improvement in recent data access success rate

### **Phase 2: Interface Unification** 🔧 *[Week 2-3]*

#### 2.1 Unified Service Architecture Implementation
**Objective**: Implement unified meta/unitary service architecture theory

**Tasks**:
- [ ] **Add SERVICE_TYPE constants** to all adapter classes
- [ ] **Standardize capabilities() responses** with unified structure
- [ ] **Implement asset_id parameter handling** for meta-services
- [ ] **Update Earth Engine adapter** to follow unified pattern
- [ ] **Add metadata_freshness fields** to all capability responses
- [ ] **Implement _create_uniform_response() helper** in BaseAdapter

**Earth Engine Pattern**:
```python
def capabilities(self, asset_id: Optional[str] = None, extra: Optional[Dict] = None):
    if asset_id:
        # Asset-specific capabilities
        return self._create_uniform_response(
            service_type="meta",
            asset_id=asset_id,
            variables=self._get_asset_variables(asset_id)
        )
    else:
        # Asset discovery
        return self._create_uniform_response(
            service_type="meta",
            assets=self._get_asset_categories_summary(),
            total_assets=150,
            discovery_methods=["asset_id_direct", "browse_by_category"]
        )
```

**Success Criteria**:
- [ ] All adapters return structurally consistent capability responses
- [ ] Meta-services support both discovery and asset-specific modes
- [ ] Router can handle both service types uniformly
- [ ] Testing notebook validates unified interface compliance

#### 2.2 Router Enhancement for Unified Services
**Objective**: Update router to handle unified service architecture

**Tasks**:
- [ ] **Enhanced discovery method** supporting meta-service asset browsing
- [ ] **Validation for meta-service requests** (require asset_id)
- [ ] **Unified error handling** for both service types
- [ ] **Asset-aware semantic mapping** through TermBroker

**Implementation**:
```python
def discover(self, service_type: Optional[str] = None, include_assets: bool = False):
    """Enhanced discovery supporting both unitary and meta services"""
    results = []

    for name, adapter in self.adapters.items():
        caps = adapter.capabilities()

        if service_type and caps.get("service_type") != service_type:
            continue

        if caps.get("service_type") == "meta" and include_assets:
            # Expand meta-service assets
            for asset in caps.get("assets", []):
                results.append({
                    "service": name,
                    "asset_id": asset["asset_id"],
                    "title": asset["title"],
                    "category": asset.get("category")
                })
        else:
            results.append({
                "service": name,
                "type": caps.get("service_type"),
                "summary": self._create_service_summary(caps)
            })

    return results
```

**Success Criteria**:
- [ ] Router discovery handles both service types uniformly
- [ ] Meta-service validation prevents incomplete requests
- [ ] Asset browsing interface functional
- [ ] Error messages are clear and actionable

### **Phase 3: Comprehensive Testing Enhancement** 📊 *[Week 3-4]*

#### 3.1 Testing Notebook Expansion
**Objective**: Increase testing comprehensiveness and uniformity

**Tasks**:
- [ ] **Add service type validation** to architecture testing
- [ ] **Implement meta-service specific tests** for Earth Engine
- [ ] **Add circuit breaker testing** for SoilGrids reliability
- [ ] **Temporal strategy testing** for WQP adaptive behavior
- [ ] **Interface consistency validation** across all services
- [ ] **Error scenario testing** (network failures, timeouts, invalid requests)
- [ ] **Performance benchmarking** with response time tracking
- [ ] **Semantic mapping validation** with confidence scoring

**Enhanced Testing Sections**:
```python
def test_unified_service_interface_compliance():
    """Test all services follow unified interface pattern"""
    for service_name, adapter_class in CANONICAL_SERVICES.items():
        adapter = adapter_class()
        caps = adapter.capabilities()

        # Validate required fields
        assert "service_type" in caps
        assert "metadata_freshness" in caps

        if caps["service_type"] == "meta":
            # Test asset discovery
            assert "assets" in caps or "asset_categories" in caps

            # Test asset-specific capabilities
            if caps.get("assets"):
                first_asset = caps["assets"][0]
                asset_caps = adapter.capabilities(asset_id=first_asset["asset_id"])
                assert "variables" in asset_caps
                assert asset_caps["asset_id"] == first_asset["asset_id"]

def test_error_resilience_patterns():
    """Test error handling and fallback strategies"""
    # Test network timeouts, server errors, invalid responses
    # Validate circuit breaker behavior
    # Test graceful degradation to cached data
```

**Success Criteria**:
- [ ] 100% interface compliance across all services
- [ ] Error scenarios handled gracefully with clear reporting
- [ ] Performance metrics tracked and within acceptable ranges
- [ ] Meta-service patterns validated thoroughly

#### 3.2 Automated Quality Assurance
**Objective**: Implement continuous quality monitoring

**Tasks**:
- [ ] **Service health monitoring** with automated status checks
- [ ] **Data quality validation** with statistical consistency checks
- [ ] **Semantic mapping regression testing** with confidence tracking
- [ ] **Performance regression detection** with automated alerts
- [ ] **Cache freshness monitoring** with automatic refresh triggers

### **Phase 4: Production Readiness** 🚀 *[Week 4-5]*

#### 4.1 ECOGNITA Integration Preparation
**Objective**: Ensure seamless ECOGNITA agent integration

**Tasks**:
- [ ] **Create EnvAgentsBaseAgent wrapper** for ECOGNITA
- [ ] **Implement schema conversion utilities** (env-agents DataFrame → ECOGNITA assets)
- [ ] **Add semantic metadata preservation** in asset creation
- [ ] **Create usage examples** for ECOGNITA agent developers
- [ ] **Documentation for meta-service asset selection** in conversational flow

**ECOGNITA Integration Pattern**:
```python
class EnvAgentsBaseAgent(BaseAgent):
    def __init__(self, agent_id: str, **kwargs):
        super().__init__(agent_id, **kwargs)
        self.router = SimpleEnvRouter()
        self._register_all_adapters()

    async def fetch_environmental_data(self, dataset: str, spec: RequestSpec) -> pd.DataFrame:
        """Standardized environmental data access for ECOGNITA agents"""
        return self.router.fetch(dataset, spec)

    async def discover_environmental_capabilities(self, domain: str = None) -> List[Dict]:
        """Discovery interface for ECOGNITA conversation flow"""
        return self.router.discover(service_type=None, include_assets=True)

    async def create_environmental_asset(self, data: pd.DataFrame, title: str, **kwargs):
        """Convert env-agents data to ECOGNITA asset"""
        asset_content = self._convert_to_ecognita_format(data)
        return await self.asset_service.create_asset(
            content=asset_content,
            title=title,
            metadata=self._extract_semantic_metadata(data),
            **kwargs
        )
```

#### 4.2 Documentation and Examples
**Objective**: Comprehensive documentation for production use

**Tasks**:
- [ ] **Update architecture documentation** with unified service theory
- [ ] **Create ECOGNITA integration guide** with examples
- [ ] **Document meta-service usage patterns** with Earth Engine examples
- [ ] **API reference documentation** for all adapter methods
- [ ] **Troubleshooting guide** for common issues and solutions

## Implementation Timeline

### Week 1: Critical Fixes
- **Days 1-2**: SoilGrids analysis and circuit breaker implementation
- **Days 3-4**: WQP temporal strategy enhancement
- **Day 5**: Integration testing and validation

### Week 2: Interface Unification
- **Days 1-2**: SERVICE_TYPE implementation and response standardization
- **Days 3-4**: Router enhancement for unified services
- **Day 5**: Interface consistency validation

### Week 3: Testing Enhancement
- **Days 1-3**: Testing notebook expansion with new patterns
- **Days 4-5**: Automated quality assurance implementation

### Week 4: Production Preparation
- **Days 1-3**: ECOGNITA integration preparation
- **Days 4-5**: Documentation and examples

### Week 5: Integration & Validation
- **Days 1-2**: End-to-end ECOGNITA integration testing
- **Days 3-5**: Performance optimization and final validation

## Success Metrics

### Reliability Metrics
- [ ] **SoilGrids Success Rate**: >80% (from current ~0%)
- [ ] **WQP Recent Data Access**: >50% (from current ~0%)
- [ ] **Overall Service Availability**: >95%
- [ ] **Error Recovery Time**: <30 seconds for circuit breaker scenarios

### Interface Consistency Metrics
- [ ] **Service Type Compliance**: 100% (all services declare SERVICE_TYPE)
- [ ] **Response Structure Consistency**: 100% (unified capability responses)
- [ ] **Meta-Service Pattern Support**: 100% (Earth Engine asset discovery functional)

### Testing Coverage Metrics
- [ ] **Interface Compliance Testing**: 100% of services
- [ ] **Error Scenario Coverage**: >90% of common failure modes
- [ ] **Performance Benchmarking**: All services with response time baselines
- [ ] **Semantic Mapping Validation**: >95% confidence for auto-accepted mappings

### ECOGNITA Integration Readiness
- [ ] **Schema Conversion**: 100% core column preservation
- [ ] **Semantic Metadata Preservation**: >90% semantic URIs maintained
- [ ] **Asset Creation Success**: >95% for standard environmental data types
- [ ] **Agent Developer Experience**: Complete documentation with working examples

## Risk Mitigation

### High-Risk Items
1. **SoilGrids API Instability**: Implement robust caching and alternative data sources
2. **WQP Data Availability Variability**: Multiple temporal fallback strategies
3. **Earth Engine Authentication Complexity**: Simplified credential management documentation

### Contingency Plans
1. **Service Failures**: Automatic fallback to cached data with staleness indicators
2. **Performance Issues**: Circuit breaker activation and load balancing
3. **Integration Challenges**: Rollback capability and incremental integration approach

## Post-Implementation Monitoring

### Continuous Monitoring
- [ ] **Daily service health checks** with automated reporting
- [ ] **Weekly performance analysis** with trend detection
- [ ] **Monthly semantic mapping review** with registry updates
- [ ] **Quarterly architecture review** for scalability assessment

### Success Validation
- [ ] **ECOGNITA agent integration** demonstrates seamless environmental data access
- [ ] **Testing notebook** consistently reports >90% system health score
- [ ] **User feedback** indicates significant improvement in reliability and usability
- [ ] **Service coverage** maintains 10 canonical services with expansion capability

This development plan provides a systematic approach to resolving critical issues while advancing the env-agents framework toward production-ready status for ECOGNITA integration. The phased approach ensures that critical reliability issues are addressed first, followed by interface improvements and comprehensive testing validation.