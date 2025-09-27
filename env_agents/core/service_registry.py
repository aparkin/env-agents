"""
Service Registry for Environmental Data Services

Centralized registry managing service metadata, health monitoring,
and discovery capabilities for all environmental data sources.
"""

from typing import Dict, List, Optional, Set, Any, Tuple
from pathlib import Path
import json
import logging
from datetime import datetime, timedelta
from collections import defaultdict

from .metadata_schema import (
    ServiceMetadata, 
    MetadataValidator,
    VariableInfo,
    QualityMetrics,
    ProvenanceInfo,
    RegistrySource
)

logger = logging.getLogger(__name__)


class ServiceRegistry:
    """
    Centralized registry for environmental data service metadata.
    
    Manages service registration, validation, health monitoring,
    and discovery capabilities across all adapters.
    """
    
    def __init__(self, registry_path: Optional[Path] = None):
        self.registry_path = registry_path or Path("registry/services.json")
        self._services: Dict[str, ServiceMetadata] = {}
        self._service_index = ServiceIndex()
        self._load_registry()
        
    def register_service(self, metadata: ServiceMetadata, validate: bool = True) -> bool:
        """
        Register a new service or update existing service metadata.
        
        Args:
            metadata: Complete service metadata
            validate: Whether to validate metadata before registration
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            if validate:
                issues = MetadataValidator.validate_metadata(metadata)
                if issues:
                    logger.warning(f"Service {metadata.service_id} has validation issues: {issues}")
                    return False
            
            # Update provenance
            if metadata.service_id in self._services:
                metadata.provenance.last_updated = datetime.now()
                logger.info(f"Updated service: {metadata.service_id}")
            else:
                metadata.provenance.created_date = datetime.now()
                metadata.provenance.last_updated = datetime.now()
                logger.info(f"Registered new service: {metadata.service_id}")
            
            self._services[metadata.service_id] = metadata
            self._service_index.index_service(metadata)
            self._save_registry()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to register service {metadata.service_id}: {e}")
            return False
    
    def get_service(self, service_id: str) -> Optional[ServiceMetadata]:
        """Get service metadata by ID"""
        return self._services.get(service_id)
    
    def list_services(self, include_disabled: bool = False) -> List[str]:
        """List all registered service IDs"""
        if include_disabled:
            return list(self._services.keys())
        
        # Filter out services with very low reliability scores (but allow new services with 0.0)
        return [
            service_id for service_id, metadata in self._services.items()
            if metadata.quality_metrics.reliability_score >= 0.0  # Changed from 0.1 to 0.0
        ]
    
    def get_all_metadata(self) -> Dict[str, ServiceMetadata]:
        """Get all service metadata"""
        return self._services.copy()
    
    def discover_services(
        self,
        domain: Optional[str] = None,
        variable: Optional[str] = None,
        provider: Optional[str] = None,
        min_quality_score: float = 0.0,
        authentication_required: Optional[bool] = None,
        spatial_coverage: Optional[str] = None
    ) -> List[str]:
        """
        Discover services based on capabilities and requirements.
        
        Args:
            domain: Filter by domain (water, air, soil, climate, etc.)
            variable: Filter by variable name or canonical variable
            provider: Filter by data provider organization
            min_quality_score: Minimum overall quality score (0.0-1.0)
            authentication_required: Filter by authentication requirement
            spatial_coverage: Filter by spatial coverage description
            
        Returns:
            List of matching service IDs sorted by quality score
        """
        return self._service_index.search(
            domain=domain,
            variable=variable,
            provider=provider,
            min_quality_score=min_quality_score,
            authentication_required=authentication_required,
            spatial_coverage=spatial_coverage
        )
    
    def get_service_health(self, service_id: str) -> Optional[Dict[str, Any]]:
        """Get service health and quality metrics"""
        metadata = self._services.get(service_id)
        if not metadata:
            return None
            
        return {
            'service_id': service_id,
            'reliability_score': metadata.quality_metrics.reliability_score,
            'data_quality_score': metadata.quality_metrics.data_quality_score,
            'overall_quality_score': metadata.get_quality_score(),
            'completeness_score': metadata.get_completeness_score(),
            'last_successful_request': metadata.quality_metrics.last_successful_request,
            'last_failed_request': metadata.quality_metrics.last_failed_request,
            'total_requests': metadata.quality_metrics.total_requests,
            'successful_requests': metadata.quality_metrics.successful_requests,
            'error_patterns': metadata.quality_metrics.error_patterns
        }
    
    def update_service_health(self, service_id: str, success: bool, 
                            response_time: float, error: Optional[str] = None):
        """Update service health metrics based on request result"""
        metadata = self._services.get(service_id)
        if metadata:
            metadata.update_quality_metrics(success, response_time, error)
            self._save_registry()
    
    def get_variables_by_domain(self, domain: str) -> List[Tuple[str, VariableInfo]]:
        """Get all variables available for a specific domain"""
        variables = []
        for service_id, metadata in self._services.items():
            if domain in metadata.capabilities.domains:
                for var in metadata.capabilities.variables:
                    if var.domain == domain:
                        variables.append((service_id, var))
        return variables
    
    def get_service_statistics(self) -> Dict[str, Any]:
        """Get overall registry statistics"""
        total_services = len(self._services)
        if total_services == 0:
            return {'total_services': 0}
            
        # Calculate aggregated metrics
        reliability_scores = [m.quality_metrics.reliability_score for m in self._services.values()]
        quality_scores = [m.quality_metrics.data_quality_score for m in self._services.values()]
        completeness_scores = [m.get_completeness_score() for m in self._services.values()]
        
        # Count by domain
        domain_counts = defaultdict(int)
        for metadata in self._services.values():
            for domain in metadata.capabilities.domains:
                domain_counts[domain] += 1
        
        # Count by provider
        provider_counts = defaultdict(int)
        for metadata in self._services.values():
            provider_counts[metadata.provider] += 1
        
        # Authentication stats
        auth_required = sum(1 for m in self._services.values() if m.authentication.required)
        
        return {
            'total_services': total_services,
            'avg_reliability_score': sum(reliability_scores) / len(reliability_scores),
            'avg_quality_score': sum(quality_scores) / len(quality_scores),
            'avg_completeness_score': sum(completeness_scores) / len(completeness_scores),
            'services_requiring_auth': auth_required,
            'auth_percentage': (auth_required / total_services) * 100,
            'domains': dict(domain_counts),
            'providers': dict(provider_counts),
            'healthy_services': sum(1 for s in reliability_scores if s >= 0.8),
            'unhealthy_services': sum(1 for s in reliability_scores if s < 0.5)
        }
    
    def export_capabilities_summary(self) -> Dict[str, Any]:
        """Export a summary of all service capabilities for external use"""
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_services': len(self._services),
            'services': {}
        }
        
        for service_id, metadata in self._services.items():
            summary['services'][service_id] = metadata.to_dict()
            
        return summary
    
    def validate_all_services(self) -> Dict[str, List[str]]:
        """Validate all registered services and return issues"""
        validation_results = {}
        
        for service_id, metadata in self._services.items():
            issues = MetadataValidator.validate_metadata(metadata)
            if issues:
                validation_results[service_id] = issues
                
        return validation_results
    
    def cleanup_stale_services(self, days_threshold: int = 90) -> List[str]:
        """Remove services that haven't been updated recently"""
        cutoff_date = datetime.now() - timedelta(days=days_threshold)
        stale_services = []
        
        for service_id, metadata in list(self._services.items()):
            last_updated = metadata.provenance.last_updated
            if last_updated and last_updated < cutoff_date:
                # Check if service has been completely inactive
                if (metadata.quality_metrics.total_requests == 0 or
                    metadata.quality_metrics.reliability_score < 0.1):
                    stale_services.append(service_id)
                    del self._services[service_id]
                    logger.info(f"Removed stale service: {service_id}")
        
        if stale_services:
            self._service_index.rebuild(list(self._services.values()))
            self._save_registry()
            
        return stale_services
    
    def _load_registry(self):
        """Load service registry from disk"""
        if not self.registry_path.exists():
            logger.info(f"Registry file not found: {self.registry_path}")
            return
            
        try:
            with open(self.registry_path, 'r') as f:
                data = json.load(f)
            
            for service_data in data.get('services', []):
                try:
                    # Convert from dict to ServiceMetadata object
                    metadata = self._dict_to_metadata(service_data)
                    self._services[metadata.service_id] = metadata
                    self._service_index.index_service(metadata)
                except Exception as e:
                    logger.error(f"Failed to load service from registry: {e}")
                    
            logger.info(f"Loaded {len(self._services)} services from registry")
            
        except Exception as e:
            logger.error(f"Failed to load registry: {e}")
    
    def _save_registry(self):
        """Save service registry to disk"""
        try:
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'version': '1.0',
                'updated': datetime.now().isoformat(),
                'services': [self._metadata_to_dict(m) for m in self._services.values()]
            }
            
            with open(self.registry_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")
    
    def _dict_to_metadata(self, data: Dict[str, Any]) -> ServiceMetadata:
        """Convert dictionary to ServiceMetadata object"""
        # This is a simplified conversion - in practice you'd need
        # more sophisticated deserialization
        # For now, we'll use the dict data directly
        pass
    
    def _metadata_to_dict(self, metadata: ServiceMetadata) -> Dict[str, Any]:
        """Convert ServiceMetadata to dictionary"""
        return metadata.to_dict()


class ServiceIndex:
    """
    Search index for efficient service discovery.
    
    Maintains multiple indexes for fast lookup by domain, variable,
    provider, and other service characteristics.
    """
    
    def __init__(self):
        self.domain_index: Dict[str, Set[str]] = defaultdict(set)
        self.variable_index: Dict[str, Set[str]] = defaultdict(set)  
        self.provider_index: Dict[str, Set[str]] = defaultdict(set)
        self.auth_index: Dict[bool, Set[str]] = {True: set(), False: set()}
        self.quality_index: List[Tuple[float, str]] = []  # (score, service_id)
        
    def index_service(self, metadata: ServiceMetadata):
        """Add or update service in search indexes"""
        service_id = metadata.service_id
        
        # Remove from existing indexes
        self._remove_from_indexes(service_id)
        
        # Domain index
        for domain in metadata.capabilities.domains:
            self.domain_index[domain.lower()].add(service_id)
        
        # Variable index (by ID, canonical, and name)
        for var in metadata.capabilities.variables:
            if var.id:
                self.variable_index[var.id.lower()].add(service_id)
            if var.canonical:
                self.variable_index[var.canonical.lower()].add(service_id)
            if var.name:
                self.variable_index[var.name.lower()].add(service_id)
        
        # Provider index
        self.provider_index[metadata.provider.lower()].add(service_id)
        
        # Authentication index
        self.auth_index[metadata.authentication.required].add(service_id)
        
        # Quality index
        quality_score = metadata.get_quality_score()
        self.quality_index.append((quality_score, service_id))
        self.quality_index.sort(reverse=True)  # Keep sorted by quality desc
    
    def search(
        self,
        domain: Optional[str] = None,
        variable: Optional[str] = None,
        provider: Optional[str] = None,
        min_quality_score: float = 0.0,
        authentication_required: Optional[bool] = None,
        spatial_coverage: Optional[str] = None
    ) -> List[str]:
        """Search for services matching criteria"""
        
        # Start with all services
        candidates = set(service_id for _, service_id in self.quality_index)
        
        # Apply filters
        if domain:
            domain_matches = self.domain_index.get(domain.lower(), set())
            candidates &= domain_matches
            
        if variable:
            variable_matches = self.variable_index.get(variable.lower(), set())
            candidates &= variable_matches
            
        if provider:
            provider_matches = self.provider_index.get(provider.lower(), set())
            candidates &= provider_matches
            
        if authentication_required is not None:
            auth_matches = self.auth_index[authentication_required]
            candidates &= auth_matches
        
        # Apply quality filter and return in quality order
        results = []
        for quality_score, service_id in self.quality_index:
            if service_id in candidates and quality_score >= min_quality_score:
                results.append(service_id)
                
        return results
    
    def rebuild(self, services: List[ServiceMetadata]):
        """Rebuild all indexes from scratch"""
        self.domain_index.clear()
        self.variable_index.clear()
        self.provider_index.clear()
        self.auth_index = {True: set(), False: set()}
        self.quality_index.clear()
        
        for metadata in services:
            self.index_service(metadata)
    
    def _remove_from_indexes(self, service_id: str):
        """Remove service from all indexes"""
        # Remove from domain index
        for domain_services in self.domain_index.values():
            domain_services.discard(service_id)
            
        # Remove from variable index
        for variable_services in self.variable_index.values():
            variable_services.discard(service_id)
            
        # Remove from provider index  
        for provider_services in self.provider_index.values():
            provider_services.discard(service_id)
            
        # Remove from auth index
        for auth_services in self.auth_index.values():
            auth_services.discard(service_id)
            
        # Remove from quality index
        self.quality_index = [(score, sid) for score, sid in self.quality_index 
                             if sid != service_id]


class ServiceHealthTracker:
    """
    Monitor and track service health metrics over time.
    
    Provides aggregated health reporting and alerting capabilities
    for service reliability monitoring.
    """
    
    def __init__(self, registry: ServiceRegistry):
        self.registry = registry
        
    def get_all_service_health(self) -> Dict[str, Dict[str, Any]]:
        """Get health status for all services"""
        health_status = {}
        
        for service_id in self.registry.list_services(include_disabled=True):
            health = self.registry.get_service_health(service_id)
            if health:
                health_status[service_id] = health
                
        return health_status
    
    def get_unhealthy_services(self, reliability_threshold: float = 0.8) -> List[str]:
        """Get services with reliability below threshold"""
        unhealthy = []
        
        for service_id in self.registry.list_services(include_disabled=True):
            health = self.registry.get_service_health(service_id)
            if health and health['reliability_score'] < reliability_threshold:
                unhealthy.append(service_id)
                
        return unhealthy
    
    def generate_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report"""
        stats = self.registry.get_service_statistics()
        unhealthy = self.get_unhealthy_services()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'overall_statistics': stats,
            'unhealthy_services': unhealthy,
            'recommendations': self._generate_recommendations(stats, unhealthy)
        }
    
    def _generate_recommendations(self, stats: Dict[str, Any], 
                                unhealthy: List[str]) -> List[str]:
        """Generate recommendations based on health metrics"""
        recommendations = []
        
        if stats['avg_reliability_score'] < 0.8:
            recommendations.append("Overall service reliability is below recommended threshold")
            
        if len(unhealthy) > stats['total_services'] * 0.2:
            recommendations.append("More than 20% of services are unhealthy - investigate common issues")
            
        if stats['avg_completeness_score'] < 0.7:
            recommendations.append("Service metadata completeness needs improvement")
            
        return recommendations