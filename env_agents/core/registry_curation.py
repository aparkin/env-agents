"""
Registry Curation and Management Workflows

Provides tools for managing semantic mappings, reviewing suggestions,
and maintaining registry quality across environmental data services.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path

from .service_discovery import ServiceDiscoveryEngine, DiscoveryReport
from .term_broker import MatchSuggestion
from .registry import RegistryManager


@dataclass
class CurationAction:
    """Represents a curation action taken on a registry suggestion"""
    action: str  # "accept", "reject", "modify", "defer"
    dataset: str
    native_id: str
    canonical: Optional[str]
    reason: str
    curator: str
    timestamp: str
    confidence: Optional[float] = None
    modifications: Optional[Dict[str, Any]] = None


@dataclass
class QualityReport:
    """Quality assessment report for registry content"""
    total_variables: int
    missing_uris: int
    missing_units: int  
    inconsistent_mappings: int
    orphaned_mappings: int
    coverage_by_domain: Dict[str, int]
    recommendations: List[str]


class RegistryCurator:
    """
    Interactive curation interface for managing registry suggestions
    and maintaining semantic quality
    """
    
    def __init__(self, registry_manager: RegistryManager, curator_id: str = "system"):
        self.registry = registry_manager
        self.curator_id = curator_id
        self.logger = logging.getLogger(__name__)
        self._curation_log: List[CurationAction] = []
    
    def review_pending_suggestions(self, 
                                 limit: Optional[int] = None,
                                 min_confidence: float = 0.0,
                                 domain_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve pending suggestions from registry_delta for review
        """
        delta = self.registry.get_delta()
        pending = []
        
        for key, suggestion in delta.items():
            if suggestion.get('status') != 'pending':
                continue
                
            confidence = suggestion.get('confidence', 0.0)
            if confidence < min_confidence:
                continue
                
            # Apply domain filter if specified
            if domain_filter:
                canonical = suggestion.get('suggested_canonical', '')
                if not canonical.startswith(f"{domain_filter}:"):
                    continue
            
            # Enhance suggestion with context
            enhanced = self._enhance_suggestion(suggestion)
            pending.append(enhanced)
            
            if limit and len(pending) >= limit:
                break
        
        # Sort by confidence descending
        pending.sort(key=lambda x: x.get('confidence', 0.0), reverse=True)
        return pending
    
    def accept_suggestion(self, 
                         dataset: str, 
                         native_id: str, 
                         canonical: Optional[str] = None,
                         modifications: Optional[Dict[str, Any]] = None) -> bool:
        """
        Accept a suggestion and promote it to registry_overrides
        """
        delta = self.registry.get_delta()
        key = f"{dataset}:{native_id}"
        
        if key not in delta:
            self.logger.error(f"Suggestion not found: {key}")
            return False
        
        suggestion = delta[key]
        final_canonical = canonical or suggestion.get('suggested_canonical')
        
        if not final_canonical:
            self.logger.error(f"No canonical variable specified for {key}")
            return False
        
        # Add to overrides
        overrides = self.registry.get_overrides()
        
        if final_canonical not in overrides.get('variables', {}):
            overrides.setdefault('variables', {})[final_canonical] = {'datasets': {}}
        
        canonical_var = overrides['variables'][final_canonical]
        canonical_var['datasets'][dataset] = {
            'native': native_id,
            'manually_curated': True,
            'confidence': suggestion.get('confidence'),
            'original_reasons': suggestion.get('reasons', []),
            'curator': self.curator_id,
            'accepted_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Apply modifications if provided
        if modifications:
            canonical_var['datasets'][dataset].update(modifications)
        
        # Update delta status
        delta[key]['status'] = 'accepted'
        delta[key]['accepted_canonical'] = final_canonical
        delta[key]['accepted_at'] = datetime.now(timezone.utc).isoformat()
        delta[key]['curator'] = self.curator_id
        
        # Save changes
        self.registry.write_overrides(overrides)
        self.registry.write_delta(delta)
        
        # Log action
        self._log_curation_action(CurationAction(
            action="accept",
            dataset=dataset,
            native_id=native_id,
            canonical=final_canonical,
            reason=f"Accepted suggestion with confidence {suggestion.get('confidence')}",
            curator=self.curator_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            confidence=suggestion.get('confidence'),
            modifications=modifications
        ))
        
        self.logger.info(f"Accepted mapping: {dataset}:{native_id} -> {final_canonical}")
        return True
    
    def reject_suggestion(self, 
                         dataset: str, 
                         native_id: str, 
                         reason: str = "Manual rejection") -> bool:
        """
        Reject a suggestion and mark it as rejected
        """
        delta = self.registry.get_delta()
        key = f"{dataset}:{native_id}"
        
        if key not in delta:
            self.logger.error(f"Suggestion not found: {key}")
            return False
        
        # Update delta status
        delta[key]['status'] = 'rejected'
        delta[key]['rejected_at'] = datetime.now(timezone.utc).isoformat()
        delta[key]['rejection_reason'] = reason
        delta[key]['curator'] = self.curator_id
        
        self.registry.write_delta(delta)
        
        # Log action
        self._log_curation_action(CurationAction(
            action="reject",
            dataset=dataset,
            native_id=native_id,
            canonical=None,
            reason=reason,
            curator=self.curator_id,
            timestamp=datetime.now(timezone.utc).isoformat()
        ))
        
        self.logger.info(f"Rejected mapping: {dataset}:{native_id} - {reason}")
        return True
    
    def create_new_canonical_variable(self,
                                    canonical_id: str,
                                    label: str,
                                    domain: str,
                                    preferred_unit: str,
                                    description: Optional[str] = None,
                                    observed_property_uri: Optional[str] = None,
                                    unit_uri: Optional[str] = None) -> bool:
        """
        Create a new canonical variable in registry_seed
        """
        seed = self.registry.get_seed()
        
        if canonical_id in seed.get('variables', {}):
            self.logger.error(f"Canonical variable already exists: {canonical_id}")
            return False
        
        new_variable = {
            'label': label,
            'description': description or label,
            'preferred_unit': preferred_unit,
            'domain': domain,
            'created_by': self.curator_id,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'datasets': {}
        }
        
        if observed_property_uri:
            new_variable['observed_property_uri'] = observed_property_uri
        if unit_uri:
            new_variable['unit_uri'] = unit_uri
        
        seed.setdefault('variables', {})[canonical_id] = new_variable
        self.registry.write_seed(seed)
        
        self.logger.info(f"Created new canonical variable: {canonical_id}")
        return True
    
    def batch_process_high_confidence(self, 
                                    confidence_threshold: float = 0.95,
                                    dry_run: bool = True) -> Dict[str, int]:
        """
        Batch process high-confidence suggestions for auto-acceptance
        """
        delta = self.registry.get_delta()
        results = {'accepted': 0, 'skipped': 0, 'errors': 0}
        
        for key, suggestion in delta.items():
            if suggestion.get('status') != 'pending':
                results['skipped'] += 1
                continue
                
            confidence = suggestion.get('confidence', 0.0)
            if confidence < confidence_threshold:
                results['skipped'] += 1
                continue
            
            dataset = suggestion.get('dataset')
            native_id = suggestion.get('native_id')
            
            if not dry_run:
                if self.accept_suggestion(dataset, native_id):
                    results['accepted'] += 1
                else:
                    results['errors'] += 1
            else:
                self.logger.info(f"Would accept: {dataset}:{native_id} (confidence: {confidence})")
                results['accepted'] += 1
        
        return results
    
    def generate_quality_report(self) -> QualityReport:
        """
        Generate a comprehensive quality report for the registry
        """
        merged = self.registry.merged()
        variables = merged.get('variables', {})
        
        total_variables = len(variables)
        missing_uris = 0
        missing_units = 0
        coverage_by_domain = {}
        recommendations = []
        
        for canonical_id, var_data in variables.items():
            # Check for missing URIs
            if not var_data.get('observed_property_uri'):
                missing_uris += 1
            
            # Check for missing units
            if not var_data.get('preferred_unit'):
                missing_units += 1
            
            # Count by domain
            domain = var_data.get('domain', 'unknown')
            coverage_by_domain[domain] = coverage_by_domain.get(domain, 0) + 1
        
        # Generate recommendations
        if missing_uris > total_variables * 0.3:
            recommendations.append("High number of variables missing observed property URIs")
        
        if missing_units > total_variables * 0.1:
            recommendations.append("Several variables missing preferred units")
        
        if 'unknown' in coverage_by_domain and coverage_by_domain['unknown'] > 5:
            recommendations.append("Many variables without assigned domains")
        
        return QualityReport(
            total_variables=total_variables,
            missing_uris=missing_uris,
            missing_units=missing_units,
            inconsistent_mappings=0,  # TODO: Implement consistency checking
            orphaned_mappings=0,      # TODO: Implement orphan detection
            coverage_by_domain=coverage_by_domain,
            recommendations=recommendations
        )
    
    def _enhance_suggestion(self, suggestion: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance a suggestion with additional context for review
        """
        enhanced = suggestion.copy()
        
        # Add related variables
        canonical = suggestion.get('suggested_canonical', '')
        if canonical:
            domain = canonical.split(':')[0] if ':' in canonical else 'unknown'
            enhanced['domain'] = domain
            
            # Find similar variables in the same domain
            merged = self.registry.merged()
            related = []
            for var_id, var_data in merged.get('variables', {}).items():
                if var_data.get('domain') == domain and var_id != canonical:
                    related.append({
                        'id': var_id,
                        'label': var_data.get('label', ''),
                        'unit': var_data.get('preferred_unit', '')
                    })
            
            enhanced['related_variables'] = related[:5]  # Limit to 5
        
        # Add confidence interpretation
        confidence = suggestion.get('confidence', 0.0)
        if confidence >= 0.90:
            enhanced['confidence_level'] = 'very_high'
        elif confidence >= 0.70:
            enhanced['confidence_level'] = 'high'
        elif confidence >= 0.50:
            enhanced['confidence_level'] = 'medium'
        else:
            enhanced['confidence_level'] = 'low'
        
        return enhanced
    
    def _log_curation_action(self, action: CurationAction):
        """Log a curation action for audit trail"""
        self._curation_log.append(action)
    
    def export_curation_log(self, filepath: Optional[Path] = None) -> str:
        """Export curation log to JSON file"""
        if filepath is None:
            filepath = Path(f"curation_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        log_data = {
            'curator': self.curator_id,
            'export_time': datetime.now(timezone.utc).isoformat(),
            'actions': [
                {
                    'action': a.action,
                    'dataset': a.dataset,
                    'native_id': a.native_id,
                    'canonical': a.canonical,
                    'reason': a.reason,
                    'timestamp': a.timestamp,
                    'confidence': a.confidence,
                    'modifications': a.modifications
                }
                for a in self._curation_log
            ]
        }
        
        with open(filepath, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        return str(filepath)


class AutoCurationPipeline:
    """
    Automated pipeline for continuous registry improvement
    """
    
    def __init__(self, registry_manager: RegistryManager, discovery_engine: ServiceDiscoveryEngine):
        self.registry = registry_manager
        self.discovery = discovery_engine
        self.logger = logging.getLogger(__name__)
    
    def run_discovery_pipeline(self, 
                             router,
                             auto_accept_threshold: float = 0.90,
                             suggest_threshold: float = 0.60) -> Dict[str, DiscoveryReport]:
        """
        Run discovery pipeline across all registered adapters
        """
        reports = {}
        
        for dataset, adapter in router.adapters.items():
            self.logger.info(f"Running discovery for {dataset}")
            
            try:
                report = self.discovery.discover_service_parameters(
                    adapter,
                    auto_accept_threshold=auto_accept_threshold,
                    suggest_threshold=suggest_threshold
                )
                reports[dataset] = report
                
                self.logger.info(f"{dataset}: {report.discovered_count} parameters, "
                               f"{len(report.auto_accepted)} auto-accepted, "
                               f"{len(report.review_queue)} for review")
                
            except Exception as e:
                self.logger.error(f"Discovery failed for {dataset}: {e}")
        
        return reports
    
    def run_nightly_curation(self, router) -> Dict[str, Any]:
        """
        Nightly automated curation process
        """
        start_time = datetime.now()
        
        # 1. Run discovery on all services
        discovery_reports = self.run_discovery_pipeline(router)
        
        # 2. Generate quality report
        curator = RegistryCurator(self.registry, "auto_curator")
        quality_report = curator.generate_quality_report()
        
        # 3. Process very high confidence suggestions
        batch_results = curator.batch_process_high_confidence(
            confidence_threshold=0.95,
            dry_run=False
        )
        
        summary = {
            'execution_time': (datetime.now() - start_time).total_seconds(),
            'services_processed': len(discovery_reports),
            'total_discovered': sum(r.discovered_count for r in discovery_reports.values()),
            'auto_accepted': sum(len(r.auto_accepted) for r in discovery_reports.values()),
            'review_queue': sum(len(r.review_queue) for r in discovery_reports.values()),
            'batch_accepted': batch_results['accepted'],
            'quality_score': self._calculate_quality_score(quality_report),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        self.logger.info(f"Nightly curation completed: {summary}")
        return summary
    
    def _calculate_quality_score(self, quality_report: QualityReport) -> float:
        """Calculate overall registry quality score (0-100)"""
        if quality_report.total_variables == 0:
            return 0.0
        
        # Penalize missing data
        uri_completeness = 1.0 - (quality_report.missing_uris / quality_report.total_variables)
        unit_completeness = 1.0 - (quality_report.missing_units / quality_report.total_variables)
        
        # Reward domain diversity
        domain_diversity = min(1.0, len(quality_report.coverage_by_domain) / 7.0)  # 7 expected domains
        
        overall_score = (uri_completeness * 0.4 + unit_completeness * 0.4 + domain_diversity * 0.2) * 100
        return round(overall_score, 1)