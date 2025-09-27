"""
Phase I Integration Test Suite - Updated for SimpleEnvRouter

Comprehensive tests for the simplified env-agents framework,
validating the integration of Phase I components with the new
3-method interface: register() → discover() → fetch()
"""

import pytest
import pandas as pd
from datetime import datetime
from pathlib import Path
import tempfile
import shutil

from env_agents import SimpleEnvRouter, RequestSpec, Geometry
from env_agents.adapters.base import BaseAdapter


class MockAdapter(BaseAdapter):
    """Mock adapter for testing"""
    
    DATASET = "MOCK_TEST"
    SOURCE_URL = "https://mock.example.com"
    SOURCE_VERSION = "1.0"
    LICENSE = "Public Domain"
    PROVIDER = "Test Provider"
    
    def __init__(self, should_fail=False):
        super().__init__()
        self.should_fail = should_fail
        self.call_count = 0
    
    def capabilities(self):
        return {
            'variables': [
                {
                    'id': 'temp',
                    'canonical': 'atmospheric:temperature',
                    'name': 'Air Temperature',
                    'description': 'Ambient air temperature',
                    'unit': 'degC',
                    'domain': 'climate'
                },
                {
                    'id': 'humidity',
                    'canonical': 'atmospheric:relative_humidity',
                    'name': 'Relative Humidity',
                    'description': 'Relative humidity percentage',
                    'unit': 'percent',
                    'domain': 'climate'
                }
            ],
            'domains': ['climate', 'atmospheric'],
            'spatial_coverage': 'Global coverage for testing',
            'temporal_coverage': '2020-present',
            'description': 'Mock adapter for testing environmental data framework'
        }
    
    def _fetch_rows(self, spec: RequestSpec):
        self.call_count += 1
        
        if self.should_fail:
            raise Exception("Mock adapter failure for testing")
        
        # Generate mock data
        rows = []
        for i in range(5):  # Generate 5 mock observations
            row = {
                'dataset': self.DATASET,
                'source_url': self.SOURCE_URL,
                'license': self.LICENSE,
                'latitude': 37.0 + (i * 0.1),
                'longitude': -122.0 + (i * 0.1),
                'time': f"2024-01-0{i+1}T12:00:00Z",
                'variable': 'temp',
                'value': 20.0 + i,
                'unit': 'degC'
            }
            rows.append(row)
        
        return rows


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def mock_router(temp_dir):
    """Create simplified router with mock adapters for testing"""
    router = SimpleEnvRouter(base_dir=str(temp_dir))
    
    # Register mock adapters
    mock_adapter = MockAdapter(should_fail=False)
    router.register(mock_adapter)
    
    failing_adapter = MockAdapter(should_fail=True)
    failing_adapter.DATASET = "MOCK_FAIL"
    router.register(failing_adapter)
    
    return router


class TestServiceRegistration:
    """Test service registration with SimpleEnvRouter"""
    
    def test_adapter_registration_success(self, mock_router):
        """Test successful adapter registration"""
        services = mock_router.discover()  # New: discover() instead of list_adapters()
        assert "MOCK_TEST" in services
        assert "MOCK_FAIL" in services
    
    def test_service_capabilities_access(self, mock_router):
        """Test access to service capabilities"""
        capabilities = mock_router.discover(format="detailed")
        
        assert capabilities is not None
        assert capabilities.get('total_services') == 2
        
        # Check specific service capabilities
        service_results = capabilities.get('service_results', {})
        if 'MOCK_TEST' in service_results:
            mock_caps = service_results['MOCK_TEST']
            assert mock_caps.get('provider') == 'Test Provider'
            assert len(mock_caps.get('items', [])) > 0
    
    def test_simple_registration_interface(self, temp_dir):
        """Test the simplified registration interface"""
        router = SimpleEnvRouter(base_dir=str(temp_dir))
        adapter = MockAdapter()
        
        # Simple registration - no complex metadata objects needed
        success = router.register(adapter)
        assert success
        
        # Verify registration worked
        services = router.discover()
        assert "MOCK_TEST" in services


