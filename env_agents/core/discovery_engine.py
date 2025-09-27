"""
Semantic Discovery Engine for Environmental Data Services

Advanced service discovery using semantic matching, capability analysis,
and intelligent ranking for environmental data source selection.
"""

from typing import Dict, List, Optional, Set, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import re
import logging
from collections import defaultdict, Counter
from datetime import datetime

from .service_registry import ServiceRegistry
from .metadata_schema import ServiceMetadata, VariableInfo

logger = logging.getLogger(__name__)


class SearchScope(Enum):
    """Scope of discovery search"""
    ALL = "all"
    GOVERNMENT = "government" 
    EARTH_ENGINE = "earth_engine"
    AUTHENTICATED = "authenticated"
    PUBLIC = "public"


class MatchType(Enum):
    """Type of semantic match"""
    EXACT = "exact"
    CANONICAL = "canonical"
    SYNONYM = "synonym"
    FUZZY = "fuzzy"
    DOMAIN = "domain"
    SPATIAL = "spatial"
    TEMPORAL = "temporal"


@dataclass
class SearchResult:
    """Result from service discovery search"""
    service_id: str
    metadata: ServiceMetadata
    relevance_score: float
    matches: List[Tuple[MatchType, str, float]]  # (type, matched_text, score)
    reason: str
    
    def __post_init__(self):
        """Calculate overall relevance score from individual matches"""
        if not self.relevance_score and self.matches:
            # Weight different match types
            weights = {
                MatchType.EXACT: 1.0,
                MatchType.CANONICAL: 0.9,
                MatchType.SYNONYM: 0.8,
                MatchType.FUZZY: 0.6,
                MatchType.DOMAIN: 0.4,
                MatchType.SPATIAL: 0.3,
                MatchType.TEMPORAL: 0.2
            }
            
            total_score = sum(weights.get(match_type, 0.5) * score 
                            for match_type, _, score in self.matches)
            self.relevance_score = min(total_score, 1.0)


@dataclass  
class DiscoveryQuery:
    """Structured query for service discovery"""
    # Text-based search
    query_text: Optional[str] = None
    variables: List[str] = field(default_factory=list)
    
    # Domain filters
    domains: List[str] = field(default_factory=list)
    providers: List[str] = field(default_factory=list)
    
    # Capability requirements
    authentication_required: Optional[bool] = None
    min_quality_score: float = 0.0
    min_reliability: float = 0.0
    
    # Geographic constraints
    spatial_coverage: Optional[str] = None
    bbox: Optional[List[float]] = None  # [west, south, east, north]
    
    # Temporal constraints
    temporal_coverage: Optional[str] = None
    date_range: Optional[Tuple[str, str]] = None
    
    # Result constraints
    max_results: int = 20
    scope: SearchScope = SearchScope.ALL


