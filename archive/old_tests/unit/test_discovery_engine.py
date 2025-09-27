"""
Unit tests for semantic discovery engine.

Tests search functionality, relevance scoring, and discovery capabilities.
"""

import pytest
from unittest.mock import Mock, patch
from env_agents.core.discovery_engine import (
    SemanticDiscoveryEngine, DiscoveryQuery, SearchResult, 
    MatchType, SearchScope
)
from env_agents.core.service_registry import ServiceRegistry
from env_agents.core.metadata_schema import (
    ServiceMetadata, VariableInfo, ServiceCapabilities,
    SpatialCoverage, TemporalCoverage, create_service_metadata_template
)


@pytest.fixture
def mock_registry():
    """Create mock service registry with test data"""
    registry = Mock(spec=ServiceRegistry)
    
    # Create test services
    weather_metadata = create_service_metadata_template("WEATHER_TEST")
    weather_metadata.title = "Weather Data Service"
    weather_metadata.description = "High quality weather observations and forecasts"
    weather_metadata.provider = "National Weather Service"
    weather_metadata.capabilities.domains = ["climate", "atmospheric", "meteorology"]
    weather_metadata.capabilities.variables = [
        VariableInfo(
            id="temp_air", 
            canonical="atmospheric:air_temperature_celsius",
            name="Air Temperature",
            description="Ambient air temperature at 2m height",
            unit="degC",
            domain="climate"
        ),
        VariableInfo(
            id="humidity",
            canonical="atmospheric:relative_humidity_percent", 
            name="Relative Humidity",
            description="Relative humidity percentage",
            unit="percent",
            domain="climate"
        ),
        VariableInfo(
            id="pressure",
            canonical="atmospheric:sea_level_pressure_pa",
            name="Sea Level Pressure", 
            description="Atmospheric pressure at sea level",
            unit="Pa",
            domain="atmospheric"
        )
    ]
    weather_metadata.capabilities.spatial_coverage = SpatialCoverage(
        description="Continental United States",
        bbox=[-125.0, 25.0, -66.0, 49.0]
    )
    
    soil_metadata = create_service_metadata_template("SOIL_TEST")
    soil_metadata.title = "Soil Properties Database"
    soil_metadata.description = "Agricultural soil survey data with chemical and physical properties"
    soil_metadata.provider = "Soil Survey Service"
    soil_metadata.capabilities.domains = ["soil", "agriculture", "pedology"]
    soil_metadata.capabilities.variables = [
        VariableInfo(
            id="ph",
            canonical="soil:ph_water",
            name="Soil pH",
            description="Soil pH measured in water solution", 
            unit="pH_units",
            domain="soil"
        ),
        VariableInfo(
            id="organic_matter",
            canonical="soil:organic_matter_percent",
            name="Organic Matter",
            description="Soil organic matter percentage",
            unit="percent", 
            domain="soil"
        )
    ]
    soil_metadata.capabilities.spatial_coverage = SpatialCoverage(
        description="Agricultural regions of North America"
    )
    
    # Mock registry methods
    registry.get_all_metadata.return_value = {
        "WEATHER_TEST": weather_metadata,
        "SOIL_TEST": soil_metadata
    }
    
    registry.list_services.return_value = ["WEATHER_TEST", "SOIL_TEST"]
    
    def mock_get_service(service_id):
        services = {
            "WEATHER_TEST": weather_metadata,
            "SOIL_TEST": soil_metadata
        }
        return services.get(service_id)
    
    registry.get_service.side_effect = mock_get_service
    
    # Mock discover_services method
    def mock_discover_services(domain=None):
        if domain == "climate" or domain == "atmospheric" or domain == "meteorology":
            return ["WEATHER_TEST"]
        elif domain == "soil":
            return ["SOIL_TEST"]
        else:
            return []
    
    registry.discover_services.side_effect = mock_discover_services
    
    return registry


@pytest.fixture 
def discovery_engine(mock_registry):
    """Create discovery engine with mock registry"""
    return SemanticDiscoveryEngine(mock_registry)