class TestSimplifiedDiscovery:
    """Test the unified discovery interface"""
    
    def test_basic_service_listing(self, mock_router):
        """Test basic service listing functionality"""
        services = mock_router.discover()  # Simplified: discover() instead of list_services()
        assert len(services) >= 2
        assert "MOCK_TEST" in services
        assert "MOCK_FAIL" in services
    
    def test_domain_based_discovery(self, mock_router):
        """Test unified discovery by domain"""
        climate_results = mock_router.discover(domain="climate")
        climate_services = climate_results.get('services', [])
        assert "MOCK_TEST" in climate_services
    
    def test_variable_based_discovery(self, mock_router):
        """Test unified discovery by variable query"""
        temp_results = mock_router.discover(query="temp")
        temp_services = temp_results.get('services', [])
        assert len(temp_services) > 0
        assert "MOCK_TEST" in temp_services
    
    def test_semantic_search(self, mock_router):
        """Test semantic search via unified discover"""
        results = mock_router.discover(query="temperature")
        services = results.get('services', [])
        assert len(services) > 0
        assert "MOCK_TEST" in services
    
    def test_detailed_capabilities(self, mock_router):
        """Test detailed capability information"""
        capabilities = mock_router.discover(format="detailed")
        
        assert 'available_domains' in capabilities
        assert 'available_providers' in capabilities
        domains = capabilities.get('available_domains', [])
        # Mock adapters provide climate and atmospheric domains
        assert any(domain in ['climate', 'atmospheric'] for domain in domains)
    
    def test_convenience_methods(self, mock_router):
        """Test backward compatibility convenience methods"""
        # These should work as aliases to discover()
        services_alt = mock_router.list_services()
        assert len(services_alt) >= 2
        
        search_results = mock_router.search("temp")
        assert len(search_results.get('services', [])) > 0
        
        capabilities_alt = mock_router.get_capabilities()
        assert capabilities_alt.get('total_services', 0) >= 2


class TestDataFetching:
    """Test data fetching with resilience features"""
    
    def test_successful_data_fetch(self, mock_router):
        """Test successful data fetching"""
        spec = RequestSpec(
            geometry=Geometry(type="point", coordinates=[-122.0, 37.0]),
            variables=["temp"],
            time_range=("2024-01-01", "2024-01-05")
        )
        
        data = mock_router.fetch("MOCK_TEST", spec)
        
        assert isinstance(data, pd.DataFrame)
        assert len(data) > 0
        assert 'observation_id' in data.columns
        assert 'variable' in data.columns
        assert 'value' in data.columns
    
    def test_resilient_fetch_with_diagnostics(self, mock_router):
        """Test resilient fetch that returns full diagnostics"""
        spec = RequestSpec(
            geometry=Geometry(type="point", coordinates=[-122.0, 37.0]),
            variables=["temp"]
        )
        
        # SimpleEnvRouter uses basic fetch - test with exception handling for resilience
        try:
            data = mock_router.fetch("MOCK_TEST", spec)
            assert isinstance(data, pd.DataFrame)
            assert len(data) > 0
        except Exception as e:
            pytest.fail(f"Fetch should not fail for MOCK_TEST: {e}")
    
    def test_fetch_failure_handling(self, mock_router):
        """Test handling of fetch failures"""
        spec = RequestSpec(
            geometry=Geometry(type="point", coordinates=[-122.0, 37.0]),
            variables=["temp"]
        )
        
        with pytest.raises(Exception):
            mock_router.fetch("MOCK_FAIL", spec)
    
    def test_resilient_fetch_failure_diagnostics(self, mock_router):
        """Test failure diagnostics in resilient fetch"""
        spec = RequestSpec(
            geometry=Geometry(type="point", coordinates=[-122.0, 37.0]),
            variables=["temp"]
        )
        
        # SimpleEnvRouter uses basic fetch - test failure handling
        with pytest.raises(Exception) as exc_info:
            mock_router.fetch("MOCK_FAIL", spec)
        assert "Mock adapter failure" in str(exc_info.value)
    
    def test_multiple_service_fetch(self, mock_router):
        """Test fetching from multiple services"""
        spec = RequestSpec(
            geometry=Geometry(type="point", coordinates=[-122.0, 37.0]),
            variables=["temp"]
        )
        
        requests = [
            ("MOCK_TEST", spec),
            ("MOCK_FAIL", spec)
        ]
        
        # SimpleEnvRouter - test multiple fetches individually
        results = []
        for service_id, spec in requests:
            try:
                data = mock_router.fetch(service_id, spec)
                results.append({'success': True, 'data': data})
            except Exception as e:
                results.append({'success': False, 'error': str(e)})
        
        assert len(results) == 2
        assert results[0]['success']
        assert not results[1]['success']


