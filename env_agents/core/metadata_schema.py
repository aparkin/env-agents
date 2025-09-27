"""
Rich Metadata Framework for Environmental Data Services

Provides standardized metadata schema, validation, and quality scoring
for all environmental data sources in the env-agents framework.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DataFormat(Enum):
    """Standard data format types"""
    TIME_SERIES = "time_series"
    RASTER = "raster" 
    POINT = "point"
    VECTOR = "vector"
    TABLE = "table"


class AuthenticationType(Enum):
    """Authentication types"""
    NONE = "none"
    API_KEY = "api_key"
    OAUTH = "oauth"
    SERVICE_ACCOUNT = "service_account"
    BASIC_AUTH = "basic_auth"


class RegistrySource(Enum):
    """Sources of metadata registration"""
    MANUAL = "manual"          # Hand-curated by maintainers
    HARVESTED = "harvested"    # Auto-discovered from service APIs
    INFERRED = "inferred"      # Machine-generated from patterns
    COMMUNITY = "community"    # User-contributed


@dataclass
class VariableInfo:
    """Structured information about a data variable"""
    id: str                           # Native parameter ID
    canonical: Optional[str] = None   # Canonical variable name (e.g., "water:discharge_cfs")
    name: str = ""                   # Human-readable name
    description: str = ""            # Detailed description
    unit: Optional[str] = None       # Native unit
    canonical_unit: Optional[str] = None  # Preferred canonical unit
    data_type: str = "float"         # Data type (float, int, string, bool)
    domain: Optional[str] = None     # Thematic domain (water, soil, air, climate)
    min_value: Optional[float] = None # Expected minimum value
    max_value: Optional[float] = None # Expected maximum value
    quality_flags: List[str] = field(default_factory=list)  # Available QC flags


@dataclass
class SpatialCoverage:
    """Spatial coverage information"""
    description: str                  # "Global", "Continental US", "Europe"
    bbox: Optional[List[float]] = None  # [west, south, east, north] in WGS84
    countries: List[str] = field(default_factory=list)  # ISO country codes
    resolution: Optional[str] = None  # "1km", "30m", "point-based"


@dataclass
class TemporalCoverage:
    """Temporal coverage information"""
    description: str                  # "1990-present", "2000-2023"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None  # None for ongoing
    resolution: Optional[str] = None  # "daily", "hourly", "monthly"
    update_frequency: Optional[str] = None  # "real-time", "daily", "annual"


@dataclass
class ServiceCapabilities:
    """Describes what a service can provide"""
    domains: List[str]                # ['water', 'soil', 'air', 'climate']
    variables: List[VariableInfo]     # Structured variable descriptions
    spatial_coverage: SpatialCoverage
    temporal_coverage: TemporalCoverage
    data_formats: List[DataFormat]    # Supported output formats
    max_spatial_extent: Optional[float] = None  # Max query area in sq km
    max_temporal_range: Optional[int] = None    # Max time range in days
    max_results_per_query: Optional[int] = None


@dataclass
class AuthenticationInfo:
    """Authentication requirements"""
    required: bool = False
    type: AuthenticationType = AuthenticationType.NONE
    endpoint: Optional[str] = None    # Auth endpoint URL
    scopes: List[str] = field(default_factory=list)
    instructions: str = ""            # How to obtain credentials
    test_credentials_available: bool = False


@dataclass  
class RateLimiting:
    """Rate limiting information"""
    requests_per_second: Optional[float] = None
    requests_per_minute: Optional[int] = None
    requests_per_hour: Optional[int] = None
    requests_per_day: Optional[int] = None
    concurrent_requests: Optional[int] = None
    burst_allowance: Optional[int] = None


@dataclass
class QualityMetrics:
    """Service quality and reliability metrics"""
    reliability_score: float = 0.0      # 0.0-1.0 based on historical success rate
    data_quality_score: float = 0.0     # 0.0-1.0 based on completeness/accuracy  
    response_time_p50: Optional[float] = None  # Median response time in seconds
    response_time_p95: Optional[float] = None  # 95th percentile response time
    last_successful_request: Optional[datetime] = None
    last_failed_request: Optional[datetime] = None
    total_requests: int = 0
    successful_requests: int = 0
    error_patterns: List[str] = field(default_factory=list)  # Common error types


@dataclass
class ProvenanceInfo:
    """Provenance and maintenance information"""
    registry_source: RegistrySource = RegistrySource.MANUAL
    created_date: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    last_validated: Optional[datetime] = None
    validation_notes: str = ""
    maintainer: Optional[str] = None
    contact_email: Optional[str] = None
    documentation_url: Optional[str] = None


@dataclass
class ServiceMetadata:
    """Complete standardized metadata for an environmental data service"""
    
    # Core Identity
    service_id: str                   # Unique identifier
    title: str                        # Human-readable title
    description: str                  # Detailed description
    provider: str                     # Data provider organization
    
    # Technical Details
    source_url: str                   # Primary API/data URL
    license: str                      # Data license (CC0, CC-BY, proprietary, etc.)
    capabilities: ServiceCapabilities # Service capabilities (required)
    
    # Optional Technical Details
    version: str = "1.0"              # Service/data version
    authentication: AuthenticationInfo = field(default_factory=AuthenticationInfo)
    rate_limiting: Optional[RateLimiting] = None
    
    # Quality & Reliability  
    quality_metrics: QualityMetrics = field(default_factory=QualityMetrics)
    
    # Provenance
    provenance: ProvenanceInfo = field(default_factory=ProvenanceInfo)
    
    # Technical Configuration
    base_url: Optional[str] = None    # Base API URL if different from source_url
    timeout_seconds: int = 30         # Default request timeout
    retry_config: Dict[str, Any] = field(default_factory=dict)
    custom_headers: Dict[str, str] = field(default_factory=dict)
    
    # Additional metadata
    tags: List[str] = field(default_factory=list)  # Searchable tags
    related_services: List[str] = field(default_factory=list)  # Related service IDs
    notes: str = ""                   # Additional notes
    
    def __post_init__(self):
        """Validate metadata after initialization"""
        self._validate()
        
    def _validate(self):
        """Validate metadata completeness and consistency"""
        required_fields = [
            'service_id', 'title', 'description', 'provider', 
            'source_url', 'license'
        ]
        
        for field_name in required_fields:
            value = getattr(self, field_name)
            if not value or (isinstance(value, str) and not value.strip()):
                raise ValueError(f"Required field '{field_name}' is empty or missing")
        
        # Validate capabilities
        if not self.capabilities.domains:
            raise ValueError("At least one domain must be specified")
            
        if not self.capabilities.variables:
            raise ValueError("At least one variable must be specified")
    
    def get_completeness_score(self) -> float:
        """Calculate metadata completeness score (0.0-1.0)"""
        total_fields = 0
        completed_fields = 0
        
        # Core fields (weight: 3)
        core_fields = ['service_id', 'title', 'description', 'provider', 'source_url', 'license']
        for field in core_fields:
            total_fields += 3
            if getattr(self, field) and getattr(self, field).strip():
                completed_fields += 3
        
        # Capabilities (weight: 2)
        cap_fields = ['domains', 'variables', 'spatial_coverage', 'temporal_coverage']
        for field in cap_fields:
            total_fields += 2
            value = getattr(self.capabilities, field, None)
            if value:
                if isinstance(value, list) and value:
                    completed_fields += 2
                elif hasattr(value, 'description') and value.description:
                    completed_fields += 2
                elif isinstance(value, str) and value.strip():
                    completed_fields += 2
        
        # Optional fields (weight: 1)
        optional_fields = ['version', 'base_url', 'notes']
        for field in optional_fields:
            total_fields += 1
            value = getattr(self, field, None)
            if value and str(value).strip():
                completed_fields += 1
        
        # Authentication info (weight: 1)
        total_fields += 1
        if self.authentication and self.authentication.type != AuthenticationType.NONE:
            completed_fields += 1
            
        return min(completed_fields / total_fields, 1.0) if total_fields > 0 else 0.0
    
    def get_quality_score(self) -> float:
        """Get overall quality score combining completeness and reliability"""
        completeness = self.get_completeness_score()
        reliability = self.quality_metrics.reliability_score
        data_quality = self.quality_metrics.data_quality_score
        
        # Weighted average: 40% completeness, 40% reliability, 20% data quality
        return (0.4 * completeness) + (0.4 * reliability) + (0.2 * data_quality)
    
    def update_quality_metrics(self, success: bool, response_time: float, error: Optional[str] = None):
        """Update quality metrics based on a request result"""
        self.quality_metrics.total_requests += 1
        
        if success:
            self.quality_metrics.successful_requests += 1
            self.quality_metrics.last_successful_request = datetime.now()
        else:
            self.quality_metrics.last_failed_request = datetime.now()
            if error and error not in self.quality_metrics.error_patterns:
                self.quality_metrics.error_patterns.append(error)
        
        # Update reliability score (exponential moving average)
        if self.quality_metrics.total_requests > 0:
            current_success_rate = self.quality_metrics.successful_requests / self.quality_metrics.total_requests
            # Smooth update: 90% existing score + 10% current rate
            self.quality_metrics.reliability_score = (
                0.9 * self.quality_metrics.reliability_score + 0.1 * current_success_rate
            )
        
        # Update response time metrics (simplified moving average)
        if success and response_time > 0:
            if self.quality_metrics.response_time_p50 is None:
                self.quality_metrics.response_time_p50 = response_time
            else:
                # Simple moving average
                self.quality_metrics.response_time_p50 = (
                    0.9 * self.quality_metrics.response_time_p50 + 0.1 * response_time
                )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'service_id': self.service_id,
            'title': self.title,
            'description': self.description,
            'provider': self.provider,
            'source_url': self.source_url,
            'license': self.license,
            'version': self.version,
            'domains': self.capabilities.domains,
            'variables': [
                {
                    'id': var.id,
                    'canonical': var.canonical,
                    'name': var.name,
                    'description': var.description,
                    'unit': var.unit,
                    'domain': var.domain
                }
                for var in self.capabilities.variables
            ],
            'spatial_coverage': self.capabilities.spatial_coverage.description,
            'temporal_coverage': self.capabilities.temporal_coverage.description,
            'authentication_required': self.authentication.required,
            'authentication_type': self.authentication.type.value if self.authentication else 'none',
            'reliability_score': self.quality_metrics.reliability_score,
            'data_quality_score': self.quality_metrics.data_quality_score,
            'completeness_score': self.get_completeness_score(),
            'overall_quality_score': self.get_quality_score(),
            'last_updated': self.provenance.last_updated.isoformat() if self.provenance.last_updated else None,
            'tags': self.tags,
            'notes': self.notes
        }


class MetadataValidator:
    """Validates and enriches service metadata"""
    
    @staticmethod
    def validate_metadata(metadata: ServiceMetadata) -> List[str]:
        """Validate metadata and return list of issues"""
        issues = []
        
        # Check required fields
        if not metadata.service_id or not metadata.service_id.strip():
            issues.append("service_id is required")
            
        if not metadata.title or not metadata.title.strip():
            issues.append("title is required")
            
        if not metadata.description or len(metadata.description.strip()) < 20:
            issues.append("description must be at least 20 characters")
            
        if not metadata.source_url or not metadata.source_url.startswith(('http://', 'https://')):
            issues.append("source_url must be a valid HTTP(S) URL")
            
        # Check capabilities
        if not metadata.capabilities.domains:
            issues.append("at least one domain must be specified")
            
        if not metadata.capabilities.variables:
            issues.append("at least one variable must be specified")
        
        # Check variable quality
        for var in metadata.capabilities.variables:
            if not var.id:
                issues.append(f"variable missing id")
            if not var.name:
                issues.append(f"variable '{var.id}' missing name")
            if not var.description:
                issues.append(f"variable '{var.id}' missing description")
        
        return issues
    
    @staticmethod
    def enrich_metadata(metadata: ServiceMetadata, existing_data: Optional[Dict[str, Any]] = None) -> ServiceMetadata:
        """Enrich metadata with inferred or default values"""
        
        # Set default provenance info if not provided
        if not metadata.provenance.created_date:
            metadata.provenance.created_date = datetime.now()
            
        if not metadata.provenance.last_updated:
            metadata.provenance.last_updated = datetime.now()
        
        # Infer domains from variables if domains are empty
        if not metadata.capabilities.domains and metadata.capabilities.variables:
            inferred_domains = set()
            for var in metadata.capabilities.variables:
                if var.domain:
                    inferred_domains.add(var.domain)
                elif var.canonical:
                    # Infer from canonical name (e.g., "water:discharge_cfs" -> "water")
                    if ':' in var.canonical:
                        domain = var.canonical.split(':')[0]
                        inferred_domains.add(domain)
            
            if inferred_domains:
                metadata.capabilities.domains = list(inferred_domains)
                logger.info(f"Inferred domains for {metadata.service_id}: {inferred_domains}")
        
        # Set default data formats if not specified
        if not metadata.capabilities.data_formats:
            metadata.capabilities.data_formats = [DataFormat.TIME_SERIES, DataFormat.POINT]
        
        return metadata


def create_service_metadata_template(service_id: str) -> ServiceMetadata:
    """Create a template ServiceMetadata object for a new service"""
    return ServiceMetadata(
        service_id=service_id,
        title=f"{service_id} Data Service",
        description="Description needed - please update with service details",
        provider="Provider needed",
        source_url="https://example.com",
        license="License needed",
        capabilities=ServiceCapabilities(
            domains=["domain_needed"],
            variables=[
                VariableInfo(
                    id="example_var",
                    name="Example Variable",
                    description="Variable description needed"
                )
            ],
            spatial_coverage=SpatialCoverage(description="Coverage description needed"),
            temporal_coverage=TemporalCoverage(description="Temporal coverage needed"),
            data_formats=[DataFormat.TIME_SERIES]
        )
    )