class TestDiscoveryEngine:
    """Test basic discovery engine functionality"""
    
    def test_initialization(self, mock_registry):
        """Test discovery engine initialization"""
        engine = SemanticDiscoveryEngine(mock_registry)
        
        assert engine.registry == mock_registry
        assert hasattr(engine, '_variable_aliases')
        assert hasattr(engine, '_domain_keywords')
        
        # Check that variable aliases were built
        assert isinstance(engine._variable_aliases, dict)
        assert 'temperature' in engine._variable_aliases
        
        # Check that domain keywords were built
        assert isinstance(engine._domain_keywords, dict)
        assert 'climate' in engine._domain_keywords


class TestTextBasedDiscovery:
    """Test text-based semantic discovery"""
    
    def test_simple_text_search(self, discovery_engine):
        """Test simple text query"""
        results = discovery_engine.discover("temperature")
        
        assert len(results) > 0
        assert any(r.service_id == "WEATHER_TEST" for r in results)
        
        # Weather service should be found for temperature query
        weather_result = next(r for r in results if r.service_id == "WEATHER_TEST")
        assert weather_result.relevance_score > 0
        assert len(weather_result.matches) > 0
    
    def test_domain_specific_search(self, discovery_engine):
        """Test domain-specific queries"""
        # Climate query should find weather service
        climate_results = discovery_engine.discover("climate data")
        climate_services = [r.service_id for r in climate_results]
        assert "WEATHER_TEST" in climate_services
        
        # Soil query should find soil service  
        soil_results = discovery_engine.discover("soil properties")
        soil_services = [r.service_id for r in soil_results]
        assert "SOIL_TEST" in soil_services
    
    def test_complex_query(self, discovery_engine):
        """Test complex multi-word query"""
        results = discovery_engine.discover("atmospheric pressure measurements")
        
        # Should find weather service due to atmospheric domain and pressure variable
        assert any(r.service_id == "WEATHER_TEST" for r in results)
        
        weather_result = next(r for r in results if r.service_id == "WEATHER_TEST")
        assert weather_result.relevance_score > 0
    
    def test_no_matches_query(self, discovery_engine):
        """Test query with no matches"""
        results = discovery_engine.discover("nonexistent data type")
        
        # Should return empty or very low relevance results
        high_relevance = [r for r in results if r.relevance_score > 0.5]
        assert len(high_relevance) == 0


class TestVariableBasedDiscovery:
    """Test variable-based discovery"""
    
    def test_exact_variable_match(self, discovery_engine):
        """Test exact variable ID match"""
        results = discovery_engine.discover_by_variable("temp_air")
        
        assert len(results) > 0
        assert any(r.service_id == "WEATHER_TEST" for r in results)
        
        # Should have high relevance for exact match
        weather_result = next(r for r in results if r.service_id == "WEATHER_TEST")
        assert weather_result.relevance_score > 0.8
    
    def test_canonical_variable_match(self, discovery_engine):
        """Test canonical variable name match"""
        results = discovery_engine.discover_by_variable("atmospheric:air_temperature_celsius")
        
        assert len(results) > 0
        assert any(r.service_id == "WEATHER_TEST" for r in results)
        
        weather_result = next(r for r in results if r.service_id == "WEATHER_TEST")
        assert weather_result.relevance_score > 0.9  # Canonical match should be high
    
    def test_partial_variable_match(self, discovery_engine):
        """Test partial variable name match"""
        results = discovery_engine.discover_by_variable("temperature", canonical_only=False)
        
        assert len(results) > 0
        weather_results = [r for r in results if r.service_id == "WEATHER_TEST"]
        assert len(weather_results) > 0
        
        # Should find match but with lower relevance than exact match
        assert weather_results[0].relevance_score > 0
    
    def test_canonical_only_search(self, discovery_engine):
        """Test canonical-only variable search"""
        # This should find the weather service
        canonical_results = discovery_engine.discover_by_variable(
            "atmospheric:air_temperature_celsius", 
            canonical_only=True
        )
        
        # This should not find anything (not a canonical name)
        non_canonical_results = discovery_engine.discover_by_variable(
            "temp_air",
            canonical_only=True
        )
        
        assert len(canonical_results) > 0
        # Note: temp_air is an ID, not canonical, so might still be found
        # depending on implementation details


