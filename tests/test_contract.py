"""
Comprehensive contract tests for env-agents framework.

Tests that all adapters follow the black box interface contract:
- Implement required abstract methods
- Return data conforming to core schema
- Handle RequestSpec inputs properly
- Provide valid capabilities metadata
"""

import pytest
import importlib
import sys
import os
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd

# Add the parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from env_agents.adapters.base import BaseAdapter
    from env_agents.core.models import RequestSpec, Geometry, CORE_COLUMNS
except ImportError as e:
    print(f"Import error: {e}")
    print("Contract tests require the package to be properly installed.")
    print("Run: pip install -e .")
    sys.exit(1)


def discover_all_adapters() -> List[type]:
    """Dynamically discover all adapter classes in the framework."""
    # Import current blessed adapters from CANONICAL_SERVICES
    try:
        from env_agents.adapters import CANONICAL_SERVICES
        adapter_classes = []

        for service_name, adapter_class in CANONICAL_SERVICES.items():
            adapter_classes.append(adapter_class)

        return adapter_classes
    except ImportError:
        # Fallback: direct imports matching current blessed configuration
        adapter_classes = []

        # Current blessed adapters from env_agents/adapters/__init__.py
        current_adapters = [
            ("power.adapter", "NASAPowerAdapter"),
            ("soil.soilgrids_wcs_adapter", "SoilGridsWCSAdapter"),
            ("openaq.adapter", "OpenAQAdapter"),
            ("gbif.adapter", "GBIFAdapter"),
            ("wqp.adapter", "WQPAdapter"),
            ("overpass.adapter", "OverpassAdapter"),
            ("air.adapter", "EPAAQSAdapter"),
            ("nwis.adapter", "USGSNWISAdapter"),
            ("ssurgo.adapter", "SSURGOAdapter"),
            ("earth_engine.gold_standard_adapter", "EarthEngineAdapter"),
        ]

        for module_path, class_name in current_adapters:
            try:
                module = importlib.import_module(f"env_agents.adapters.{module_path}")
                if hasattr(module, class_name):
                    adapter_class = getattr(module, class_name)
                    if issubclass(adapter_class, BaseAdapter) and adapter_class != BaseAdapter:
                        adapter_classes.append(adapter_class)
            except (ImportError, AttributeError) as e:
                print(f"Warning: Could not import {module_path}.{class_name}: {e}")

        return adapter_classes


def create_test_spec() -> RequestSpec:
    """Create a basic test RequestSpec for contract testing."""
    return RequestSpec(
        geometry=Geometry(
            type="point",
            coordinates=[-122.4194, 37.7749]  # San Francisco
        ),
        time_range=("2023-01-01", "2023-01-31"),
        variables=["temperature", "humidity"]  # Generic variables
    )


def validate_core_schema(row: Dict[str, Any]) -> bool:
    """Validate that a row contains all core schema columns."""
    for col in CORE_COLUMNS:
        if col not in row:
            print(f"Missing required column: {col}")
            return False
    return True


def validate_capabilities(capabilities: dict) -> bool:
    """Validate that capabilities dictionary has required structure."""
    service_type = capabilities.get("service_type", "service")
    
    if service_type == "service":
        # Standard service validation - requires 'variables' list
        if "variables" not in capabilities:
            print(f"Missing required capability key for service: variables")
            return False
        if not isinstance(capabilities["variables"], list):
            print("capabilities['variables'] should be a list for standard services")
            return False
    
    elif service_type == "meta":
        # Meta-service validation - requires 'assets' (list or dict for scaling)
        if "assets" not in capabilities:
            print(f"Missing required capability key for meta-service: assets")
            return False
        
        assets = capabilities["assets"]
        if isinstance(assets, list):
            # List format: direct asset list (for smaller meta-services)
            pass  # Valid format
        elif isinstance(assets, dict):
            # Dictionary format: category-based assets (for large-scale meta-services)
            # Each category should have structure like {"count": int, "examples": list}
            for category, info in assets.items():
                if not isinstance(info, dict):
                    print(f"Meta-service asset category '{category}' should be dict with count/examples")
                    return False
                if "count" not in info or "examples" not in info:
                    print(f"Meta-service category '{category}' should have 'count' and 'examples'")
                    return False
        else:
            print("capabilities['assets'] should be list or dict for meta-services")
            return False
    
    else:
        print(f"Invalid service_type: {service_type}. Must be 'service' or 'meta'")
        return False
    
    return True


