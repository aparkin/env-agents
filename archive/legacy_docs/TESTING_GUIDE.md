# env-agents Testing Guide

**Complete testing framework for the Phase I enhanced env-agents framework**  
**Version:** 1.0.0-beta  
**Updated:** September 13, 2025

## 📋 **Testing Architecture Overview**

```
env-agents/
├── tests/
│   ├── unit/                          # Unit tests (fast, isolated)
│   │   ├── test_metadata_schema.py    # Service metadata validation
│   │   ├── test_service_registry.py   # Registry operations
│   │   ├── test_discovery_engine.py   # Search and discovery
│   │   └── test_resilient_fetcher.py  # Fallback strategies
│   ├── integration/                   # Integration tests (slower, real services)
│   │   ├── test_government_apis.py    # Government service validation
│   │   ├── test_earth_engine.py       # Earth Engine integration
│   │   └── test_service_health.py     # Health monitoring
│   ├── notebooks/                     # Interactive testing notebooks
│   │   ├── 01_Framework_Validation.ipynb    # Basic functionality
│   │   ├── 02_Service_Discovery.ipynb       # Discovery scenarios
│   │   ├── 03_Data_Retrieval.ipynb          # Fetching workflows
│   │   ├── 04_Health_Monitoring.ipynb       # Performance analysis
│   │   └── 05_Production_Readiness.ipynb    # End-to-end validation
│   ├── legacy/                        # Archived legacy tests
│   ├── test_phase_i_integration.py    # Comprehensive Phase I tests
│   └── run_validation_suite.py        # Automated test runner
├── notebooks/
│   ├── legacy/                        # Archived legacy notebooks
│   └── testing/                       # Current testing notebooks
└── examples/
    ├── phase_i_demo.py               # Live demonstration
    └── validation_examples/          # Validation scenarios
```

## 🚀 **Quick Start Testing**

### **1. Run Complete Validation Suite**
```bash
# Navigate to project directory
cd env-agents

# Run comprehensive validation
python tests/run_validation_suite.py --verbose --integration

# Review validation report
cat validation_report.txt
```

### **2. Run Unit Tests Only** 
```bash
# Fast unit tests (< 30 seconds)
python -m pytest tests/unit/ -v

# Run specific component tests
python -m pytest tests/unit/test_discovery_engine.py -v
```

### **3. Run Integration Tests**
```bash
# Full integration tests (requires credentials)
python -m pytest tests/integration/ -v --slow

# Run without slow tests
python -m pytest tests/integration/ -v
```

### **4. Interactive Testing**
```bash
# Launch Jupyter and navigate to notebooks/testing/
jupyter lab notebooks/testing/
```

## 📊 **Test Categories**

### **Unit Tests** (`tests/unit/`)
- **Speed**: Fast (< 30 seconds total)
- **Scope**: Individual components in isolation
- **Dependencies**: Mock adapters, no external services
- **Purpose**: Validate core logic and error handling

### **Integration Tests** (`tests/integration/`)
- **Speed**: Medium (1-5 minutes total)  
- **Scope**: Service interactions and workflows
- **Dependencies**: Real services (with fallbacks)
- **Purpose**: Validate end-to-end functionality

### **Notebook Tests** (`tests/notebooks/`)
- **Speed**: Interactive
- **Scope**: Manual validation and exploration
- **Dependencies**: Full environment
- **Purpose**: Human validation and documentation

### **Legacy Tests** (`tests/legacy/`)
- **Speed**: Variable
- **Scope**: Historical validation
- **Dependencies**: Legacy adapters
- **Purpose**: Regression testing and reference

## 🧪 **Using the Test Scripts**

### **Main Validation Script**

```bash
# Full validation with report generation
python tests/run_validation_suite.py

# Options:
--verbose, -v          # Detailed output
--integration, -i      # Include integration tests
--pattern PATTERN      # Custom test file pattern
--report-file FILE     # Custom report file name

# Examples:
python tests/run_validation_suite.py -v -i
python tests/run_validation_suite.py --pattern="test_*discovery*" 
```

