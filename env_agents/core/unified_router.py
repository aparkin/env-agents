"""
Unified Environmental Data Router - Phase I Enhanced Version

Production-ready router integrating rich metadata, semantic discovery,
and resilient data fetching for environmental data services.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Union, Tuple
import pandas as pd
import logging
from datetime import datetime, timezone
from pathlib import Path

# New Phase I components  
from .service_registry import ServiceRegistry
from .discovery_engine import SemanticDiscoveryEngine, DiscoveryQuery, SearchResult
from .resilient_fetcher import ResilientDataFetcher, FetchResult, RetryConfig, FallbackConfig
from .metadata_schema import ServiceMetadata, create_service_metadata_template

# Legacy components (preserved for compatibility)
from .registry import RegistryManager
from .models import RequestSpec, CORE_COLUMNS, Geometry
from .errors import FetchError
from .ids import compute_observation_id as _cid

logger = logging.getLogger(__name__)


class UnifiedEnvRouter:
    """
    Production-ready unified router for environmental data services.
    
    Provides:
    - Rich service metadata and health monitoring
    - Semantic discovery and capability-based search
    - Resilient data fetching with fallback strategies
    - Backward compatibility with existing adapters
    """
    
    def __init__(self, 
                 base_dir: Optional[str] = None,
                 registry_path: Optional[Path] = None,
                 retry_config: Optional[RetryConfig] = None,
                 fallback_config: Optional[FallbackConfig] = None):
        
        # Initialize paths
        self.base_dir = base_dir or "."
        if registry_path is None:
            registry_path = Path(self.base_dir) / "registry" / "services.json"
        
        # Initialize core components
        self.service_registry = ServiceRegistry(registry_path)
        self.discovery_engine = SemanticDiscoveryEngine(self.service_registry)
        
        # Legacy registry for backward compatibility
        self.legacy_registry = RegistryManager(self.base_dir)
        
        # Adapter storage
        self.adapters: Dict[str, Any] = {}
        
        # Initialize resilient fetcher (will be configured after adapters are registered)
        self.retry_config = retry_config or RetryConfig()
        self.fallback_config = fallback_config or FallbackConfig()
        self._resilient_fetcher: Optional[ResilientDataFetcher] = None
        
        # Statistics tracking
        self._stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'discovery_requests': 0,
            'fallback_usage': 0
        }
    
    # ===================
    # Service Registration
    # ===================
    
    def register(self, adapter, metadata: Optional[ServiceMetadata] = None) -> bool:
        """
        Register an adapter with optional rich metadata.
        
        Args:
            adapter: Adapter instance implementing BaseAdapter interface
            metadata: Optional ServiceMetadata object. If not provided, 
                     will be auto-generated from adapter capabilities.
                     
        Returns:
            True if registration successful, False otherwise
        """
        try:
            # Set router reference (legacy compatibility)
            adapter._router_ref = self
            
            # Store adapter
            dataset = getattr(adapter, 'DATASET', adapter.__class__.__name__)
            self.adapters[dataset] = adapter
            
            # Generate or use provided metadata
            if metadata is None:
                metadata = self._generate_metadata_from_adapter(adapter)
            
            # Register with service registry
            success = self.service_registry.register_service(metadata)
            
            if success:
                logger.info(f"Successfully registered adapter: {dataset}")
                # Invalidate resilient fetcher to trigger rebuild with new adapter
                self._resilient_fetcher = None
            else:
                logger.warning(f"Failed to register metadata for adapter: {dataset}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to register adapter {getattr(adapter, 'DATASET', 'unknown')}: {e}")
            return False
    
    def register_multiple(self, adapters: List[Any], 
                         metadata_list: Optional[List[ServiceMetadata]] = None) -> Dict[str, bool]:
        """Register multiple adapters efficiently"""
        results = {}
        
        metadata_list = metadata_list or [None] * len(adapters)
        
        for adapter, metadata in zip(adapters, metadata_list):
            dataset = getattr(adapter, 'DATASET', adapter.__class__.__name__)
            results[dataset] = self.register(adapter, metadata)
            
        return results
    
    # ===================
    # Service Discovery  
    # ===================
    
    def list_adapters(self) -> List[str]:
        """List all registered adapter IDs"""
        return sorted(self.adapters.keys())
    
    def list_services(self, include_disabled: bool = False) -> List[str]:
        """List all registered service IDs with optional filtering"""
        return self.service_registry.list_services(include_disabled=include_disabled)
    
    def get_service_metadata(self, service_id: str) -> Optional[ServiceMetadata]:
        """Get complete metadata for a service"""
        return self.service_registry.get_service(service_id)
    
    def capabilities(self) -> Dict[str, Any]:
        """
        Get capabilities for all services (legacy compatible format).
        """
        caps = {}
        
        for service_id in self.list_services(include_disabled=True):
            try:
                metadata = self.service_registry.get_service(service_id)
                if metadata:
                    # Convert to legacy format
                    caps[service_id] = {
                        'variables': [
                            {
                                'id': var.id,
                                'canonical': var.canonical,
                                'name': var.name,
                                'description': var.description,
                                'unit': var.unit,
                                'domain': var.domain
                            }
                            for var in metadata.capabilities.variables
                        ],
                        'domains': metadata.capabilities.domains,
                        'spatial_coverage': metadata.capabilities.spatial_coverage.description,
                        'temporal_coverage': metadata.capabilities.temporal_coverage.description,
                        'provider': metadata.provider,
                        'license': metadata.license,
                        'authentication_required': metadata.authentication.required,
                        'reliability_score': metadata.quality_metrics.reliability_score,
                        'quality_score': metadata.get_quality_score()
                    }
                else:
                    # Fallback to adapter capabilities if metadata not found
                    adapter = self.adapters.get(service_id)
                    if adapter:
                        caps[service_id] = adapter.capabilities()
            except Exception as e:
                caps[service_id] = {"error": str(e)}
                
        return caps
    
    def discover_services(self, 
                         domain: Optional[str] = None,
                         variable: Optional[str] = None,
                         provider: Optional[str] = None,
                         min_quality_score: float = 0.0,
                         authentication_required: Optional[bool] = None,
                         spatial_coverage: Optional[str] = None) -> List[str]:
        """
        Discover services based on capabilities (simple interface).
        
        Returns list of service IDs matching criteria, sorted by quality.
        """
        self._stats['discovery_requests'] += 1
        
        return self.service_registry.discover_services(
            domain=domain,
            variable=variable,
            provider=provider,
            min_quality_score=min_quality_score,
            authentication_required=authentication_required,
            spatial_coverage=spatial_coverage
        )
    
    def search(self, query: Union[str, DiscoveryQuery]) -> List[SearchResult]:
        """
        Advanced semantic search for services.
        
        Args:
            query: Text query or structured DiscoveryQuery
            
        Returns:
            List of SearchResult objects with relevance scoring
        """
        self._stats['discovery_requests'] += 1
        return self.discovery_engine.discover(query)
    
    def discover_by_variable(self, variable: str, 
                           canonical_only: bool = False) -> List[SearchResult]:
        """Find services providing a specific variable"""
        return self.discovery_engine.discover_by_variable(variable, canonical_only)
    
    def discover_by_location(self, latitude: float, longitude: float,
                           radius_km: Optional[float] = None) -> List[SearchResult]:
        """Find services with data coverage for a location"""
        return self.discovery_engine.discover_by_location(latitude, longitude, radius_km)
    
    def discover_by_domain(self, domain: str) -> List[SearchResult]:
        """Find all services in a specific environmental domain"""
        return self.discovery_engine.discover_by_domain(domain)
    
    def suggest_variables(self, partial_name: str, 
                         limit: int = 10) -> List[Tuple[str, str, int]]:
        """Suggest variable names based on partial input"""
        return self.discovery_engine.suggest_variables(partial_name, limit)
    
    def get_capability_summary(self) -> Dict[str, Any]:
        """Get summary of all available capabilities"""
        return self.discovery_engine.get_capability_summary()
    
    # ===================
    # Data Fetching
    # ===================
    
    def fetch(self, dataset: str, spec: RequestSpec) -> pd.DataFrame:
        """
        Fetch data from a service with resilient error handling.
        
        Args:
            dataset: Service ID to fetch from
            spec: Request specification
            
        Returns:
            DataFrame with standardized schema and rich metadata
            
        Raises:
            FetchError: If fetch fails after all fallback attempts
        """
        self._stats['total_requests'] += 1
        
        # Initialize resilient fetcher if needed
        if self._resilient_fetcher is None:
            self._resilient_fetcher = ResilientDataFetcher(
                self.service_registry,
                self.adapters,
                self.retry_config,
                self.fallback_config
            )
        
        # Use resilient fetcher
        result = self._resilient_fetcher.fetch(dataset, spec)
        
        # Update statistics
        if result.is_success:
            self._stats['successful_requests'] += 1
        if result.fallbacks_used:
            self._stats['fallback_usage'] += 1
        
        # Handle result
        if not result.is_success:
            raise FetchError(f"Failed to fetch from {dataset}: {result.error_details}")
        
        if result.data is None:
            raise FetchError(f"No data returned from {dataset}")
        
        # Apply legacy post-processing for compatibility
        df = self._apply_legacy_processing(result.data, dataset, result)
        
        return df
    
    def fetch_resilient(self, dataset: str, spec: RequestSpec) -> FetchResult:
        """
        Fetch data with full resilient result information.
        
        Returns FetchResult with diagnostics, fallback info, and metadata.
        Useful for debugging and monitoring.
        """
        self._stats['total_requests'] += 1
        
        if self._resilient_fetcher is None:
            self._resilient_fetcher = ResilientDataFetcher(
                self.service_registry,
                self.adapters,
                self.retry_config,
                self.fallback_config
            )
        
        result = self._resilient_fetcher.fetch(dataset, spec)
        
        # Update statistics
        if result.is_success:
            self._stats['successful_requests'] += 1
        if result.fallbacks_used:
            self._stats['fallback_usage'] += 1
        
        # Apply legacy processing if data exists
        if result.data is not None:
            result.data = self._apply_legacy_processing(result.data, dataset, result)
        
        return result
    
    def fetch_multiple(self, requests: List[Tuple[str, RequestSpec]]) -> List[FetchResult]:
        """Fetch from multiple services with coordination"""
        if self._resilient_fetcher is None:
            self._resilient_fetcher = ResilientDataFetcher(
                self.service_registry,
                self.adapters,
                self.retry_config,
                self.fallback_config
            )
        
        results = self._resilient_fetcher.fetch_multiple(requests)
        
        # Update statistics
        for result in results:
            self._stats['total_requests'] += 1
            if result.is_success:
                self._stats['successful_requests'] += 1
            if result.fallbacks_used:
                self._stats['fallback_usage'] += 1
                
            # Apply legacy processing
            if result.data is not None:
                service_id = result.metadata.get('service', 'unknown')
                result.data = self._apply_legacy_processing(result.data, service_id, result)
        
        return results
    
    # ===================
    # Health & Monitoring
    # ===================
    
    def check_health(self) -> Dict[str, Any]:
        """Check overall system health"""
        stats = self.service_registry.get_service_statistics()
        unhealthy_services = []
        
        for service_id in self.list_services():
            health = self.service_registry.get_service_health(service_id)
            if health and health['reliability_score'] < 0.8:
                unhealthy_services.append(service_id)
        
        return {
            'status': 'healthy' if len(unhealthy_services) < stats['total_services'] * 0.2 else 'degraded',
            'total_services': stats['total_services'],
            'unhealthy_services': unhealthy_services,
            'avg_reliability': stats['avg_reliability_score'],
            'avg_quality': stats['avg_quality_score'],
            'router_stats': self._stats.copy()
        }
    
    def get_service_health(self, service_id: str) -> Optional[Dict[str, Any]]:
        """Get health status for a specific service"""
        return self.service_registry.get_service_health(service_id)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get router performance statistics"""
        stats = self._stats.copy()
        
        # Add success rates
        if stats['total_requests'] > 0:
            stats['success_rate'] = (stats['successful_requests'] / stats['total_requests']) * 100
            stats['fallback_usage_rate'] = (stats['fallback_usage'] / stats['total_requests']) * 100
        else:
            stats['success_rate'] = 0.0
            stats['fallback_usage_rate'] = 0.0
        
        # Add fetcher stats if available
        if self._resilient_fetcher:
            stats['fetcher_stats'] = self._resilient_fetcher.get_statistics()
            
        return stats
    
    # ===================
    # Legacy Compatibility
    # ===================
    
    def refresh_capabilities(self, *, extra_by_dataset: dict = None, 
                           write: bool = True) -> dict:
        """
        Legacy capability refresh with enhanced metadata updates.
        
        Updates both legacy registry and new service registry.
        """
        # Call legacy refresh first
        harvest = {}
        
        for dataset, adapter in self.adapters.items():
            try:
                extra = (extra_by_dataset or {}).get(dataset)
                caps = adapter.capabilities(extra) if extra else adapter.capabilities()
                
                harvest[dataset] = {
                    "dataset": caps.get("dataset", getattr(adapter, "DATASET", dataset)),
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "variables": caps.get("variables", []),
                    "attributes_schema": caps.get("attributes_schema", {}),
                    "rate_limits": caps.get("rate_limits", {}),
                    "notes": caps.get("notes", ""),
                }
                
                # Update service metadata in new registry
                metadata = self.service_registry.get_service(dataset)
                if metadata:
                    # Update provenance
                    metadata.provenance.last_validated = datetime.now()
                    metadata.provenance.validation_notes = "Refreshed via refresh_capabilities"
                    
                    # Update variables if available
                    if caps.get("variables"):
                        # Convert legacy format to VariableInfo objects
                        from .metadata_schema import VariableInfo
                        new_variables = []
                        for var in caps["variables"]:
                            if isinstance(var, dict):
                                new_variables.append(VariableInfo(
                                    id=var.get("id", ""),
                                    canonical=var.get("canonical"),
                                    name=var.get("name", ""),
                                    description=var.get("description", ""),
                                    unit=var.get("unit"),
                                    domain=var.get("domain")
                                ))
                        
                        if new_variables:
                            metadata.capabilities.variables = new_variables
                
            except Exception as e:
                harvest[dataset] = {"dataset": dataset, "error": str(e)}
                logger.error(f"Failed to refresh capabilities for {dataset}: {e}")
        
        # Write to legacy registry
        if write and hasattr(self.legacy_registry, 'write_harvest'):
            try:
                self.legacy_registry.write_harvest(harvest)
            except Exception as e:
                logger.warning(f"Failed to write legacy harvest: {e}")
        
        return harvest
    
    def _attach_meta(self, df: pd.DataFrame, adapter) -> pd.DataFrame:
        """Attach metadata attributes (legacy compatibility)"""
        try:
            df.attrs["schema"] = {"core_columns": CORE_COLUMNS}
            df.attrs["capabilities"] = adapter.capabilities()
            
            # Try to get legacy registry
            if hasattr(self.legacy_registry, 'merged'):
                df.attrs["variable_registry"] = self.legacy_registry.merged()
                
        except Exception as e:
            logger.warning(f"Failed to attach metadata attributes: {e}")
            
        return df
    
    def _apply_legacy_processing(self, df: pd.DataFrame, dataset: str, 
                               result: FetchResult) -> pd.DataFrame:
        """Apply legacy post-processing for backward compatibility"""
        try:
            # Ensure all core columns exist
            for col in CORE_COLUMNS:
                if col not in df.columns:
                    df[col] = None
            
            # Ensure retrieval timestamp
            if ("retrieval_timestamp" not in df.columns) or df["retrieval_timestamp"].isna().all():
                df["retrieval_timestamp"] = datetime.now(timezone.utc).isoformat()
            
            # Apply semantic processing if available
            try:
                if hasattr(self.legacy_registry, 'merged'):
                    registry = self.legacy_registry.merged()
                    from .term_broker import TermBroker
                    from .semantics import attach_semantics
                    
                    broker = TermBroker(registry)
                    df = attach_semantics(df, broker, dataset)
            except Exception as e:
                logger.debug(f"Semantic processing failed for {dataset}: {e}")
            
            # Ensure semantic columns exist
            for col in ("observed_property_uri", "unit_uri", "preferred_unit"):
                if col not in df.columns:
                    df[col] = None
            
            # Recompute observation IDs
            if "observation_id" not in df.columns or df["observation_id"].isna().any():
                df["observation_id"] = _cid(df)
            else:
                recomputed = _cid(df)
                if not recomputed.equals(df["observation_id"]):
                    df["observation_id"] = recomputed
            
            # Order columns (core first)
            core_first = [c for c in CORE_COLUMNS if c in df.columns]
            extras = [c for c in df.columns if c not in CORE_COLUMNS]
            df = df[core_first + extras]
            
            # Attach metadata attributes
            adapter = self.adapters.get(dataset)
            if adapter:
                df = self._attach_meta(df, adapter)
            
            # Add result diagnostics to attributes
            if hasattr(df, 'attrs'):
                df.attrs['fetch_result'] = {
                    'status': result.status.value,
                    'response_time': result.response_time,
                    'fallbacks_used': [fb.value for fb in result.fallbacks_used],
                    'diagnostics': result.diagnostics
                }
                
        except Exception as e:
            logger.warning(f"Legacy processing failed for {dataset}: {e}")
            
        return df
    
    def _generate_metadata_from_adapter(self, adapter) -> ServiceMetadata:
        """Generate ServiceMetadata from adapter capabilities"""
        dataset = getattr(adapter, 'DATASET', adapter.__class__.__name__)
        
        try:
            caps = adapter.capabilities()
            
            # Create basic metadata template
            metadata = create_service_metadata_template(dataset)
            
            # Populate from adapter attributes
            metadata.title = getattr(adapter, 'TITLE', f"{dataset} Data Service")
            metadata.description = getattr(adapter, 'DESCRIPTION', caps.get('description', 'Environmental data service'))
            metadata.provider = getattr(adapter, 'PROVIDER', 'Unknown Provider')
            metadata.source_url = getattr(adapter, 'SOURCE_URL', 'https://example.com')
            metadata.license = getattr(adapter, 'LICENSE', 'Unknown License')
            metadata.version = getattr(adapter, 'SOURCE_VERSION', '1.0')
            
            # Populate capabilities
            if caps.get('variables'):
                from .metadata_schema import VariableInfo
                variables = []
                for var in caps['variables']:
                    if isinstance(var, dict):
                        variables.append(VariableInfo(
                            id=var.get('id', ''),
                            canonical=var.get('canonical'),
                            name=var.get('name', ''),
                            description=var.get('description', ''),
                            unit=var.get('unit'),
                            domain=var.get('domain')
                        ))
                metadata.capabilities.variables = variables
            
            # Set domains from variables or adapter
            domains = caps.get('domains', [])
            if not domains and metadata.capabilities.variables:
                # Infer domains from variables
                domains = list(set(var.domain for var in metadata.capabilities.variables if var.domain))
            if not domains:
                domains = ['environmental']  # Default
            metadata.capabilities.domains = domains
            
            # Set coverage info
            spatial_desc = caps.get('spatial_coverage', 'Coverage information not available')
            metadata.capabilities.spatial_coverage.description = spatial_desc
            
            temporal_desc = caps.get('temporal_coverage', 'Temporal coverage not specified')
            metadata.capabilities.temporal_coverage.description = temporal_desc
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to generate metadata for {dataset}: {e}")
            # Return minimal template
            return create_service_metadata_template(dataset)