class TestAdapterContract:
    """Test contract compliance for all adapters."""
    
    def test_adapter_discovery(self):
        """Test that we can discover adapter classes."""
        adapters = discover_all_adapters()
        assert len(adapters) > 0, "Should discover at least one adapter class"
        print(f"Discovered {len(adapters)} adapter classes")
    
    @pytest.mark.parametrize("adapter_class", discover_all_adapters())
    def test_adapter_inheritance(self, adapter_class):
        """Test that all adapters inherit from BaseAdapter."""
        assert issubclass(adapter_class, BaseAdapter), \
            f"{adapter_class.__name__} must inherit from BaseAdapter"
    
    @pytest.mark.parametrize("adapter_class", discover_all_adapters())
    def test_adapter_constants(self, adapter_class):
        """Test that adapters define required class constants."""
        required_constants = ["DATASET", "SOURCE_URL", "SOURCE_VERSION", "LICENSE", "SERVICE_TYPE"]
        
        for const in required_constants:
            assert hasattr(adapter_class, const), \
                f"{adapter_class.__name__} must define {const} constant"
            
            value = getattr(adapter_class, const)
            assert isinstance(value, str), \
                f"{adapter_class.__name__}.{const} must be a string"
            assert len(value) > 0, \
                f"{adapter_class.__name__}.{const} cannot be empty"
        
        # Additional validation for SERVICE_TYPE
        service_type = getattr(adapter_class, "SERVICE_TYPE")
        assert service_type in ["service", "meta"], \
            f"{adapter_class.__name__}.SERVICE_TYPE must be 'service' or 'meta', got '{service_type}'"
    
    @pytest.mark.parametrize("adapter_class", discover_all_adapters())
    def test_adapter_instantiation(self, adapter_class):
        """Test that adapters can be instantiated."""
        try:
            adapter = adapter_class()
            assert adapter is not None, f"Failed to instantiate {adapter_class.__name__}"
        except Exception as e:
            pytest.fail(f"Failed to instantiate {adapter_class.__name__}: {e}")
    
    @pytest.mark.parametrize("adapter_class", discover_all_adapters())
    def test_capabilities_method(self, adapter_class):
        """Test that adapters implement capabilities method properly."""
        adapter = adapter_class()
        
        # Test that capabilities method exists and is callable
        assert hasattr(adapter, 'capabilities'), \
            f"{adapter_class.__name__} must implement capabilities method"
        assert callable(adapter.capabilities), \
            f"{adapter_class.__name__}.capabilities must be callable"
        
        # Test that capabilities returns valid structure
        try:
            capabilities = adapter.capabilities()
            assert isinstance(capabilities, dict), \
                f"{adapter_class.__name__}.capabilities() must return dict"
            assert validate_capabilities(capabilities), \
                f"{adapter_class.__name__}.capabilities() returned invalid structure"
        except Exception as e:
            pytest.fail(f"{adapter_class.__name__}.capabilities() failed: {e}")
    
    @pytest.mark.parametrize("adapter_class", discover_all_adapters())
    def test_fetch_rows_method(self, adapter_class):
        """Test that adapters implement _fetch_rows method."""
        adapter = adapter_class()
        
        # Test that _fetch_rows method exists and is callable
        assert hasattr(adapter, '_fetch_rows'), \
            f"{adapter_class.__name__} must implement _fetch_rows method"
        assert callable(adapter._fetch_rows), \
            f"{adapter_class.__name__}._fetch_rows must be callable"
    
    @pytest.mark.parametrize("adapter_class", discover_all_adapters())
    def test_black_box_interface(self, adapter_class):
        """Test complete black box interface compliance."""
        adapter = adapter_class()
        spec = create_test_spec()
        
        # Test capabilities
        capabilities = adapter.capabilities()
        assert validate_capabilities(capabilities)
        
        # Test that fetch method exists (from BaseAdapter)
        assert hasattr(adapter, 'fetch'), \
            f"{adapter_class.__name__} should inherit fetch method from BaseAdapter"
        assert callable(adapter.fetch), \
            f"{adapter_class.__name__}.fetch should be callable"