**Output:**
- Console validation report
- `validation_report.txt` with detailed results
- `test_results.json` with machine-readable results

### **Phase I Integration Tests**

```bash
# Run comprehensive Phase I validation
python -m pytest tests/test_phase_i_integration.py -v

# Run specific test classes
python -m pytest tests/test_phase_i_integration.py::TestServiceRegistration -v
python -m pytest tests/test_phase_i_integration.py::TestSemanticDiscovery -v
python -m pytest tests/test_phase_i_integration.py::TestResilientFetching -v

# Run with markers
python -m pytest -m "not slow" tests/test_phase_i_integration.py -v
```

### **Custom Test Execution**

```bash
# Run tests with specific markers
python -m pytest -m integration tests/ -v          # Integration tests only
python -m pytest -m "not slow" tests/ -v           # Skip slow tests
python -m pytest -k "discovery" tests/ -v          # Tests with "discovery" in name

# Generate coverage report
python -m pytest tests/ --cov=env_agents --cov-report=html

# Run with detailed output
python -m pytest tests/ -v -s --tb=long
```

## 📓 **Notebook-Based Testing Plan**

### **Testing Notebook Structure**

#### **01_Framework_Validation.ipynb**
**Purpose:** Basic framework functionality validation  
**Duration:** 5-10 minutes  
**Coverage:**
- Import validation
- Router initialization
- Basic adapter registration
- Core schema validation
- Configuration loading

#### **02_Service_Discovery.ipynb** 
**Purpose:** Service discovery and search validation
**Duration:** 10-15 minutes
**Coverage:**
- Semantic search scenarios
- Variable-based discovery
- Location-based queries
- Domain filtering
- Relevance scoring analysis

#### **03_Data_Retrieval.ipynb**
**Purpose:** Data fetching workflow validation
**Duration:** 15-20 minutes
**Coverage:**
- Standard data fetching
- Resilient fetching with diagnostics
- Fallback strategy testing
- Multi-service coordination
- Error handling scenarios

#### **04_Health_Monitoring.ipynb**
**Purpose:** Health monitoring and performance analysis
**Duration:** 10-15 minutes
**Coverage:**
- Service health tracking
- Performance metrics analysis
- Quality score evaluation
- Registry statistics
- Trend analysis

#### **05_Production_Readiness.ipynb**
**Purpose:** End-to-end production validation
**Duration:** 20-30 minutes
**Coverage:**
- Complete workflows from discovery to data
- Large-scale service coordination
- Performance benchmarking
- Resource usage analysis
- Stress testing scenarios

### **Running Notebook Tests**

```bash
# Install notebook testing dependencies
pip install jupyter nbconvert nbformat

# Launch testing environment
jupyter lab notebooks/testing/

# Automated notebook execution
jupyter nbconvert --to notebook --execute notebooks/testing/01_Framework_Validation.ipynb
jupyter nbconvert --to html --execute notebooks/testing/ --output-dir=test_reports/
```

## 🏗️ **Test Development Workflow**

### **Adding New Tests**

1. **Unit Tests:**
```python
# tests/unit/test_new_component.py
import pytest
from env_agents.core.new_component import NewComponent

class TestNewComponent:
    def test_basic_functionality(self):
        component = NewComponent()
        result = component.process()
        assert result is not None
    
    def test_error_handling(self):
        component = NewComponent()
        with pytest.raises(ValueError):
            component.process(invalid_input=True)
```

2. **Integration Tests:**
```python
# tests/integration/test_new_integration.py
import pytest
from env_agents import UnifiedEnvRouter

@pytest.mark.integration
class TestNewIntegration:
    def test_end_to_end_workflow(self):
        router = UnifiedEnvRouter()
        # Test real service interactions
        pass
```