class SemanticDiscoveryEngine:
    """
    Advanced discovery engine for environmental data services.
    
    Provides semantic search, capability matching, and intelligent
    ranking to help users find the most relevant data sources.
    """
    
    def __init__(self, registry: ServiceRegistry):
        self.registry = registry
        self._variable_aliases = self._build_variable_aliases()
        self._domain_keywords = self._build_domain_keywords()
        
    def discover(self, query: Union[str, DiscoveryQuery]) -> List[SearchResult]:
        """
        Discover services based on query.
        
        Args:
            query: Text query or structured DiscoveryQuery object
            
        Returns:
            List of SearchResult objects ranked by relevance
        """
        # Convert string query to DiscoveryQuery
        if isinstance(query, str):
            query = DiscoveryQuery(query_text=query)
            
        # Get candidate services
        candidates = self._get_candidates(query)
        
        # Score and rank candidates
        results = []
        for service_id in candidates:
            metadata = self.registry.get_service(service_id)
            if not metadata:
                continue
                
            result = self._score_service(metadata, query)
            if result.relevance_score > 0:
                results.append(result)
        
        # Sort by relevance and apply result limit
        results.sort(key=lambda r: r.relevance_score, reverse=True)
        return results[:query.max_results]
    
    def discover_by_variable(self, variable: str, 
                           canonical_only: bool = False) -> List[SearchResult]:
        """
        Discover services that provide a specific variable.
        
        Args:
            variable: Variable name, ID, or canonical form
            canonical_only: Only match canonical variable names
            
        Returns:
            List of services providing the variable, ranked by quality
        """
        query = DiscoveryQuery(
            variables=[variable],
            min_quality_score=0.1
        )
        
        results = []
        for service_id, metadata in self.registry.get_all_metadata().items():
            matches = self._match_variables([variable], metadata.capabilities.variables, 
                                          canonical_only=canonical_only)
            
            if matches:
                relevance_score = max(score for _, _, score in matches)
                result = SearchResult(
                    service_id=service_id,
                    metadata=metadata,
                    relevance_score=relevance_score,
                    matches=matches,
                    reason=f"Provides variable: {variable}"
                )
                results.append(result)
        
        # Sort by quality score for variable-specific searches
        results.sort(key=lambda r: (r.relevance_score, r.metadata.get_quality_score()), 
                    reverse=True)
        return results
    
    def discover_by_location(self, latitude: float, longitude: float, 
                           radius_km: Optional[float] = None) -> List[SearchResult]:
        """
        Discover services with data coverage for a specific location.
        
        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees  
            radius_km: Search radius in kilometers (optional)
            
        Returns:
            List of services with spatial coverage, ranked by relevance
        """
        query = DiscoveryQuery(
            bbox=[longitude - 0.1, latitude - 0.1, longitude + 0.1, latitude + 0.1],
            min_quality_score=0.1
        )
        
        results = []
        for service_id, metadata in self.registry.get_all_metadata().items():
            # Check spatial coverage
            coverage = metadata.capabilities.spatial_coverage
            if self._location_in_coverage(latitude, longitude, coverage):
                result = SearchResult(
                    service_id=service_id,
                    metadata=metadata,
                    relevance_score=0.8,  # High relevance for spatial match
                    matches=[(MatchType.SPATIAL, f"({latitude}, {longitude})", 0.8)],
                    reason=f"Covers location: {latitude:.3f}, {longitude:.3f}"
                )
                results.append(result)
        
        results.sort(key=lambda r: r.metadata.get_quality_score(), reverse=True)
        return results
    
    def discover_by_domain(self, domain: str) -> List[SearchResult]:
        """
        Discover all services for a specific environmental domain.
        
        Args:
            domain: Environmental domain (water, air, soil, climate, etc.)
            
        Returns:
            List of services in the domain, ranked by quality
        """
        services = self.registry.discover_services(domain=domain)
        
        results = []
        for service_id in services:
            metadata = self.registry.get_service(service_id)
            if metadata:
                result = SearchResult(
                    service_id=service_id,
                    metadata=metadata,
                    relevance_score=0.7,
                    matches=[(MatchType.DOMAIN, domain, 0.7)],
                    reason=f"Domain: {domain}"
                )
                results.append(result)
        
        results.sort(key=lambda r: r.metadata.get_quality_score(), reverse=True)
        return results
    
    def suggest_variables(self, partial_name: str, limit: int = 10) -> List[Tuple[str, str, int]]:
        """
        Suggest variable names based on partial input.
        
        Args:
            partial_name: Partial variable name
            limit: Maximum suggestions to return
            
        Returns:
            List of (variable_name, service_id, occurrence_count) tuples
        """
        partial_lower = partial_name.lower()
        suggestions = defaultdict(int)
        
        for service_id, metadata in self.registry.get_all_metadata().items():
            for var in metadata.capabilities.variables:
                # Check variable ID, name, and canonical form
                candidates = [var.id, var.name, var.canonical]
                candidates = [c for c in candidates if c]  # Remove None values
                
                for candidate in candidates:
                    if candidate and partial_lower in candidate.lower():
                        suggestions[(candidate, service_id)] += 1
        
        # Sort by occurrence count and name similarity
        sorted_suggestions = sorted(
            suggestions.items(),
            key=lambda x: (x[1], -len(x[0][0])),  # Count desc, length asc
            reverse=True
        )
        
        return [(var_name, service_id, count) 
                for (var_name, service_id), count in sorted_suggestions[:limit]]
    
    def get_capability_summary(self) -> Dict[str, Any]:
        """Get summary of all available capabilities across services"""
        all_domains = set()
        all_variables = set()
        variable_counts = Counter()
        provider_counts = Counter()
        
        for metadata in self.registry.get_all_metadata().values():
            all_domains.update(metadata.capabilities.domains)
            provider_counts[metadata.provider] += 1
            
            for var in metadata.capabilities.variables:
                all_variables.add(var.canonical or var.name or var.id)
                if var.domain:
                    variable_counts[var.domain] += 1
        
        return {
            'total_domains': len(all_domains),
            'domains': sorted(all_domains),
            'total_variables': len(all_variables),
            'variables_by_domain': dict(variable_counts.most_common()),
            'providers': dict(provider_counts.most_common()),
            'most_common_variables': self._get_most_common_variables(10)
        }
    
    def _get_candidates(self, query: DiscoveryQuery) -> Set[str]:
        """Get initial candidate services based on query filters"""
        candidates = set(self.registry.list_services())
        
        # Apply scope filter
        if query.scope != SearchScope.ALL:
            scoped_candidates = set()
            for service_id in candidates:
                metadata = self.registry.get_service(service_id)
                if metadata and self._matches_scope(metadata, query.scope):
                    scoped_candidates.add(service_id)
            candidates = scoped_candidates
        
        # Apply domain filter
        if query.domains:
            domain_candidates = set()
            for domain in query.domains:
                domain_candidates.update(
                    self.registry.discover_services(domain=domain)
                )
            candidates &= domain_candidates
        
        # Apply provider filter
        if query.providers:
            provider_candidates = set()
            for provider in query.providers:
                provider_candidates.update(
                    self.registry.discover_services(provider=provider)
                )
            candidates &= provider_candidates
            
        # Apply quality filters
        if query.min_quality_score > 0 or query.min_reliability > 0:
            quality_candidates = set()
            for service_id in candidates:
                metadata = self.registry.get_service(service_id)
                if metadata:
                    if (metadata.get_quality_score() >= query.min_quality_score and
                        metadata.quality_metrics.reliability_score >= query.min_reliability):
                        quality_candidates.add(service_id)
            candidates = quality_candidates
            
        return candidates
    
    def _score_service(self, metadata: ServiceMetadata, 
                      query: DiscoveryQuery) -> SearchResult:
        """Score a service against a discovery query"""
        matches = []
        
        # Text query matching
        if query.query_text:
            text_matches = self._match_text_query(query.query_text, metadata)
            matches.extend(text_matches)
        
        # Variable matching
        if query.variables:
            var_matches = self._match_variables(query.variables, 
                                              metadata.capabilities.variables)
            matches.extend(var_matches)
        
        # Spatial matching
        if query.bbox or query.spatial_coverage:
            spatial_matches = self._match_spatial(query, metadata.capabilities.spatial_coverage)
            matches.extend(spatial_matches)
            
        # Temporal matching
        if query.date_range or query.temporal_coverage:
            temporal_matches = self._match_temporal(query, metadata.capabilities.temporal_coverage)
            matches.extend(temporal_matches)
        
        # Calculate relevance score
        relevance_score = 0.0
        if matches:
            # Weight matches by type and combine
            match_weights = {
                MatchType.EXACT: 1.0,
                MatchType.CANONICAL: 0.9,
                MatchType.SYNONYM: 0.7,
                MatchType.FUZZY: 0.5,
                MatchType.DOMAIN: 0.3,
                MatchType.SPATIAL: 0.4,
                MatchType.TEMPORAL: 0.2
            }
            
            weighted_score = sum(match_weights.get(match_type, 0.3) * score 
                               for match_type, _, score in matches)
            relevance_score = min(weighted_score / len(matches), 1.0)
            
            # Boost score by service quality
            quality_boost = metadata.get_quality_score() * 0.2
            relevance_score = min(relevance_score + quality_boost, 1.0)
        
        # Generate reason
        reason = self._generate_reason(matches, metadata)
        
        return SearchResult(
            service_id=metadata.service_id,
            metadata=metadata,
            relevance_score=relevance_score,
            matches=matches,
            reason=reason
        )
    
    def _match_text_query(self, query_text: str, 
                         metadata: ServiceMetadata) -> List[Tuple[MatchType, str, float]]:
        """Match text query against service metadata"""
        matches = []
        query_lower = query_text.lower()
        query_words = set(query_lower.split())
        
        # Check service title and description
        title_words = set(metadata.title.lower().split())
        desc_words = set(metadata.description.lower().split())
        
        title_overlap = len(query_words & title_words) / len(query_words) if query_words else 0
        if title_overlap > 0:
            matches.append((MatchType.EXACT, f"title: {metadata.title}", title_overlap))
            
        desc_overlap = len(query_words & desc_words) / len(query_words) if query_words else 0
        if desc_overlap > 0.3:  # Threshold for description matches
            matches.append((MatchType.FUZZY, "description", desc_overlap))
        
        # Check domain keywords
        for domain in metadata.capabilities.domains:
            domain_keywords = self._domain_keywords.get(domain, set())
            keyword_overlap = len(query_words & domain_keywords) / len(query_words) if query_words else 0
            if keyword_overlap > 0:
                matches.append((MatchType.DOMAIN, f"domain: {domain}", keyword_overlap))
        
        # Check variable names and descriptions
        for variable in metadata.capabilities.variables:
            if variable.name:
                var_words = set(variable.name.lower().split())
                var_overlap = len(query_words & var_words) / len(query_words) if query_words else 0
                if var_overlap > 0:
                    matches.append((MatchType.FUZZY, f"variable: {variable.name}", var_overlap))
            
            if variable.description:
                desc_words = set(variable.description.lower().split())
                desc_overlap = len(query_words & desc_words) / len(query_words) if query_words else 0
                if desc_overlap > 0.3:
                    matches.append((MatchType.FUZZY, f"variable desc: {variable.name}", desc_overlap))
        
        return matches
    
    def _match_variables(self, query_vars: List[str], 
                        service_vars: List[VariableInfo],
                        canonical_only: bool = False) -> List[Tuple[MatchType, str, float]]:
        """Match query variables against service variables"""
        matches = []
        
        for query_var in query_vars:
            query_lower = query_var.lower()
            
            for service_var in service_vars:
                # Exact ID match
                if service_var.id and service_var.id.lower() == query_lower:
                    matches.append((MatchType.EXACT, f"variable: {service_var.id}", 1.0))
                    continue
                
                # Canonical match
                if service_var.canonical and service_var.canonical.lower() == query_lower:
                    matches.append((MatchType.CANONICAL, f"canonical: {service_var.canonical}", 0.95))
                    continue
                
                if canonical_only:
                    continue
                
                # Name match
                if service_var.name and service_var.name.lower() == query_lower:
                    matches.append((MatchType.SYNONYM, f"name: {service_var.name}", 0.8))
                    continue
                    
                # Fuzzy matches
                if service_var.name and query_lower in service_var.name.lower():
                    score = len(query_lower) / len(service_var.name) if service_var.name else 0
                    if score > 0.3:
                        matches.append((MatchType.FUZZY, f"partial: {service_var.name}", score * 0.6))
        
        return matches
    
    def _match_spatial(self, query: DiscoveryQuery, 
                      coverage) -> List[Tuple[MatchType, str, float]]:
        """Match spatial requirements"""
        matches = []
        
        # Simple coverage matching - could be enhanced with actual geometry
        if query.spatial_coverage and coverage:
            if query.spatial_coverage.lower() in coverage.description.lower():
                matches.append((MatchType.SPATIAL, f"coverage: {coverage.description}", 0.8))
        
        # TODO: Implement bbox intersection checking
        if query.bbox and coverage and coverage.bbox:
            # Placeholder for actual bbox intersection logic
            matches.append((MatchType.SPATIAL, "bbox intersection", 0.6))
            
        return matches
    
    def _match_temporal(self, query: DiscoveryQuery, 
                       coverage) -> List[Tuple[MatchType, str, float]]:
        """Match temporal requirements"""
        matches = []
        
        if query.temporal_coverage and coverage:
            if query.temporal_coverage.lower() in coverage.description.lower():
                matches.append((MatchType.TEMPORAL, f"period: {coverage.description}", 0.7))
        
        # TODO: Implement actual date range intersection
        if query.date_range and coverage:
            matches.append((MatchType.TEMPORAL, "date range overlap", 0.5))
            
        return matches
    
    def _matches_scope(self, metadata: ServiceMetadata, scope: SearchScope) -> bool:
        """Check if service matches search scope"""
        if scope == SearchScope.ALL:
            return True
        elif scope == SearchScope.GOVERNMENT:
            gov_providers = {'USGS', 'EPA', 'NOAA', 'NASA', 'USDA', 'EIA'}
            return any(gov in metadata.provider.upper() for gov in gov_providers)
        elif scope == SearchScope.EARTH_ENGINE:
            return 'earth engine' in metadata.provider.lower() or 'google' in metadata.provider.lower()
        elif scope == SearchScope.AUTHENTICATED:
            return metadata.authentication.required
        elif scope == SearchScope.PUBLIC:
            return not metadata.authentication.required
        return True
    
    def _location_in_coverage(self, lat: float, lon: float, coverage) -> bool:
        """Check if location is within spatial coverage"""
        # Simplified coverage checking - could be enhanced
        if not coverage:
            return False
            
        if coverage.bbox:
            west, south, east, north = coverage.bbox
            return west <= lon <= east and south <= lat <= north
            
        # Fallback to description-based checking
        coverage_desc = coverage.description.lower()
        if 'global' in coverage_desc:
            return True
        elif 'us' in coverage_desc or 'united states' in coverage_desc:
            return -180 <= lon <= -60 and 20 <= lat <= 75  # Approximate US bounds
            
        return False
    
    def _build_variable_aliases(self) -> Dict[str, Set[str]]:
        """Build variable alias dictionary for enhanced matching"""
        aliases = {
            'temperature': {'temp', 'air_temp', 'water_temp', 'temperature', 'celsius', 'fahrenheit'},
            'precipitation': {'precip', 'rainfall', 'rain', 'precipitation', 'ppt'},
            'discharge': {'flow', 'streamflow', 'river_flow', 'discharge', 'cfs', 'cms'},
            'water_level': {'stage', 'height', 'water_height', 'gage_height', 'level'},
            'ph': {'ph', 'acidity', 'alkalinity'},
            'dissolved_oxygen': {'do', 'oxygen', 'dissolved_oxygen', 'o2'},
            'conductivity': {'ec', 'specific_conductance', 'conductivity', 'salinity'},
            'turbidity': {'turbidity', 'tss', 'suspended_solids', 'clarity'}
        }
        return aliases
    
    def _build_domain_keywords(self) -> Dict[str, Set[str]]:
        """Build domain keyword dictionary"""
        keywords = {
            'water': {'water', 'hydro', 'stream', 'river', 'lake', 'groundwater', 'aquatic'},
            'air': {'air', 'atmosphere', 'atmospheric', 'pollution', 'quality', 'emission'},
            'atmospheric': {'air', 'atmosphere', 'atmospheric', 'pressure', 'meteorological', 'weather'},
            'soil': {'soil', 'ground', 'earth', 'sediment', 'agriculture', 'pedologic'},
            'climate': {'climate', 'weather', 'meteorological', 'precipitation', 'temperature'},
            'meteorology': {'weather', 'meteorological', 'atmospheric', 'climate', 'forecast'},
            'biodiversity': {'species', 'ecology', 'biological', 'fauna', 'flora', 'ecosystem'},
            'marine': {'ocean', 'marine', 'coastal', 'sea', 'buoy', 'oceanographic'},
            'energy': {'energy', 'power', 'electricity', 'renewable', 'fossil', 'consumption'}
        }
        return keywords
    
    def _generate_reason(self, matches: List[Tuple[MatchType, str, float]], 
                        metadata: ServiceMetadata) -> str:
        """Generate human-readable reason for match"""
        if not matches:
            return f"Service available: {metadata.title}"
            
        # Find best match
        best_match = max(matches, key=lambda m: m[2])
        match_type, match_text, score = best_match
        
        if match_type == MatchType.EXACT:
            return f"Exact match: {match_text}"
        elif match_type == MatchType.CANONICAL:
            return f"Canonical variable: {match_text}"
        elif match_type == MatchType.DOMAIN:
            return f"Domain match: {match_text}"
        else:
            return f"Relevant match: {match_text} (score: {score:.2f})"
    
    def _get_most_common_variables(self, limit: int) -> List[Tuple[str, int]]:
        """Get most commonly available variables across all services"""
        variable_counts = Counter()
        
        for metadata in self.registry.get_all_metadata().values():
            for var in metadata.capabilities.variables:
                var_name = var.canonical or var.name or var.id
                if var_name:
                    variable_counts[var_name] += 1
                    
        return variable_counts.most_common(limit)