from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Union
import requests
import pandas as pd
from datetime import datetime, timezone, timedelta
from ..core.models import RequestSpec, CORE_COLUMNS
from ..core.utils_geo import centroid_from_geometry
from ..core.ids import compute_observation_id

class BaseAdapter(ABC):
    DATASET: str = "BASE"
    SOURCE_URL: str = ""
    SOURCE_VERSION: str = ""
    LICENSE: str = ""
    REQUIRES_API_KEY: bool = False
    SERVICE_TYPE: str = "service"  # "service" or "meta" for meta-services like Earth Engine

    # Filter capabilities - adapters override to declare supported filters
    SUPPORTED_FILTERS = {
        "domain": List[str],
        "spatial_coverage": List[str],
        "temporal_coverage": List[str], 
        "provider": List[str],
        "data_type": List[str]
    }

    def __init__(self):
        self._router_ref = None
        # Shared session with a friendly UA
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": f"env-agents/{self.DATASET}"})

    @abstractmethod
    def capabilities(self, asset_id: str = None, extra: dict | None = None) -> dict:
        """
        Return capabilities description.

        For unitary services: asset_id is ignored
        For meta-services:
        - asset_id=None: Return asset discovery (list of available assets)
        - asset_id="specific": Return detailed capabilities for that asset
        """
        ...

    @abstractmethod
    def _fetch_rows(self, spec: RequestSpec) -> List[Dict[str, Any]]:
        """Return list of dict rows matching core schema keys."""
        ...
    
    def discover(self, 
                 query: str = None,
                 limit: int = 20,
                 format: str = "summary", 
                 **filters) -> Dict[str, Any]:
        """
        Generic discovery method with standardized response format.
        
        Args:
            query: Text search within variables/assets
            limit: Maximum number of items to return  
            format: Response detail level ("summary" | "detailed" | "raw")
            **filters: Additional filters (domain, provider, etc.)
            
        Returns:
            Standardized discovery response dict
        """
        caps = self.capabilities()
        
        if format == "raw":
            return caps
        elif format == "detailed":
            return self._discovery_detailed(caps, query, limit, **filters)
        else:
            return self._discovery_summary(caps, query, limit, **filters)
    
    def get_filter_values(self) -> Dict[str, List[str]]:
        """
        Return actual filter values this adapter supports.
        
        Adapters should override to provide their specific filter values.
        """
        return {
            "domain": self._extract_domains(),
            "spatial_coverage": [getattr(self, 'SPATIAL_COVERAGE', 'Unknown')],
            "temporal_coverage": [getattr(self, 'TEMPORAL_COVERAGE', 'Unknown')],
            "provider": [getattr(self, 'PROVIDER', getattr(self, 'DATASET', 'Unknown'))],
            "data_type": ["historical"]  # Default assumption
        }
    
    def _extract_domains(self) -> List[str]:
        """Extract domains from capabilities or provide defaults."""
        caps = self.capabilities()
        
        # Try to extract from capabilities
        if 'domains' in caps:
            return caps['domains']
        
        # Try to extract from variables
        if 'variables' in caps:
            domains = set()
            for var in caps['variables']:
                if isinstance(var, dict) and 'domain' in var:
                    domains.add(var['domain'])
            if domains:
                return list(domains)
        
        # Default fallback
        return ['environmental']

    def _create_uniform_response(self,
                                service_type: str,
                                variables: List[Dict[str, Any]] = None,
                                assets: List[Dict[str, Any]] = None,
                                include_freshness: bool = True,
                                **additional_fields) -> Dict[str, Any]:
        """
        Create uniform response format for both unitary and meta services.

        Args:
            service_type: "unitary" or "meta"
            variables: List of variables (for unitary services or detailed meta-service responses)
            assets: List of assets (for meta-service discovery responses)
            include_freshness: Include metadata freshness information
            **additional_fields: Additional service-specific fields
        """
        response = {
            'dataset': getattr(self, 'DATASET', 'unknown'),
            'service_type': service_type,
            **additional_fields
        }

        if service_type == "unitary":
            response['variables'] = variables or []
        elif service_type == "meta":
            if assets is not None:
                # Asset discovery mode
                response['assets'] = assets
                response['total_assets'] = len(assets)
            else:
                # Asset-specific capabilities mode
                response['variables'] = variables or []

        # Add metadata freshness information
        if include_freshness:
            freshness = self._check_metadata_freshness("capabilities")
            response['metadata_freshness'] = {
                'last_updated': freshness['last_updated'].isoformat() if freshness['last_updated'] else None,
                'age_hours': freshness['age_hours'],
                'refresh_status': freshness['refresh_status'],
                'needs_refresh': freshness['needs_refresh']
            }

        return response

    def _check_metadata_freshness(self,
                                 metadata_type: str = "capabilities",
                                 max_age_hours: int = 168) -> Dict[str, Any]:
        """
        Check metadata freshness and provide refresh status.

        Args:
            metadata_type: Type of metadata ('capabilities', 'parameters', 'assets')
            max_age_hours: Maximum age in hours before refresh recommended (default: 7 days)

        Returns:
            {
                'is_fresh': bool,
                'last_updated': datetime,
                'age_hours': float,
                'needs_refresh': bool,
                'refresh_status': 'current' | 'stale' | 'expired',
                'next_refresh': datetime
            }
        """
        # Check if service has cached metadata with timestamps
        cache_key = f"_{metadata_type}_cache_timestamp"
        last_updated = getattr(self, cache_key, None)

        now = datetime.now()

        if last_updated is None:
            return {
                'is_fresh': False,
                'last_updated': None,
                'age_hours': float('inf'),
                'needs_refresh': True,
                'refresh_status': 'expired',
                'next_refresh': now
            }

        age_hours = (now - last_updated).total_seconds() / 3600
        is_fresh = age_hours < max_age_hours
        needs_refresh = age_hours > max_age_hours

        if age_hours < max_age_hours * 0.5:
            refresh_status = 'current'
        elif age_hours < max_age_hours:
            refresh_status = 'stale'
        else:
            refresh_status = 'expired'

        next_refresh = last_updated + timedelta(hours=max_age_hours)

        return {
            'is_fresh': is_fresh,
            'last_updated': last_updated,
            'age_hours': age_hours,
            'needs_refresh': needs_refresh,
            'refresh_status': refresh_status,
            'next_refresh': next_refresh
        }

    def _refresh_metadata(self,
                         metadata_type: str = "capabilities",
                         force_refresh: bool = False) -> Dict[str, Any]:
        """
        Uniform metadata refresh interface for scraped services.

        Args:
            metadata_type: Type of metadata to refresh
            force_refresh: Force refresh even if cache is fresh

        Returns:
            {
                'refreshed': bool,
                'method': 'cache_hit' | 'scraped' | 'api_call',
                'timestamp': datetime,
                'items_count': int,
                'errors': List[str]
            }
        """
        # Default implementation - services override for specific behavior
        freshness = self._check_metadata_freshness(metadata_type)

        if freshness['is_fresh'] and not force_refresh:
            return {
                'refreshed': False,
                'method': 'cache_hit',
                'timestamp': freshness['last_updated'],
                'items_count': 0,
                'errors': []
            }

        # Services should override this method to implement their refresh logic
        return {
            'refreshed': False,
            'method': 'not_implemented',
            'timestamp': datetime.now(),
            'items_count': 0,
            'errors': ['Service does not implement metadata refresh']
        }

    def _discovery_summary(self, caps: Dict[str, Any], query: str, limit: int, **filters) -> Dict[str, Any]:
        """
        Generate standardized summary response.
        
        This provides the core standardized format. Adapters can override for custom behavior.
        """
        variables = caps.get('variables', [])
        
        # Apply text query filtering
        filtered_variables = variables
        if query:
            filtered_variables = self._filter_variables_by_query(variables, query)
        
        # Apply additional filters (domain, etc.)
        if filters:
            filtered_variables = self._filter_variables_by_filters(filtered_variables, filters)
        
        # Limit results
        limited_variables = filtered_variables[:limit]
        
        return {
            "service_id": self.DATASET,
            "service_type": self.SERVICE_TYPE,
            "total_items": len(variables),
            "filtered_items": len(filtered_variables),
            
            "domains": self._extract_domains(),
            "provider": getattr(self, 'PROVIDER', self.DATASET),
            "spatial_coverage": getattr(self, 'SPATIAL_COVERAGE', 'Coverage information not available'),
            "temporal_coverage": getattr(self, 'TEMPORAL_COVERAGE', 'Temporal coverage not specified'),
            
            "items": self._format_items_summary(limited_variables),
            "has_more": len(filtered_variables) > limit,
            
            "usage_examples": self._generate_usage_examples(),
            "drill_down_options": self._generate_drill_down_options(query, filters),
            "query_suggestions": self._generate_query_suggestions(),
            
            "extra": self._generate_extra_info(caps, query, filters)
        }
    
    def _discovery_detailed(self, caps: Dict[str, Any], query: str, limit: int, **filters) -> Dict[str, Any]:
        """
        Generate detailed response with full variable information.
        """
        # Start with summary structure
        result = self._discovery_summary(caps, query, limit, **filters)
        
        # Add detailed variable information
        variables = caps.get('variables', [])
        filtered_variables = variables
        
        if query:
            filtered_variables = self._filter_variables_by_query(variables, query)
        if filters:
            filtered_variables = self._filter_variables_by_filters(filtered_variables, filters)
        
        # Provide more detailed items format
        result["items"] = self._format_items_detailed(filtered_variables[:limit])
        
        # Add detailed extra information
        if "extra" not in result:
            result["extra"] = {}
        result["extra"].update({
            "full_capabilities": caps,
            "applied_filters": filters,
            "search_query": query
        })
        
        return result
    
    def _filter_variables_by_query(self, variables: List[Any], query: str) -> List[Any]:
        """Filter variables by text query."""
        query_lower = query.lower()
        filtered = []
        
        for var in variables:
            var_text = str(var).lower()
            if isinstance(var, dict):
                # Search in common fields
                searchable_fields = ['id', 'name', 'description', 'canonical']
                var_text = ' '.join(str(var.get(field, '')).lower() for field in searchable_fields)
            
            if query_lower in var_text:
                filtered.append(var)
        
        return filtered
    
    def _filter_variables_by_filters(self, variables: List[Any], filters: Dict[str, Any]) -> List[Any]:
        """Apply domain/provider/etc filters to variables."""
        # Default implementation - adapters can override for sophisticated filtering
        if not filters:
            return variables
        
        filtered = []
        for var in variables:
            if isinstance(var, dict):
                # Check domain filter
                if 'domain' in filters:
                    var_domain = var.get('domain', '')
                    if isinstance(filters['domain'], str):
                        if filters['domain'].lower() not in var_domain.lower():
                            continue
                    elif isinstance(filters['domain'], list):
                        if not any(d.lower() in var_domain.lower() for d in filters['domain']):
                            continue
                
                # Add more filter types as needed
                
            filtered.append(var)
        
        return filtered
    
    def _format_items_summary(self, variables: List[Any]) -> List[Dict[str, Any]]:
        """Format variables for summary display."""
        formatted = []
        for var in variables:
            if isinstance(var, dict):
                formatted.append({
                    "id": var.get("id", ""),
                    "name": var.get("name", var.get("id", "")),
                    "unit": var.get("unit", ""),
                    "description": var.get("description", "")[:100] + ("..." if len(var.get("description", "")) > 100 else ""),
                    "domain": var.get("domain", "")
                })
            else:
                # Handle string variables
                formatted.append({
                    "id": str(var),
                    "name": str(var),
                    "unit": "",
                    "description": "",
                    "domain": ""
                })
        return formatted
    
    def _format_items_detailed(self, variables: List[Any]) -> List[Dict[str, Any]]:
        """Format variables for detailed display."""
        formatted = []
        for var in variables:
            if isinstance(var, dict):
                formatted.append(var.copy())  # Full variable info
            else:
                formatted.append({
                    "id": str(var),
                    "name": str(var), 
                    "unit": "",
                    "description": "",
                    "domain": ""
                })
        return formatted
    
    def _generate_usage_examples(self) -> List[str]:
        """Generate usage examples for this service."""
        examples = [
            f"router.fetch('{self.DATASET}', RequestSpec(geometry=point, variables=[...]))"
        ]
        
        # Add service-specific examples based on SERVICE_TYPE
        if self.SERVICE_TYPE == "meta":
            examples.append(
                f"router.fetch('{self.DATASET}', RequestSpec(geometry=bbox, extra={{'asset_id': 'ASSET_ID'}}))"
            )
        
        return examples
    
    def _generate_drill_down_options(self, query: str, filters: Dict[str, Any]) -> Dict[str, str]:
        """Generate drill-down exploration options."""
        options = {}
        
        if not query:
            options["search_variables"] = f"router.discover('{self.DATASET}', query='your_term')"
        
        domains = self._extract_domains()
        if len(domains) > 1:
            options["browse_domains"] = f"router.discover('{self.DATASET}', domain='domain_name')"
        
        if self.SERVICE_TYPE == "meta":
            options["browse_assets"] = f"router.discover('{self.DATASET}', format='detailed')"
        
        return options
    
    def _generate_query_suggestions(self) -> List[str]:
        """Generate helpful query suggestions."""
        # Default suggestions - adapters can override for service-specific suggestions
        return ["temperature", "precipitation", "quality", "concentration"]
    
    def _generate_extra_info(self, caps: Dict[str, Any], query: str, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate service-specific extra information."""
        return {}  # Adapters override for custom info

    def _prov(self, spec: RequestSpec, upstream: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "prov:wasGeneratedBy": {
                "software": "env-agents",
                "agent_id": f"{self.DATASET}@{self.SOURCE_VERSION}",
                "parameters": {
                    "geometry": spec.geometry.__dict__,
                    "time_range": spec.time_range,
                    "variables": spec.variables,
                    "depth_cm": spec.depth_cm,
                    "resolution": spec.resolution,
                    "extra": spec.extra,
                },
                "executed_at": datetime.now(timezone.utc).isoformat(),
            },
            "prov:used": [upstream],
        }

    def fetch(self, spec: RequestSpec) -> pd.DataFrame:
        rows = self._fetch_rows(spec)
        df = pd.DataFrame(rows)
    
        # Defaults
        if "dataset" not in df.columns:         df["dataset"] = self.DATASET
        if "source_url" not in df.columns:      df["source_url"] = self.SOURCE_URL
        if "source_version" not in df.columns:  df["source_version"] = self.SOURCE_VERSION
        if "license" not in df.columns:         df["license"] = self.LICENSE
        if "geometry_type" not in df.columns:   df["geometry_type"] = spec.geometry.type
    
        # Fill lat/lon if missing via centroid
        if "latitude" not in df.columns or "longitude" not in df.columns:
            lat, lon = centroid_from_geometry(spec.geometry.type, spec.geometry.coordinates)
            if "latitude"  not in df.columns: df["latitude"]  = lat
            if "longitude" not in df.columns: df["longitude"] = lon
    
        # Ensure attributes/provenance columns exist (unique dicts per row)
        # Use object dtype and assign individually to avoid unhashable type errors
        if "attributes" not in df.columns:  
            df["attributes"] = None
            for i in range(len(df)):
                df.at[i, "attributes"] = {}
        if "provenance" not in df.columns:  
            df["provenance"] = None  
            for i in range(len(df)):
                df.at[i, "provenance"] = {}
    
        # Ensure all core columns exist
        for col in CORE_COLUMNS:
            if col not in df.columns:
                df[col] = None
    
        # Fill retrieval timestamp if missing
        if "retrieval_timestamp" not in df.columns or df["retrieval_timestamp"].isna().all():
            df["retrieval_timestamp"] = datetime.now(timezone.utc).isoformat()

        # temporal_coverage defaults if missing/empty
        if "temporal_coverage" not in df.columns or df["temporal_coverage"].isna().all():
            # infer per-row from 'time'
            def _infer_cov(t):
                try:
                    dt = pd.to_datetime(t, utc=True)
                    return "instantaneous" if (getattr(dt, "hour", 0) or getattr(dt, "minute", 0) or getattr(dt, "second", 0)) else "daily"
                except Exception:
                    return None
            df["temporal_coverage"] = df.get("time").map(_infer_cov)
    
        # Canonical observation_id (overwrite any adapter-provided value)
        df["observation_id"] = compute_observation_id(df)
    
        return df[CORE_COLUMNS]