3. **Notebook Tests:**
```python
# Create new notebook in notebooks/testing/
# Include:
# - Clear objectives
# - Step-by-step validation
# - Visual outputs where helpful
# - Timing information
# - Clear pass/fail criteria
```

### **Test Maintenance**

```bash
# Update test dependencies
pip install -r requirements-dev.txt

# Run test linting
flake8 tests/
black tests/

# Update test documentation
python scripts/generate_test_docs.py
```

## 📈 **Performance Benchmarking**

### **Built-in Benchmarks**

```python
# Run performance benchmarks
from tests.benchmarks import run_performance_suite

results = run_performance_suite()
print(f"Discovery latency: {results['discovery_p95']:.3f}s")
print(f"Fetch success rate: {results['fetch_success_rate']:.1f}%")
```

### **Custom Benchmarking**

```python
# Example custom benchmark
import time
from env_agents import UnifiedEnvRouter

def benchmark_discovery_performance():
    router = UnifiedEnvRouter()
    
    queries = ["temperature", "soil ph", "water quality"]
    times = []
    
    for query in queries:
        start = time.time()
        results = router.search(query)
        end = time.time()
        times.append(end - start)
    
    return {
        'mean_latency': sum(times) / len(times),
        'p95_latency': sorted(times)[int(0.95 * len(times))],
        'total_results': sum(len(router.search(q)) for q in queries)
    }
```

## 🔍 **Debugging Failed Tests**

### **Common Issues and Solutions**

1. **Import Errors:**
```bash
# Reinstall in development mode
pip install -e .

# Check Python path
python -c "import env_agents; print(env_agents.__file__)"
```

2. **Service Timeouts:**
```bash
# Run with longer timeouts
python -m pytest tests/ --timeout=300

# Skip network-dependent tests
python -m pytest -m "not network" tests/
```

3. **Authentication Issues:**
```bash
# Verify credentials configuration
python verify_credentials.py

# Run with mock services only
python -m pytest -m "not real_services" tests/
```

### **Debug Output**

```python
# Enable detailed logging in tests
import logging
logging.basicConfig(level=logging.DEBUG)

# Use pytest debugging
python -m pytest tests/ -v -s --pdb      # Drop into debugger on failure
python -m pytest tests/ -v --lf          # Run last failed tests only
```

## 📋 **Test Checklist**

### **Before Committing Code**
- [ ] All unit tests pass (`python -m pytest tests/unit/`)
- [ ] Integration tests pass (`python -m pytest tests/integration/`)  
- [ ] Phase I validation passes (`python tests/run_validation_suite.py`)
- [ ] No linting errors (`flake8 tests/`)
- [ ] Documentation updated if needed

### **Before Release**
- [ ] Full validation suite passes with integration tests
- [ ] All testing notebooks execute successfully
- [ ] Performance benchmarks meet targets
- [ ] Legacy compatibility validated
- [ ] Production readiness notebook validates end-to-end workflows

### **Continuous Integration**
- [ ] Unit tests run on every commit
- [ ] Integration tests run on pull requests
- [ ] Nightly full validation runs
- [ ] Performance regression testing
- [ ] Documentation generation

## 🎯 **Success Criteria**

### **Unit Test Targets**
- **Coverage**: >90% code coverage
- **Speed**: Complete in <30 seconds
- **Reliability**: 100% pass rate in isolation
- **Maintainability**: Clear, focused test cases

### **Integration Test Targets**
- **Coverage**: All major workflows tested
- **Reliability**: >95% pass rate with real services
- **Performance**: Meet latency and throughput targets
- **Resilience**: Graceful degradation under failures

### **Overall Quality Gates**
- All automated tests pass
- Manual validation notebooks complete successfully  
- Performance benchmarks meet targets
- Production readiness criteria validated
- Documentation and examples current

This comprehensive testing framework ensures the Phase I enhanced env-agents framework meets production quality standards while providing clear validation of all capabilities.