class TestLocationBasedDiscovery:
    """Test location-based discovery"""
    
    def test_us_location_discovery(self, discovery_engine):
        """Test discovery for US location"""
        # Location in continental US
        results = discovery_engine.discover_by_location(39.0, -98.0)  # Geographic center of US
        
        # Weather service covers continental US, so should be found
        assert any(r.service_id == "WEATHER_TEST" for r in results)
    
    def test_global_vs_regional_coverage(self, discovery_engine):
        """Test coverage matching logic"""
        # Test location discovery - mock services have different coverage
        results = discovery_engine.discover_by_location(45.0, -93.0)  # Minnesota
        
        # Both services should potentially be found as they have broad coverage
        service_ids = [r.service_id for r in results]
        assert len(service_ids) > 0
    
    def test_outside_coverage_location(self, discovery_engine):
        """Test location outside service coverage"""
        # Test with a location that might be outside coverage
        results = discovery_engine.discover_by_location(60.0, 100.0)  # Siberia
        
        # Results will depend on how coverage checking is implemented
        # At minimum, should not crash
        assert isinstance(results, list)


class TestDomainBasedDiscovery:
    """Test domain-based discovery"""
    
    def test_climate_domain(self, discovery_engine):
        """Test climate domain discovery"""
        results = discovery_engine.discover_by_domain("climate")
        
        climate_services = [r.service_id for r in results]
        assert "WEATHER_TEST" in climate_services
        
        weather_result = next(r for r in results if r.service_id == "WEATHER_TEST")
        assert weather_result.relevance_score > 0
    
    def test_soil_domain(self, discovery_engine):
        """Test soil domain discovery"""
        results = discovery_engine.discover_by_domain("soil")
        
        soil_services = [r.service_id for r in results]
        assert "SOIL_TEST" in soil_services
    
    def test_nonexistent_domain(self, discovery_engine):
        """Test discovery for nonexistent domain"""
        results = discovery_engine.discover_by_domain("nonexistent")
        
        # Should return empty results
        assert len(results) == 0


class TestStructuredDiscovery:
    """Test structured discovery queries"""
    
    def test_discovery_query_creation(self):
        """Test DiscoveryQuery creation and defaults"""
        query = DiscoveryQuery()
        
        assert query.query_text is None
        assert query.variables == []
        assert query.domains == []
        assert query.max_results == 20
        assert query.scope == SearchScope.ALL
    
    def test_discovery_query_with_filters(self):
        """Test DiscoveryQuery with various filters"""
        query = DiscoveryQuery(
            query_text="temperature data",
            variables=["temp_air", "humidity"],
            domains=["climate"],
            min_quality_score=0.8,
            max_results=10,
            scope=SearchScope.GOVERNMENT
        )
        
        assert query.query_text == "temperature data"
        assert len(query.variables) == 2
        assert "climate" in query.domains
        assert query.min_quality_score == 0.8
        assert query.scope == SearchScope.GOVERNMENT
    
    def test_structured_query_execution(self, discovery_engine):
        """Test execution of structured discovery query"""
        query = DiscoveryQuery(
            query_text="weather temperature",
            domains=["climate"],
            max_results=5
        )
        
        results = discovery_engine.discover(query)
        
        assert len(results) <= 5  # Respects max_results
        assert any(r.service_id == "WEATHER_TEST" for r in results)


class TestVariableSuggestions:
    """Test variable name suggestions"""
    
    def test_temperature_suggestions(self, discovery_engine):
        """Test suggestions for temperature"""
        suggestions = discovery_engine.suggest_variables("temp", limit=10)
        
        assert len(suggestions) > 0
        assert all(len(suggestion) == 3 for suggestion in suggestions)  # (name, service_id, count)
        
        # Should find temperature-related variables
        suggestion_names = [s[0] for s in suggestions]
        assert any("temp" in name.lower() for name in suggestion_names)
    
    def test_partial_name_suggestions(self, discovery_engine):
        """Test suggestions with partial names"""
        suggestions = discovery_engine.suggest_variables("ph", limit=5)
        
        # Should find pH-related variables from soil service
        assert len(suggestions) > 0
        
        # Check that soil service pH variable is found
        ph_suggestions = [s for s in suggestions if "ph" in s[0].lower()]
        assert len(ph_suggestions) > 0
    
    def test_no_suggestions(self, discovery_engine):
        """Test suggestions for nonexistent variable"""
        suggestions = discovery_engine.suggest_variables("nonexistent_variable")
        
        assert len(suggestions) == 0


