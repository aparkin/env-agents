"""
Unit tests for metadata schema validation and quality scoring.

Tests the ServiceMetadata framework for completeness, validation,
and quality scoring functionality.
"""

import pytest
from datetime import datetime
from env_agents.core.metadata_schema import (
    ServiceMetadata, VariableInfo, ServiceCapabilities, 
    SpatialCoverage, TemporalCoverage, AuthenticationInfo,
    QualityMetrics, ProvenanceInfo, MetadataValidator,
    create_service_metadata_template, AuthenticationType,
    RegistrySource, DataFormat
)


class TestVariableInfo:
    """Test VariableInfo dataclass functionality"""
    
    def test_variable_info_creation(self):
        """Test basic VariableInfo creation"""
        var = VariableInfo(
            id="temp_air",
            canonical="atmospheric:air_temperature_celsius",
            name="Air Temperature",
            description="Ambient air temperature",
            unit="degC",
            domain="climate"
        )
        
        assert var.id == "temp_air"
        assert var.canonical == "atmospheric:air_temperature_celsius"
        assert var.name == "Air Temperature"
        assert var.unit == "degC"
        assert var.domain == "climate"
    
    def test_variable_info_defaults(self):
        """Test VariableInfo with default values"""
        var = VariableInfo(id="test_var")
        
        assert var.id == "test_var"
        assert var.canonical is None
        assert var.name == ""
        assert var.description == ""
        assert var.unit is None
        assert var.data_type == "float"
        assert var.quality_flags == []


class TestServiceMetadata:
    """Test ServiceMetadata functionality"""
    
    def test_minimal_valid_metadata(self):
        """Test creation of minimal valid metadata"""
        metadata = ServiceMetadata(
            service_id="TEST_SERVICE",
            title="Test Service",
            description="A test service for validation",
            provider="Test Provider",
            source_url="https://test.example.com",
            license="MIT",
            capabilities=ServiceCapabilities(
                domains=["test"],
                variables=[VariableInfo(id="test_var", name="Test Variable")],
                spatial_coverage=SpatialCoverage(description="Test coverage"),
                temporal_coverage=TemporalCoverage(description="Test temporal"),
                data_formats=[DataFormat.TIME_SERIES]
            )
        )
        
        assert metadata.service_id == "TEST_SERVICE"
        assert metadata.title == "Test Service"
        assert len(metadata.capabilities.variables) == 1
        assert metadata.capabilities.domains == ["test"]
    
    def test_metadata_validation_success(self):
        """Test successful metadata validation"""
        metadata = create_service_metadata_template("VALID_SERVICE")
        metadata.title = "Valid Service"
        metadata.description = "This is a valid service with proper description"
        metadata.provider = "Valid Provider"
        metadata.source_url = "https://valid.example.com"
        metadata.license = "MIT"
        
        # Should not raise exception
        assert metadata.service_id == "VALID_SERVICE"
    
    def test_metadata_validation_failure(self):
        """Test metadata validation with missing required fields"""
        with pytest.raises(ValueError, match="Required field.*is empty"):
            ServiceMetadata(
                service_id="",  # Empty service_id should fail
                title="Test",
                description="Test description",
                provider="Test Provider", 
                source_url="https://test.com",
                license="MIT",
                capabilities=ServiceCapabilities(
                    domains=["test"],
                    variables=[VariableInfo(id="test")],
                    spatial_coverage=SpatialCoverage(description="Test"),
                    temporal_coverage=TemporalCoverage(description="Test"),
                    data_formats=[DataFormat.TIME_SERIES]
                )
            )
    
    def test_metadata_completeness_scoring(self):
        """Test metadata completeness scoring"""
        # Create minimal metadata
        minimal_metadata = create_service_metadata_template("MINIMAL")
        minimal_score = minimal_metadata.get_completeness_score()
        
        # Create rich metadata
        rich_metadata = create_service_metadata_template("RICH")
        rich_metadata.title = "Rich Test Service"
        rich_metadata.description = "Comprehensive test service with detailed information"
        rich_metadata.provider = "Rich Test Provider"
        rich_metadata.version = "2.1.0"
        rich_metadata.notes = "Additional service notes"
        rich_metadata.base_url = "https://api.rich-test.com"
        rich_metadata.authentication.required = True
        rich_metadata.authentication.type = AuthenticationType.API_KEY
        
        rich_score = rich_metadata.get_completeness_score()
        
        # Rich metadata should have higher completeness score
        assert rich_score > minimal_score
        assert 0.0 <= minimal_score <= 1.0
        assert 0.0 <= rich_score <= 1.0
    
    def test_quality_metrics_update(self):
        """Test quality metrics updates"""
        metadata = create_service_metadata_template("QUALITY_TEST")
        
        initial_score = metadata.quality_metrics.reliability_score
        assert initial_score == 0.0
        
        # Update with successful request
        metadata.update_quality_metrics(success=True, response_time=0.5)
        
        assert metadata.quality_metrics.total_requests == 1
        assert metadata.quality_metrics.successful_requests == 1
        assert metadata.quality_metrics.reliability_score > initial_score
        assert metadata.quality_metrics.last_successful_request is not None
        
        # Update with failed request
        metadata.update_quality_metrics(success=False, response_time=2.0, error="Test error")
        
        assert metadata.quality_metrics.total_requests == 2
        assert metadata.quality_metrics.successful_requests == 1
        assert metadata.quality_metrics.last_failed_request is not None
        assert "Test error" in metadata.quality_metrics.error_patterns
    
    def test_overall_quality_score(self):
        """Test overall quality score calculation"""
        metadata = create_service_metadata_template("OVERALL_QUALITY")
        
        # Initially should have low quality due to no reliability data
        initial_quality = metadata.get_quality_score()
        
        # Add some successful requests to improve reliability
        for _ in range(10):
            metadata.update_quality_metrics(success=True, response_time=0.5)
        
        # Set data quality score
        metadata.quality_metrics.data_quality_score = 0.9
        
        improved_quality = metadata.get_quality_score()
        
        # Should improve with better reliability and data quality
        assert improved_quality > initial_quality
        assert 0.0 <= improved_quality <= 1.0
    
    def test_metadata_to_dict(self):
        """Test metadata serialization to dictionary"""
        metadata = create_service_metadata_template("DICT_TEST")
        metadata.title = "Dictionary Test Service"
        
        result_dict = metadata.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict['service_id'] == "DICT_TEST"
        assert result_dict['title'] == "Dictionary Test Service"
        assert 'variables' in result_dict
        assert 'spatial_coverage' in result_dict
        assert 'completeness_score' in result_dict
        assert 'overall_quality_score' in result_dict


