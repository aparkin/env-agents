"""
NWIS Parameter Harvester Implementation
Implements formal harvest() method for ServiceDiscovery integration
"""

from typing import List, Dict, Any
from datetime import datetime, timezone

def add_harvest_method_to_nwis(adapter_instance):
    """Add harvest method to existing NWIS adapter instance"""
    
    def harvest(self) -> List[Dict[str, Any]]:
        """
        Harvest USGS NWIS parameter catalog for semantic discovery
        Returns ServiceCapability-compatible objects
        """
        try:
            # Use existing _harvest_parameter_codes method
            params = self._harvest_parameter_codes(groups="ALL")  # Get all parameter groups
            
            # Convert to ServiceCapability format
            capabilities = []
            for param in params:
                capabilities.append({
                    'service': self.DATASET,
                    'native_id': param.get('platform', ''),
                    'label': param.get('description', ''),
                    'unit': param.get('unit', ''),
                    'description': param.get('description', ''),
                    'domain': 'water',
                    'frequency': 'varies',
                    'spatial_coverage': 'continental_us',
                    'temporal_coverage': 'historical_and_realtime',
                    'last_updated': datetime.now(timezone.utc).isoformat(),
                    'metadata': {
                        'canonical': param.get('canonical', ''),
                        'parameter_group': 'physical_chemical',
                        'usgs_parameter_code': param.get('platform', ''),
                        'data_types': ['instantaneous_values', 'daily_values']
                    }
                })
            
            return capabilities
            
        except Exception as e:
            self.logger.error(f"NWIS parameter harvest failed: {e}")
            return []
    
    # Bind method to instance
    import types
    adapter_instance.harvest = types.MethodType(harvest, adapter_instance)
    return adapter_instance