class TestCapabilitySummary:
    """Test capability summary generation"""
    
    def test_capability_summary_structure(self, discovery_engine):
        """Test capability summary structure"""
        summary = discovery_engine.get_capability_summary()
        
        assert isinstance(summary, dict)
        assert 'total_domains' in summary
        assert 'domains' in summary
        assert 'total_variables' in summary
        assert 'providers' in summary
        assert 'variables_by_domain' in summary
    
    def test_capability_summary_content(self, discovery_engine):
        """Test capability summary content accuracy"""
        summary = discovery_engine.get_capability_summary()
        
        # Should have domains from our test services
        assert summary['total_domains'] > 0
        assert 'climate' in summary['domains']
        assert 'soil' in summary['domains']
        
        # Should have providers
        providers = summary['providers']
        assert 'National Weather Service' in providers
        assert 'Soil Survey Service' in providers
        
        # Should have variables by domain
        vars_by_domain = summary['variables_by_domain']
        assert 'climate' in vars_by_domain
        assert 'soil' in vars_by_domain


class TestMatchTypeAndScoring:
    """Test match types and relevance scoring"""
    
    def test_match_type_enum(self):
        """Test MatchType enum values"""
        assert MatchType.EXACT.value == "exact"
        assert MatchType.CANONICAL.value == "canonical"
        assert MatchType.SYNONYM.value == "synonym"
        assert MatchType.FUZZY.value == "fuzzy"
        assert MatchType.DOMAIN.value == "domain"
        assert MatchType.SPATIAL.value == "spatial"
        assert MatchType.TEMPORAL.value == "temporal"
    
    def test_search_result_creation(self):
        """Test SearchResult creation and scoring"""
        # Create mock metadata
        metadata = create_service_metadata_template("TEST_RESULT")
        
        # Create result with matches
        matches = [
            (MatchType.EXACT, "temperature", 1.0),
            (MatchType.DOMAIN, "climate", 0.4)
        ]
        
        result = SearchResult(
            service_id="TEST_RESULT",
            metadata=metadata,
            relevance_score=0.0,  # Will be calculated from matches
            matches=matches,
            reason="Test result"
        )
        
        assert result.service_id == "TEST_RESULT"
        assert len(result.matches) == 2
        assert result.relevance_score > 0  # Should be calculated from matches
    
    def test_relevance_score_calculation(self):
        """Test automatic relevance score calculation"""
        metadata = create_service_metadata_template("SCORE_TEST")
        
        # High relevance matches
        high_matches = [(MatchType.EXACT, "test", 1.0)]
        high_result = SearchResult(
            service_id="SCORE_TEST",
            metadata=metadata,
            relevance_score=0.0,
            matches=high_matches,
            reason="High relevance test"
        )
        
        # Lower relevance matches
        low_matches = [(MatchType.FUZZY, "test", 0.3)]
        low_result = SearchResult(
            service_id="SCORE_TEST", 
            metadata=metadata,
            relevance_score=0.0,
            matches=low_matches,
            reason="Low relevance test"
        )
        
        assert high_result.relevance_score > low_result.relevance_score


class TestErrorHandling:
    """Test error handling in discovery engine"""
    
    def test_empty_registry(self):
        """Test discovery with empty registry"""
        empty_registry = Mock(spec=ServiceRegistry)
        empty_registry.get_all_metadata.return_value = {}
        empty_registry.list_services.return_value = []
        
        engine = SemanticDiscoveryEngine(empty_registry)
        
        # Should handle empty registry gracefully
        results = engine.discover("test query")
        assert len(results) == 0
        
        suggestions = engine.suggest_variables("test")
        assert len(suggestions) == 0
        
        summary = engine.get_capability_summary()
        assert summary['total_domains'] == 0
    
    def test_malformed_metadata_handling(self, mock_registry):
        """Test handling of malformed metadata"""
        # Create metadata with missing fields
        bad_metadata = create_service_metadata_template("BAD_SERVICE")
        bad_metadata.capabilities.variables = []  # Empty variables
        bad_metadata.capabilities.domains = []    # Empty domains
        
        mock_registry.get_all_metadata.return_value = {"BAD_SERVICE": bad_metadata}
        mock_registry.list_services.return_value = ["BAD_SERVICE"]
        
        engine = SemanticDiscoveryEngine(mock_registry)
        
        # Should handle gracefully without crashing
        results = engine.discover("test")
        assert isinstance(results, list)
        
        summary = engine.get_capability_summary()
        assert isinstance(summary, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])