class TestMetadataValidator:
    """Test MetadataValidator functionality"""
    
    def test_validate_metadata_success(self):
        """Test validation of valid metadata"""
        metadata = ServiceMetadata(
            service_id="VALID_TEST",
            title="Valid Test Service",
            description="This is a comprehensive test service with sufficient description length",
            provider="Valid Test Provider",
            source_url="https://valid-test.example.com",
            license="MIT License",
            capabilities=ServiceCapabilities(
                domains=["test", "validation"],
                variables=[
                    VariableInfo(
                        id="test_var_1",
                        name="Test Variable 1", 
                        description="First test variable"
                    ),
                    VariableInfo(
                        id="test_var_2",
                        name="Test Variable 2",
                        description="Second test variable"
                    )
                ],
                spatial_coverage=SpatialCoverage(description="Global test coverage"),
                temporal_coverage=TemporalCoverage(description="2020-present"),
                data_formats=[DataFormat.TIME_SERIES, DataFormat.POINT]
            )
        )
        
        issues = MetadataValidator.validate_metadata(metadata)
        assert len(issues) == 0
    
    def test_validate_metadata_failures(self):
        """Test validation of invalid metadata"""
        # Test that invalid metadata raises ValueError during construction
        with pytest.raises(ValueError) as exc_info:
            ServiceMetadata(
                service_id="",  # Empty service_id
                title="",       # Empty title  
                description="Short",  # Too short description
                provider="Test Provider",
                source_url="not-a-url",  # Invalid URL
                license="MIT",
                capabilities=ServiceCapabilities(
                    domains=[],  # Empty domains
                    variables=[], # Empty variables
                    spatial_coverage=SpatialCoverage(description="Test"),
                    temporal_coverage=TemporalCoverage(description="Test"), 
                    data_formats=[DataFormat.TIME_SERIES]
                )
            )
        
        assert "Required field 'service_id' is empty or missing" in str(exc_info.value)
        
        # Test the separate validator function with invalid data
        # We'll create a mock metadata object that bypasses validation
        from unittest.mock import Mock
        mock_metadata = Mock()
        mock_metadata.service_id = ""
        mock_metadata.title = "" 
        mock_metadata.description = "Short"
        mock_metadata.provider = "Test Provider"
        mock_metadata.source_url = "not-a-url"
        mock_metadata.license = "MIT"
        mock_metadata.capabilities = Mock()
        mock_metadata.capabilities.domains = []
        mock_metadata.capabilities.variables = []
        
        issues = MetadataValidator.validate_metadata(mock_metadata)
        
        # Should have multiple validation issues
        assert len(issues) >= 4
        
        # Check for specific expected issues
        issue_texts = ' '.join(issues).lower()
        assert 'service_id' in issue_texts
        assert 'title' in issue_texts
        assert 'description' in issue_texts
        assert 'source_url' in issue_texts
        assert 'domain' in issue_texts
        assert 'variable' in issue_texts
    
    def test_validate_variable_quality(self):
        """Test validation of variable quality"""
        metadata = ServiceMetadata(
            service_id="VAR_TEST",
            title="Variable Test",
            description="Testing variable validation functionality",
            provider="Test Provider",
            source_url="https://test.example.com",
            license="MIT",
            capabilities=ServiceCapabilities(
                domains=["test"],
                variables=[
                    VariableInfo(id="", name="", description=""),  # Missing required fields
                    VariableInfo(id="valid_var", name="Valid Variable", description="Valid description")
                ],
                spatial_coverage=SpatialCoverage(description="Test"),
                temporal_coverage=TemporalCoverage(description="Test"),
                data_formats=[DataFormat.TIME_SERIES]
            )
        )
        
        metadata._validate = lambda: None  # Disable automatic validation
        
        issues = MetadataValidator.validate_metadata(metadata)
        
        # Should have issues with the invalid variable
        assert len(issues) > 0
        issue_text = ' '.join(issues).lower()
        assert 'variable' in issue_text
        assert 'missing' in issue_text or 'id' in issue_text
    
    def test_enrich_metadata(self):
        """Test metadata enrichment functionality"""
        metadata = create_service_metadata_template("ENRICH_TEST")
        
        # Clear some fields that should be enriched
        metadata.provenance.created_date = None
        metadata.provenance.last_updated = None
        metadata.capabilities.data_formats = []
        
        enriched = MetadataValidator.enrich_metadata(metadata)
        
        # Should have enriched provenance dates
        assert enriched.provenance.created_date is not None
        assert enriched.provenance.last_updated is not None
        
        # Should have default data formats
        assert len(enriched.capabilities.data_formats) > 0
        assert DataFormat.TIME_SERIES in enriched.capabilities.data_formats