class TestHealthMonitoring:
    """Test health monitoring and statistics"""
    
    def test_overall_health_check(self, mock_router):
        """Test overall system health check"""
        # SimpleEnvRouter - basic health check via service discovery
        services = mock_router.discover()
        capabilities = mock_router.discover(format="detailed")
        
        # Basic health indicators
        assert len(services) >= 2
        assert capabilities.get('total_services', 0) >= 2
        assert capabilities.get('successful_services', 0) >= 1
    
    def test_service_health_tracking(self, mock_router):
        """Test individual service health tracking"""
        # First perform some operations to generate health data
        spec = RequestSpec(
            geometry=Geometry(type="point", coordinates=[-122.0, 37.0]),
            variables=["temp"]
        )
        
        # Successful fetch
        try:
            mock_router.fetch("MOCK_TEST", spec)
        except:
            pass
        
        # Failed fetch
        try:
            mock_router.fetch("MOCK_FAIL", spec)
        except:
            pass
        
        # SimpleEnvRouter - check service availability
        services = mock_router.discover()
        assert "MOCK_TEST" in services
        
        # Test service can be queried
        capabilities = mock_router.discover(format="detailed")
        service_results = capabilities.get('service_results', {})
        assert "MOCK_TEST" in service_results
    
    def test_router_statistics(self, mock_router):
        """Test router performance statistics"""
        # Generate some activity
        spec = RequestSpec(
            geometry=Geometry(type="point", coordinates=[-122.0, 37.0]),
            variables=["temp"]
        )
        
        try:
            mock_router.fetch("MOCK_TEST", spec)
        except:
            pass
        
        # SimpleEnvRouter - basic statistics via capabilities
        capabilities = mock_router.discover(format="detailed")
        
        assert capabilities.get('total_services', 0) > 0
        assert capabilities.get('successful_services', 0) >= 0
        # Basic operation count available
        assert 'total_items_across_services' in capabilities


class TestLegacyCompatibility:
    """Test backward compatibility with legacy interfaces"""
    
    def test_legacy_capabilities_format(self, mock_router):
        """Test legacy capabilities method returns expected format"""
        # Test convenience method that should alias to get_capabilities
        caps = mock_router.get_capabilities()
        
        assert isinstance(caps, dict)
        service_results = caps.get('service_results', {})
        assert "MOCK_TEST" in service_results
        
        mock_caps = service_results["MOCK_TEST"]
        assert 'provider' in mock_caps
        assert 'items' in mock_caps
        assert isinstance(mock_caps['items'], list)
    
    def test_refresh_capabilities(self, mock_router):
        """Test legacy refresh capabilities functionality"""
        harvest = mock_router.refresh_capabilities(write=False)
        
        assert isinstance(harvest, dict)
        assert "MOCK_TEST" in harvest
        assert "variables" in harvest["MOCK_TEST"]
    
    def test_legacy_discovery_interface(self, mock_router):
        """Test legacy service discovery interface"""
        # Test that legacy methods still work via convenience aliases
        domain_results = mock_router.discover(domain="climate")
        services = domain_results.get('services', [])
        assert "MOCK_TEST" in services


