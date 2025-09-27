"""
Service Discovery and Registry Management for Environmental Data Services

This module provides automated discovery, mapping, and validation of environmental
data parameters across different government and scientific data sources.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import logging
from pathlib import Path

from .term_broker import TermBroker, NativeParam, MatchSuggestion, load_rule_pack
from .registry import RegistryManager
from .units import normalize_unit


@dataclass 
class ServiceCapability:
    """Discovered capability from a service"""
    service: str
    native_id: str
    label: Optional[str]
    unit: Optional[str]
    description: Optional[str]
    domain: Optional[str]
    frequency: Optional[str]
    spatial_coverage: Optional[str]
    temporal_coverage: Optional[str]
    last_updated: Optional[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DiscoveryReport:
    """Report from service discovery process"""
    service: str
    discovered_count: int
    auto_accepted: List[MatchSuggestion]
    review_queue: List[MatchSuggestion]
    failed_matches: List[ServiceCapability]
    execution_time: float
    errors: List[str] = field(default_factory=list)


class ServiceDiscoveryEngine:
    """
    Automated discovery and semantic mapping engine for environmental services
    """
    
    def __init__(self, registry_manager: RegistryManager, base_dir: str = "."):
        self.registry = registry_manager
        self.base_dir = Path(base_dir)
        self.logger = logging.getLogger(__name__)
        
    def discover_service_parameters(self, 
                                   adapter, 
                                   *, 
                                   force_refresh: bool = False,
                                   auto_accept_threshold: float = 0.90,
                                   suggest_threshold: float = 0.60) -> DiscoveryReport:
        """
        Discover and map service parameters using harvest + TermBroker
        """
        start_time = datetime.now()
        service_name = adapter.DATASET
        
        try:
            # 1. Harvest service capabilities
            capabilities = self._harvest_service_capabilities(adapter, force_refresh)
            
            # 2. Convert to NativeParam objects
            native_params = self._capabilities_to_native_params(service_name, capabilities)
            
            # 3. Use TermBroker for semantic matching
            broker = TermBroker(self.registry.merged())
            accepted, suggestions = broker.match(
                service_name, 
                native_params,
                auto_accept_threshold=auto_accept_threshold,
                suggest_threshold=suggest_threshold
            )
            
            # 4. Auto-accept high confidence matches
            if accepted:
                self._auto_accept_mappings(accepted)
                
            # 5. Queue suggestions for review
            if suggestions:
                self._queue_suggestions(suggestions)
                
            # 6. Identify failed matches
            mapped_ids = {m.native_id for m in (accepted + suggestions)}
            failed = [cap for cap in capabilities if cap.native_id not in mapped_ids]
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return DiscoveryReport(
                service=service_name,
                discovered_count=len(capabilities),
                auto_accepted=accepted,
                review_queue=suggestions,
                failed_matches=failed,
                execution_time=execution_time
            )
            
        except Exception as e:
            self.logger.error(f"Discovery failed for {service_name}: {e}")
            execution_time = (datetime.now() - start_time).total_seconds()
            return DiscoveryReport(
                service=service_name,
                discovered_count=0,
                auto_accepted=[],
                review_queue=[],
                failed_matches=[],
                execution_time=execution_time,
                errors=[str(e)]
            )
    
    def _harvest_service_capabilities(self, adapter, force_refresh: bool) -> List[ServiceCapability]:
        """Extract capabilities from adapter using harvest() or capabilities() fallback"""
        capabilities = []
        
        # Try harvest() method first (preferred)
        if hasattr(adapter, 'harvest') and callable(adapter.harvest):
            try:
                harvested = adapter.harvest()
                capabilities.extend(self._process_harvested_data(adapter.DATASET, harvested))
            except Exception as e:
                self.logger.warning(f"Harvest failed for {adapter.DATASET}: {e}")
        
        # Fallback to capabilities()
        if not capabilities:
            try:
                caps = adapter.capabilities()
                variables = caps.get('variables', [])
                for var in variables:
                    capabilities.append(ServiceCapability(
                        service=adapter.DATASET,
                        native_id=var.get('platform', var.get('canonical', '')),
                        label=var.get('description', var.get('label', '')),
                        unit=var.get('unit', ''),
                        description=var.get('description', ''),
                        domain=self._infer_domain_from_service(adapter.DATASET),
                        frequency=caps.get('temporal_resolution'),
                        spatial_coverage=str(caps.get('geometry', [])),
                        temporal_coverage=caps.get('temporal_coverage'),
                        last_updated=datetime.now(timezone.utc).isoformat(),
                    ))
            except Exception as e:
                self.logger.error(f"Capabilities extraction failed for {adapter.DATASET}: {e}")
                
        return capabilities
    
    def _process_harvested_data(self, service: str, harvested_data: Any) -> List[ServiceCapability]:
        """Process raw harvested data into ServiceCapability objects"""
        capabilities = []
        
        if isinstance(harvested_data, list):
            for item in harvested_data:
                if isinstance(item, dict):
                    capabilities.append(ServiceCapability(
                        service=service,
                        native_id=item.get('id', item.get('platform', item.get('code', ''))),
                        label=item.get('name', item.get('label', item.get('description', ''))),
                        unit=normalize_unit(item.get('unit', item.get('units', ''))),
                        description=item.get('description', item.get('longname', '')),
                        domain=item.get('domain', self._infer_domain_from_service(service)),
                        frequency=item.get('frequency'),
                        spatial_coverage=item.get('spatial_coverage'),
                        temporal_coverage=item.get('temporal_coverage'),
                        last_updated=datetime.now(timezone.utc).isoformat(),
                        metadata=item
                    ))
        
        return capabilities
    
    def _capabilities_to_native_params(self, service: str, capabilities: List[ServiceCapability]) -> List[NativeParam]:
        """Convert ServiceCapability objects to NativeParam for TermBroker"""
        native_params = []
        
        for cap in capabilities:
            native_params.append(NativeParam(
                dataset=service,
                id=cap.native_id,
                label=cap.label,
                unit=cap.unit,
                domain=cap.domain
            ))
            
        return native_params
    
    def _auto_accept_mappings(self, accepted: List[MatchSuggestion]):
        """Add auto-accepted mappings to registry_overrides.json"""
        overrides = self.registry.get_overrides()
        
        for match in accepted:
            if match.dataset not in overrides.get('variables', {}):
                overrides.setdefault('variables', {})[match.canonical] = {
                    'datasets': {}
                }
            
            canonical_var = overrides['variables'].setdefault(match.canonical, {'datasets': {}})
            canonical_var['datasets'][match.dataset] = {
                'native': match.native_id,
                'auto_accepted': True,
                'confidence': match.score,
                'reasons': match.reasons,
                'accepted_at': datetime.now(timezone.utc).isoformat()
            }
        
        self.registry.write_overrides(overrides)
        self.logger.info(f"Auto-accepted {len(accepted)} mappings")
    
    def _queue_suggestions(self, suggestions: List[MatchSuggestion]):
        """Add suggestions to registry_delta.json for review"""
        delta = self.registry.get_delta()
        
        for suggestion in suggestions:
            key = f"{suggestion.dataset}:{suggestion.native_id}"
            delta[key] = {
                'dataset': suggestion.dataset,
                'native_id': suggestion.native_id,
                'native_label': suggestion.native_label,
                'native_unit': suggestion.native_unit,
                'suggested_canonical': suggestion.canonical,
                'confidence': suggestion.score,
                'reasons': suggestion.reasons,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'status': 'pending'
            }
        
        self.registry.write_delta(delta)
        self.logger.info(f"Queued {len(suggestions)} suggestions for review")
    
    def _infer_domain_from_service(self, service: str) -> Optional[str]:
        """Infer domain from service name"""
        service_lower = service.lower()
        
        domain_map = {
            'usgs_nwis': 'water',
            'usgs_wqp': 'water', 
            'openaq': 'air',
            'epa_aqs': 'air',
            'nasa_power': 'atmosphere',
            'noaa': 'atmosphere',
            'era5': 'atmosphere',
            'appeears': 'land',
            'cropscape': 'land',
            'firms': 'fire',
            'gbif': 'ecology',
            'osm': 'infrastructure'
        }
        
        for key, domain in domain_map.items():
            if key in service_lower:
                return domain
                
        return None


class RegistryValidator:
    """Validates registry consistency and semantic quality"""
    
    def __init__(self, registry_manager: RegistryManager):
        self.registry = registry_manager
        self.logger = logging.getLogger(__name__)
    
    def validate_registry_consistency(self) -> Dict[str, List[str]]:
        """Validate registry for consistency issues"""
        issues = {
            'missing_units': [],
            'invalid_uris': [],
            'duplicate_mappings': [],
            'unit_conflicts': [],
            'domain_mismatches': []
        }
        
        merged = self.registry.merged()
        variables = merged.get('variables', {})
        
        for canonical_id, var_data in variables.items():
            # Check for missing preferred units
            if not var_data.get('preferred_unit'):
                issues['missing_units'].append(canonical_id)
            
            # Check for invalid URIs
            uri = var_data.get('observed_property_uri')
            if uri and not self._is_valid_uri(uri):
                issues['invalid_uris'].append(f"{canonical_id}: {uri}")
            
            # Check for unit conflicts across datasets
            datasets = var_data.get('datasets', {})
            units_seen = set()
            for ds_name, ds_data in datasets.items():
                native_unit = ds_data.get('unit')
                if native_unit:
                    normalized = normalize_unit(native_unit)
                    if normalized and normalized not in units_seen:
                        units_seen.add(normalized)
                    elif normalized and len(units_seen) > 1:
                        issues['unit_conflicts'].append(f"{canonical_id}: multiple units {units_seen}")
        
        return issues
    
    def _is_valid_uri(self, uri: str) -> bool:
        """Basic URI validation"""
        return uri.startswith(('http://', 'https://')) and '/' in uri[8:]
    
    def suggest_registry_improvements(self) -> Dict[str, Any]:
        """Suggest improvements to registry structure"""
        suggestions = {
            'new_canonical_variables': [],
            'unit_standardizations': [],
            'ontology_enhancements': [],
            'cross_reference_opportunities': []
        }
        
        # Analyze patterns in registry_delta to suggest new canonical variables
        delta = self.registry.get_delta()
        
        # Group similar suggestions
        label_groups = {}
        for key, suggestion in delta.items():
            if suggestion.get('status') == 'pending':
                label = suggestion.get('native_label', '').lower()
                label_groups.setdefault(label, []).append(suggestion)
        
        # Suggest canonical variables for frequently occurring labels
        for label, suggestions_list in label_groups.items():
            if len(suggestions_list) >= 2:  # Multiple services have this parameter
                services = [s['dataset'] for s in suggestions_list]
                suggestions['new_canonical_variables'].append({
                    'suggested_canonical': f"env:{label.replace(' ', '_')}",
                    'label': label,
                    'services': services,
                    'count': len(suggestions_list)
                })
        
        return suggestions