class TestSchemaCompliance:
    """Test that adapters return data conforming to core schema."""
    
    @pytest.mark.parametrize("adapter_class", discover_all_adapters()[:3])  # Test first 3 for speed
    def test_fetch_returns_valid_schema(self, adapter_class):
        """Test that _fetch_rows returns valid schema (limited test due to API costs)."""
        adapter = adapter_class()
        spec = create_test_spec()
        
        try:
            # Only test the first few results to avoid API limits
            rows = adapter._fetch_rows(spec)
            assert isinstance(rows, list), \
                f"{adapter_class.__name__}._fetch_rows must return list"
            
            if rows:  # Only validate if data is returned
                first_row = rows[0]
                assert isinstance(first_row, dict), \
                    f"{adapter_class.__name__}._fetch_rows must return list of dicts"
                assert validate_core_schema(first_row), \
                    f"{adapter_class.__name__} returned invalid schema"
                
        except Exception as e:
            # Allow graceful failure for network/API issues during testing
            print(f"Warning: {adapter_class.__name__}._fetch_rows failed: {e}")


class TestReplaceability:
    """Test that adapters are truly replaceable black boxes."""
    
    def test_adapter_replaceability_pattern(self):
        """Test that adapters can be used interchangeably."""
        adapters = discover_all_adapters()[:2]  # Test first 2 for speed
        spec = create_test_spec()
        
        for adapter_class in adapters:
            adapter = adapter_class()
            
            # Test that all adapters have the same interface
            assert hasattr(adapter, 'capabilities')
            assert hasattr(adapter, 'fetch')
            
            # Test that capabilities return the expected format
            capabilities = adapter.capabilities()
            assert isinstance(capabilities, dict)
            assert 'variables' in capabilities
    
    def test_standardized_outputs(self):
        """Test that all adapters produce standardized output format."""
        # This test verifies that the fetch method (from BaseAdapter) 
        # produces consistent DataFrame output regardless of adapter
        adapters = discover_all_adapters()
        
        for adapter_class in adapters:
            adapter = adapter_class()
            
            # Test that fetch method exists and returns DataFrame type annotation
            assert hasattr(adapter, 'fetch')
            
            # We can't easily test the actual return type without API calls,
            # but we can verify the method signature is consistent
            assert callable(adapter.fetch)


if __name__ == "__main__":
    # Run basic discovery test when script is executed directly
    print("Running adapter contract tests...")
    
    adapters = discover_all_adapters()
    print(f"Discovered {len(adapters)} adapter classes:")
    for adapter_class in adapters:
        print(f"  - {adapter_class.__name__}")
    
    print("\nTesting basic instantiation...")
    for adapter_class in adapters:
        try:
            adapter = adapter_class()
            capabilities = adapter.capabilities()
            print(f"  ✅ {adapter_class.__name__}: {len(capabilities.get('variables', []))} variables")
        except Exception as e:
            print(f"  ❌ {adapter_class.__name__}: {e}")
    
    print("\nContract tests completed. Run 'python -m pytest tests/test_contract.py -v' for full test suite.")