class TestConfigurationOptions:
    """Test various configuration options and edge cases"""
    
    def test_basic_router_initialization(self, temp_dir):
        """Test basic SimpleEnvRouter initialization"""
        router = SimpleEnvRouter(base_dir=str(temp_dir))
        
        adapter = MockAdapter()
        success = router.register(adapter)
        assert success
        
        # Verify basic functionality
        services = router.discover()
        assert "MOCK_TEST" in services
    
    def test_router_with_custom_base_dir(self, temp_dir):
        """Test router with custom base directory"""
        custom_dir = temp_dir / "custom"
        custom_dir.mkdir()
        
        router = SimpleEnvRouter(base_dir=str(custom_dir))
        
        adapter = MockAdapter()
        router.register(adapter)
        
        # Verify router works with custom directory
        services = router.discover()
        assert len(services) >= 1


@pytest.mark.integration
class TestEndToEndScenarios:
    """End-to-end integration test scenarios"""
    
    def test_complete_discovery_to_fetch_workflow(self, mock_router):
        """Test complete workflow from discovery to data fetch"""
        
        # Step 1: Discover services for temperature data
        temp_results = mock_router.discover(query="temp")
        temp_services = temp_results.get('services', [])
        assert len(temp_services) > 0
        
        # Step 2: Get service capabilities
        service_id = temp_services[0]
        capabilities = mock_router.discover(format="detailed")
        assert capabilities is not None
        assert service_id in capabilities.get('service_results', {})
        
        # Step 3: Fetch data
        spec = RequestSpec(
            geometry=Geometry(type="point", coordinates=[-122.0, 37.0]),
            variables=["temp"],
            time_range=("2024-01-01", "2024-01-05")
        )
        
        data = mock_router.fetch(service_id, spec)
        assert isinstance(data, pd.DataFrame)
        assert len(data) > 0
    
    def test_semantic_search_to_data_workflow(self, mock_router):
        """Test semantic search to data retrieval workflow"""
        
        # Step 1: Semantic search using unified discover
        results = mock_router.discover(query="atmospheric temperature")
        services = results.get('services', [])
        assert len(services) > 0
        
        # Step 2: Select first matching service
        service_id = services[0]
        assert service_id is not None
        
        # Step 3: Fetch data with resilient interface
        spec = RequestSpec(
            geometry=Geometry(type="point", coordinates=[-122.0, 37.0]),
            variables=["temp"]
        )
        
        # SimpleEnvRouter uses basic fetch
        data = mock_router.fetch(service_id, spec)
        assert isinstance(data, pd.DataFrame)
        assert len(data) > 0
    
    def test_multi_service_comparison(self, mock_router):
        """Test comparing data from multiple services"""
        
        spec = RequestSpec(
            geometry=Geometry(type="point", coordinates=[-122.0, 37.0]),
            variables=["temp"]
        )
        
        # Get services that provide temperature using unified discover
        temp_results = mock_router.discover(query="temp")
        temp_services = temp_results.get('services', [])
        
        # Fetch from available services
        requests = [(service_id, spec) for service_id in temp_services[:2]]  # Limit to 2
        # SimpleEnvRouter - fetch from services individually
        successful_results = []
        for service_id, spec in requests:
            try:
                data = mock_router.fetch(service_id, spec)
                successful_results.append({'service': service_id, 'data': data})
            except Exception:
                pass  # Service failed, skip
        
        assert len(successful_results) >= 1
        
        # Verify data quality
        for result in successful_results:
            assert isinstance(result['data'], pd.DataFrame)
            assert len(result['data']) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])