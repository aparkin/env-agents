# Testing Directory Structure & Usage Guide

**Clean and organized testing framework for env-agents Phase I**  
**Updated:** September 13, 2025

## 📁 **Organized Directory Structure**

```
env-agents/
│
├── 📋 TESTING_GUIDE.md                    # Complete testing documentation
├── 🚀 run_tests.py                        # Simple test runner script
│
├── tests/                                 # All test code
│   ├── unit/                             # Fast, isolated unit tests
│   │   ├── test_metadata_schema.py       # ✅ Created - Metadata validation
│   │   ├── test_discovery_engine.py      # ✅ Created - Search functionality
│   │   ├── test_service_registry.py      # Registry operations
│   │   └── test_resilient_fetcher.py     # Fallback strategies
│   │
│   ├── integration/                      # Service integration tests
│   │   ├── test_government_apis.py       # Government service validation
│   │   ├── test_earth_engine.py          # Earth Engine integration  
│   │   └── test_service_health.py        # Health monitoring
│   │
│   ├── notebooks/                        # Interactive notebook tests
│   │   ├── 01_Framework_Validation.ipynb # ✅ Created - Basic validation
│   │   ├── 02_Service_Discovery.ipynb    # Discovery scenarios
│   │   ├── 03_Data_Retrieval.ipynb       # Fetching workflows
│   │   ├── 04_Health_Monitoring.ipynb    # Performance analysis
│   │   └── 05_Production_Readiness.ipynb # End-to-end validation
│   │
│   ├── legacy/                           # ✅ Archived legacy tests
│   │   ├── comprehensive_data_test.py    # Moved from root
│   │   ├── test_enhanced_system.py       # Moved from root
│   │   ├── test_adaptive_surgo.py        # Moved from integration/
│   │   └── [other legacy tests...]
│   │
│   ├── test_phase_i_integration.py       # ✅ Created - Main integration tests
│   └── run_validation_suite.py           # ✅ Created - Automated validation
│
├── notebooks/                            # Interactive notebooks
│   ├── testing/                          # Current testing notebooks
│   │   └── 01_Framework_Validation.ipynb # ✅ Created
│   └── legacy/                           # ✅ Archived legacy notebooks
│       ├── Complete_Demo_Fixed_Ordered.ipynb
│       ├── Interactive_Testing_Clean.ipynb
│       └── [other legacy notebooks...]
│
├── examples/                             # Demonstration code
│   ├── phase_i_demo.py                   # ✅ Created - Live demo
│   └── validation_examples/              # Validation scenarios
│
└── [other framework code...]
```

## 🚀 **Quick Start - How to Run Tests**

### **1. Simple Test Execution**

```bash
# Navigate to project directory
cd env-agents

# Run all validations (recommended)
python run_tests.py --all

# Run specific test types
python run_tests.py --unit              # Fast unit tests
python run_tests.py --integration       # Integration tests
python run_tests.py --validation        # Comprehensive validation
python run_tests.py --demo             # Live demonstration
python run_tests.py --notebook         # Interactive validation

# With verbose output
python run_tests.py --unit --verbose
```

### **2. Advanced Test Execution**

```bash
# Manual pytest commands
python -m pytest tests/unit/ -v                    # Unit tests
python -m pytest tests/test_phase_i_integration.py # Integration tests
python -m pytest tests/ -k "discovery" -v         # Tests matching "discovery"
python -m pytest -m "not slow" tests/ -v          # Skip slow tests

# Comprehensive validation with report
python tests/run_validation_suite.py --verbose --integration
cat validation_report.txt
```

### **3. Interactive Notebook Testing**

```bash
# Launch Jupyter for interactive testing
jupyter lab notebooks/testing/

# Or execute notebooks automatically
jupyter nbconvert --to notebook --execute notebooks/testing/01_Framework_Validation.ipynb
```

## 📊 **Test Categories & Expected Timing**

| Test Type | Duration | Scope | Purpose |
|-----------|----------|-------|---------|
| **Unit Tests** | <30 seconds | Individual components | Logic validation |
| **Integration Tests** | 1-3 minutes | Service interactions | Workflow validation |
| **Validation Suite** | 2-5 minutes | Complete framework | Production readiness |
| **Demo Script** | 3-7 minutes | End-to-end scenarios | Feature demonstration |
| **Interactive Notebooks** | 5-30 minutes | Manual validation | Human verification |

## 🎯 **Success Criteria**

### **Passing Tests Should Show:**
- ✅ All imports successful
- ✅ Router initialization working  
- ✅ Service registration functional
- ✅ Discovery engine responding
- ✅ Health monitoring active
- ✅ Legacy compatibility maintained

### **Expected Output Example:**
```
env-agents Testing Framework
========================================
🧪 Running unit tests...
✅ Unit tests passed

🔗 Running integration tests...  
✅ Integration tests passed

🔍 Running comprehensive validation suite...
✅ Validation suite passed

🎯 Running Phase I demonstration...
✅ Demo completed successfully

========================================
✅ All 4 test suites passed
🎯 Framework is ready for production use
```

## 🔍 **Debugging Failed Tests**

### **Common Issues:**

1. **Import Errors:**
   ```bash
   pip install -e .                    # Reinstall in development mode
   python -c "import env_agents; print(env_agents.__file__)"
   ```

2. **Missing Dependencies:**
   ```bash
   pip install pandas>=2.0 requests>=2.32 pydantic>=2.0
   pip install pytest jupyter           # For testing
   ```

3. **Path Issues:**
   ```bash
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   python run_tests.py --unit --verbose
   ```

4. **Permission Issues:**
   ```bash
   chmod +x run_tests.py
   chmod +x tests/run_validation_suite.py
   ```

## 📋 **Test Development Guidelines**

### **Adding New Unit Tests:**
```python
# tests/unit/test_new_component.py
import pytest
from env_agents.core.new_component import NewComponent

class TestNewComponent:
    def test_basic_functionality(self):
        component = NewComponent()
        result = component.process()
        assert result is not None
```

### **Adding New Integration Tests:**
```python
# tests/integration/test_new_integration.py
import pytest
from env_agents import UnifiedEnvRouter

@pytest.mark.integration
class TestNewIntegration:
    def test_end_to_end(self):
        router = UnifiedEnvRouter()
        # Test complete workflow
```

### **Adding New Notebook Tests:**
1. Create notebook in `notebooks/testing/`
2. Include clear objectives and pass/fail criteria
3. Add timing information
4. Include visual outputs where helpful

## 📈 **Maintenance Schedule**

### **Daily (Development):**
- Run unit tests before commits
- Quick validation suite before pushes

### **Weekly (Integration):**
- Full validation suite with integration tests
- Review and update any failing tests
- Check performance metrics

### **Monthly (Cleanup):**
- Archive outdated legacy tests
- Update test documentation
- Review test coverage metrics
- Update notebook examples

## 🎉 **Benefits of This Organization**

### **✅ Clear Separation:**
- Unit tests for fast feedback
- Integration tests for workflow validation  
- Legacy tests preserved but organized
- Interactive notebooks for human verification

### **✅ Easy Usage:**
- Simple `run_tests.py` script for all needs
- Clear documentation and examples
- Automated validation with reports

### **✅ Maintenance:**
- Legacy content archived but accessible
- New development follows clear patterns
- Comprehensive testing ensures quality

This organized testing framework ensures the Phase I enhanced env-agents framework maintains production quality while providing clear validation paths for all users.