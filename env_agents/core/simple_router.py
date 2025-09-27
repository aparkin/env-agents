# env_agents/core/simple_router.py

from __future__ import annotations
import pandas as pd
from typing import Dict, Any, List, Union, Tuple
from .registry import RegistryManager
from .models import RequestSpec, CORE_COLUMNS
from .errors import FetchError
from datetime import datetime, timezone
from .ids import compute_observation_id as _cid


class SimpleEnvRouter:
    """
    Simplified Environmental Data Router with 3-method interface:
    1. register() - Register environmental data adapters
    2. discover() - Unified discovery for services and capabilities  
    3. fetch() - Fetch environmental data from services
    
    Designed as a plugin foundation for environmental data services
    with generic, service-agnostic discovery patterns.
    """
    
    def __init__(self, base_dir: str):
        """
        Initialize router with base directory for configuration.
        
        Args:
            base_dir: Base directory for registry and configuration files
        """
        self.base_dir = base_dir
        self.registry = RegistryManager(base_dir)
        self.adapters: Dict[str, Any] = {}
    
    # ==========================================
    # 1. REGISTER - Setup environmental services
    # ==========================================
    
    def register(self, adapter) -> bool:
        """
        Register an environmental data adapter.
        
        Args:
            adapter: Adapter instance implementing BaseAdapter interface
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            # Set router reference for adapter
            adapter._router_ref = self
            
            # Store adapter by dataset name
            dataset = getattr(adapter, 'DATASET', adapter.__class__.__name__)
            self.adapters[dataset] = adapter
            
            return True
            
        except Exception as e:
            # Log error but don't raise - keep router operational
            print(f"Warning: Failed to register adapter {getattr(adapter, 'DATASET', 'unknown')}: {e}")
            return False
    
    # ==========================================
    # 2. DISCOVER - Unified service discovery
    # ==========================================
    
    def discover(self, 
                 query: str = None,
                 limit: int = 20,
                 format: str = "summary",
                 service: str = None,
                 **filters) -> Union[List[str], Dict[str, Any]]:
        """
        Unified discovery method for environmental services and capabilities.
        
        This method provides a single interface for all discovery needs:
        - List all services
        - Search for specific variables/capabilities
        - Filter by domain, provider, coverage, etc.
        - Drill down into specific services
        
        Args:
            query: Text search within service variables/assets (optional)
            limit: Maximum number of items to return per service (default: 20)
            format: Response detail level - "summary" | "detailed" | "raw" (default: "summary")  
            service: Specific service to query (optional - if provided, only query that service)
            **filters: Additional filters:
                - domain: Environmental domain(s) - "climate", "hydrology", "air_quality", etc.
                - provider: Data provider(s) - "NASA", "USGS", "EPA", etc.
                - spatial_coverage: Geographic coverage - "global", "US", "regional", etc.
                - temporal_coverage: Time coverage - "historical", "realtime", "forecast", etc.
                - data_type: Data type - "observations", "model", "satellite", etc.
        
        Returns:
            If no arguments provided: List of registered service IDs
            Otherwise: Dict with discovery results in standardized format
            
        Examples:
            # List all services
            services = router.discover()
            # ['NASA_POWER', 'USGS_NWIS', 'WQP', 'EARTH_ENGINE', ...]
            
            # Search for temperature data
            results = router.discover(query="temperature")
            # Returns services that provide temperature data with usage examples
            
            # Find climate services 
            results = router.discover(domain="climate", format="detailed")
            # Returns detailed info for all climate-related services
            
            # Drill down into specific service
            results = router.discover(service="WQP", query="nitrogen", limit=50)
            # Returns WQP's nitrogen-related variables
            
            # Get full capabilities
            results = router.discover(format="detailed")
            # Returns comprehensive capabilities for all services
        """
        
        # Simple case: no parameters = list service IDs
        if not any([query, service, filters]) and format == "summary":
            return list(self.adapters.keys())
        
        # Advanced case: discovery with filtering and service queries
        return self._discovery_query(
            query=query,
            limit=limit, 
            format=format,
            service=service,
            **filters
        )
    
    def _discovery_query(self, 
                        query: str = None,
                        limit: int = 20,
                        format: str = "summary",
                        service: str = None,
                        **filters) -> Dict[str, Any]:
        """
        Execute advanced discovery query with filtering and aggregation.
        
        This method implements the core discovery logic:
        1. Filter services based on provided criteria
        2. Query each matching service for its discovery response
        3. Aggregate results in standardized format
        """
        
        # Determine which services to query
        target_services = {}
        if service:
            # Query specific service
            if service in self.adapters:
                target_services[service] = self.adapters[service]
            else:
                raise ValueError(f"Service '{service}' not registered. Available: {list(self.adapters.keys())}")
        else:
            # Query all services that match filters
            for service_id, adapter in self.adapters.items():
                if self._service_matches_filters(adapter, filters):
                    target_services[service_id] = adapter
        
        # Query each target service for discovery results
        service_results = {}
        for service_id, adapter in target_services.items():
            try:
                # Each adapter handles its own discovery complexity
                result = adapter.discover(query=query, limit=limit, format=format, **filters)
                service_results[service_id] = result
            except Exception as e:
                # Don't let one service failure break entire discovery
                service_results[service_id] = {
                    "service_id": service_id,
                    "error": f"Discovery failed: {str(e)}"
                }
        
        # Aggregate and return results
        return self._aggregate_discovery_results(
            service_results=service_results,
            query=query,
            filters=filters,
            format=format
        )
    
    def _service_matches_filters(self, adapter, filters: Dict[str, Any]) -> bool:
        """
        Check if service matches provided filters using generic approach.
        
        This method queries each adapter for its filter values and checks
        for matches without any hardcoded service-specific logic.
        """
        if not filters:
            return True
        
        try:
            # Get filter values that this adapter supports
            adapter_filters = adapter.get_filter_values()
            
            # Check each provided filter
            for filter_key, filter_value in filters.items():
                if filter_key in adapter_filters:
                    adapter_values = adapter_filters[filter_key]
                    
                    # Handle string and list filter values
                    if isinstance(filter_value, str):
                        if filter_value not in adapter_values:
                            return False
                    elif isinstance(filter_value, list):
                        if not any(v in adapter_values for v in filter_value):
                            return False
                else:
                    # Adapter doesn't support this filter - no match
                    return False
            
            return True
            
        except Exception:
            # If filter checking fails, include the service (fail open)
            return True
    
    def _aggregate_discovery_results(self, 
                                   service_results: Dict[str, Dict[str, Any]],
                                   query: str,
                                   filters: Dict[str, Any],
                                   format: str) -> Dict[str, Any]:
        """
        Aggregate discovery results from multiple services into standardized response.
        
        This provides the top-level aggregated view that agents can use for
        capability discovery and intent detection.
        """
        
        # Calculate aggregated statistics
        total_services = len(service_results)
        total_items = 0
        total_filtered_items = 0
        all_domains = set()
        all_providers = set()
        
        successful_services = []
        failed_services = []
        
        for service_id, result in service_results.items():
            # Handle case where result might be a string instead of dict
            if isinstance(result, str):
                failed_services.append({"service": service_id, "error": f"Invalid response format: got string '{result[:100]}'"})
            elif not isinstance(result, dict):
                failed_services.append({"service": service_id, "error": f"Invalid response format: got {type(result).__name__}"})
            elif "error" in result:
                failed_services.append({"service": service_id, "error": result["error"]})
            elif isinstance(result, dict):
                successful_services.append(service_id)
                total_items += result.get("total_items", 0)
                total_filtered_items += result.get("filtered_items", 0)

                # Collect domains and providers
                domains = result.get("domains")
                if domains and isinstance(domains, (list, set)):
                    all_domains.update(domains)
                provider = result.get("provider")
                if provider and isinstance(provider, str):
                    all_providers.add(provider)
            else:
                failed_services.append({"service": service_id, "error": f"Unexpected response type: {type(result)}"})
        
        # Generate aggregated response
        aggregated = {
            # Query context
            "query": query,
            "applied_filters": filters,
            "response_format": format,
            
            # Service summary
            "total_services": total_services,
            "successful_services": len(successful_services),
            "failed_services": len(failed_services),
            
            # Capability summary
            "total_items_across_services": total_items,
            "filtered_items_across_services": total_filtered_items,
            "available_domains": sorted(list(all_domains)),
            "available_providers": sorted(list(all_providers)),
            
            # Individual service results
            "services": successful_services,
            "service_results": {k: v for k, v in service_results.items() if isinstance(v, dict) and "error" not in v},
            
            # Error reporting
            "errors": failed_services if failed_services else None,
            
            # Discovery guidance
            "usage_guidance": self._generate_aggregated_usage_guidance(service_results, query, filters),
            "available_filters": self._get_available_filters()
        }
        
        return aggregated
    
    def _generate_aggregated_usage_guidance(self, 
                                          service_results: Dict[str, Dict[str, Any]], 
                                          query: str, 
                                          filters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate usage guidance based on discovery results."""
        guidance = {
            "next_steps": [],
            "example_fetches": [],
            "refinement_options": []
        }
        
        successful_results = {k: v for k, v in service_results.items() if "error" not in v}
        
        if not successful_results:
            guidance["next_steps"] = [
                "No services matched your criteria",
                "Try broadening your search or removing filters",
                "Use router.discover() to see all available services"
            ]
        else:
            # Generate next steps based on results
            if not query:
                guidance["next_steps"].append("Try searching with query parameter: router.discover(query='your_term')")
            
            if len(successful_results) == 1:
                service_id = list(successful_results.keys())[0]
                result = successful_results[service_id]
                if result.get("usage_examples"):
                    guidance["example_fetches"] = result["usage_examples"][:2]
            else:
                # Multiple services - show variety
                for service_id, result in list(successful_results.items())[:3]:
                    if result.get("usage_examples"):
                        guidance["example_fetches"].append(result["usage_examples"][0])
            
            # Suggest refinement options
            all_domains = set()
            for result in successful_results.values():
                if result.get("domains"):
                    all_domains.update(result["domains"])
            
            if len(all_domains) > 1:
                guidance["refinement_options"].append(
                    f"Filter by domain: router.discover(domain='{list(all_domains)[0]}')"
                )
        
        return guidance
    
    def _get_available_filters(self) -> Dict[str, List[str]]:
        """
        Get all available filter values across registered services.
        
        This helps agents understand what filtering options are available.
        """
        all_filters = {}
        
        for service_id, adapter in self.adapters.items():
            try:
                adapter_filters = adapter.get_filter_values()
                for filter_key, filter_values in adapter_filters.items():
                    if filter_key not in all_filters:
                        all_filters[filter_key] = set()
                    all_filters[filter_key].update(filter_values)
            except Exception:
                # Skip services that don't support filter introspection
                continue
        
        # Convert sets to sorted lists
        return {k: sorted(list(v)) for k, v in all_filters.items()}
    
    # ==========================================
    # 3. FETCH - Get environmental data
    # ==========================================
    
    def fetch(self, dataset: str, spec: RequestSpec) -> pd.DataFrame:
        """
        Fetch environmental data from a registered service.
        
        This method provides a uniform interface for data retrieval across
        all environmental services, with standardized post-processing.
        
        Args:
            dataset: Service ID to fetch from (from discover() results)
            spec: Request specification with geometry, time range, variables, etc.
            
        Returns:
            DataFrame with standardized schema and rich metadata
            
        Raises:
            FetchError: If service not found or data fetch fails
            
        Examples:
            # Fetch temperature from NASA POWER
            data = router.fetch('NASA_POWER', RequestSpec(
                geometry=Geometry(type='point', coordinates=[-122.4, 37.8]),
                time_range=('2024-01-01', '2024-01-31'),
                variables=['T2M']
            ))
            
            # Fetch water quality from WQP
            data = router.fetch('WQP', RequestSpec(
                geometry=Geometry(type='bbox', coordinates=[...]),
                variables=['Temperature', 'pH']
            ))
            
            # Fetch from Earth Engine meta-service
            data = router.fetch('EARTH_ENGINE', RequestSpec(
                geometry=Geometry(type='bbox', coordinates=[...]),
                extra={'asset_id': 'MODIS/061/MOD11A1'}
            ))
        """
        
        # Check if service is registered
        if dataset not in self.adapters:
            available = list(self.adapters.keys())
            raise FetchError(f"Service '{dataset}' not registered. Available services: {available}")
        
        adapter = self.adapters[dataset]
        
        try:
            # 1. Fetch raw data from adapter
            df = adapter.fetch(spec)
            
            # 2. Apply standardized post-processing
            df = self._apply_standard_processing(df, adapter, spec)
            
            # 3. Attach metadata for analysis tools
            df = self._attach_metadata(df, adapter)
            
            return df
            
        except Exception as e:
            raise FetchError(f"Failed to fetch data from {dataset}: {str(e)}")
    
    def _apply_standard_processing(self, df: pd.DataFrame, adapter, spec: RequestSpec) -> pd.DataFrame:
        """
        Apply standardized post-processing to ensure consistent data format.
        
        This ensures all environmental data follows the same schema and patterns
        regardless of the source service.
        """
        
        # Ensure all core columns exist
        for col in CORE_COLUMNS:
            if col not in df.columns:
                df[col] = None
        
        # Ensure retrieval timestamp 
        if ("retrieval_timestamp" not in df.columns) or df["retrieval_timestamp"].isna().all():
            df["retrieval_timestamp"] = datetime.now(timezone.utc).isoformat()
        
        # Apply semantic processing if registry available
        try:
            registry = self.registry.merged()
            from .term_broker import TermBroker
            from .semantics import attach_semantics
            broker = TermBroker(registry)
            df = attach_semantics(df, broker, adapter.DATASET)
        except Exception:
            # Semantic processing is optional - continue without it
            pass
        
        # Ensure semantic columns exist even if processing failed
        for col in ("observed_property_uri", "unit_uri", "preferred_unit"):
            if col not in df.columns:
                df[col] = None
        
        # Recompute observation IDs for consistency
        if "observation_id" not in df.columns or df["observation_id"].isna().any():
            df["observation_id"] = _cid(df)
        else:
            recomputed = _cid(df)
            if not recomputed.equals(df["observation_id"]):
                df["observation_id"] = recomputed
        
        # Order columns (core schema first, extras after)
        core_first = [c for c in CORE_COLUMNS if c in df.columns]
        extras = [c for c in df.columns if c not in CORE_COLUMNS]
        df = df[core_first + extras]
        
        return df
    
    def _attach_metadata(self, df: pd.DataFrame, adapter) -> pd.DataFrame:
        """
        Attach metadata attributes for analysis tools and provenance.
        
        This provides rich metadata that analysis tools like pandas, geopandas,
        and visualization libraries can use.
        """
        try:
            # Schema information
            df.attrs["schema"] = {"core_columns": CORE_COLUMNS}
            
            # Service capabilities
            df.attrs["capabilities"] = adapter.capabilities()
            
            # Variable registry (if available)
            try:
                df.attrs["variable_registry"] = self.registry.merged()
            except Exception:
                pass
            
            # Service information
            df.attrs["service_info"] = {
                "dataset": adapter.DATASET,
                "provider": getattr(adapter, 'PROVIDER', adapter.DATASET),
                "source_url": adapter.SOURCE_URL,
                "service_type": adapter.SERVICE_TYPE,
                "license": adapter.LICENSE
            }
            
        except Exception:
            # Don't fail fetch if metadata attachment fails
            pass
        
        return df
    
    # ==========================================
    # Convenience Methods (Legacy Compatibility)
    # ==========================================
    
    def list_services(self) -> List[str]:
        """
        List all registered service IDs.
        
        Convenience method equivalent to: router.discover()
        """
        return self.discover()
    
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get detailed capabilities for all services.
        
        Convenience method equivalent to: router.discover(format="detailed")
        """
        return self.discover(format="detailed")
    
    def search(self, query: str, limit: int = 20) -> Dict[str, Any]:
        """
        Search across all services for variables/capabilities.
        
        Convenience method equivalent to: router.discover(query=query, limit=limit)
        """
        return self.discover(query=query, limit=limit)
    
    # ==========================================
    # Registry Management (Advanced)
    # ==========================================
    
    def refresh_capabilities(self, *, extra_by_dataset: dict = None, write: bool = True) -> dict:
        """
        Refresh service capabilities and update registry.
        
        This method updates the semantic registry with current service capabilities.
        Useful for maintenance and keeping semantic mappings current.
        
        Args:
            extra_by_dataset: Optional extra parameters per dataset
            write: Whether to persist changes to registry files
            
        Returns:
            Dict of harvested capabilities per service
        """
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
                
                # Add optional fields if present
                for field in ["statistics", "units", "discovery_status", "capabilities_schema_version"]:
                    if field in caps:
                        harvest[dataset][field] = caps[field]
                        
            except Exception as e:
                harvest[dataset] = {"dataset": dataset, "error": str(e)}
        
        # Write to registry if requested
        if write:
            try:
                self.registry.write_harvest(harvest)
                # Refresh registry cache
                if hasattr(self.registry, "reload"):
                    self.registry.reload()
                elif hasattr(self.registry, "invalidate_cache"):
                    self.registry.invalidate_cache()
            except Exception as e:
                print(f"Warning: Failed to write harvest to registry: {e}")
        
        return harvest