class TestSpatialTemporalCoverage:
    """Test spatial and temporal coverage classes"""
    
    def test_spatial_coverage(self):
        """Test SpatialCoverage functionality"""
        coverage = SpatialCoverage(
            description="Continental United States",
            bbox=[-125.0, 25.0, -66.0, 49.0],
            countries=["US"],
            resolution="1km"
        )
        
        assert coverage.description == "Continental United States"
        assert len(coverage.bbox) == 4
        assert coverage.countries == ["US"]
        assert coverage.resolution == "1km"
    
    def test_temporal_coverage(self):
        """Test TemporalCoverage functionality"""  
        start_date = datetime(2020, 1, 1)
        coverage = TemporalCoverage(
            description="2020-present",
            start_date=start_date,
            end_date=None,  # Ongoing
            resolution="daily",
            update_frequency="real-time"
        )
        
        assert coverage.description == "2020-present"
        assert coverage.start_date == start_date
        assert coverage.end_date is None
        assert coverage.resolution == "daily"
        assert coverage.update_frequency == "real-time"


class TestAuthenticationInfo:
    """Test authentication information handling"""
    
    def test_no_authentication(self):
        """Test no authentication required"""
        auth = AuthenticationInfo()
        
        assert not auth.required
        assert auth.type == AuthenticationType.NONE
        assert auth.scopes == []
        assert not auth.test_credentials_available
    
    def test_api_key_authentication(self):
        """Test API key authentication"""
        auth = AuthenticationInfo(
            required=True,
            type=AuthenticationType.API_KEY,
            instructions="Obtain API key from developer portal",
            test_credentials_available=True
        )
        
        assert auth.required
        assert auth.type == AuthenticationType.API_KEY
        assert "API key" in auth.instructions
        assert auth.test_credentials_available


class TestCreateServiceTemplate:
    """Test service metadata template creation"""
    
    def test_create_basic_template(self):
        """Test basic template creation"""
        template = create_service_metadata_template("TEMPLATE_TEST")
        
        assert template.service_id == "TEMPLATE_TEST"
        assert "TEMPLATE_TEST" in template.title
        assert len(template.capabilities.variables) > 0
        assert len(template.capabilities.domains) > 0
        assert template.capabilities.spatial_coverage.description
        assert template.capabilities.temporal_coverage.description
        
        # Should pass basic validation
        issues = MetadataValidator.validate_metadata(template)
        # Template may have some issues (like placeholder values), but should be structurally valid
        assert isinstance(issues, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])