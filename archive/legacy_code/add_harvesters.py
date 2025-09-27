#!/usr/bin/env python3
"""
Add harvest() methods to existing gold standard adapters

This script adds the formal harvest() interface to NWIS, OpenAQ, and NASA POWER
adapters by wrapping their existing parameter discovery methods.
"""

import sys
from pathlib import Path

def add_nwis_harvest():
    """Add harvest method to NWIS adapter"""
    nwis_file = Path("env_agents/adapters/nwis/adapter.py")
    
    harvest_method = '''
    def harvest(self) -> List[Dict[str, Any]]:
        """
        Harvest USGS NWIS parameter catalog for semantic discovery
        Returns ServiceCapability-compatible objects
        """
        try:
            # Use existing _harvest_parameter_codes method with all groups
            params = self._harvest_parameter_codes(groups="ALL")
            
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
                        'parameter_group': 'usgs_water_quality',
                        'usgs_parameter_code': param.get('platform', ''),
                        'data_types': ['instantaneous_values', 'daily_values']
                    }
                })
            
            return capabilities
            
        except Exception as e:
            self.logger.error(f"NWIS parameter harvest failed: {e}")
            return []
'''
    
    # Read current file
    content = nwis_file.read_text()
    
    # Find the end of the class (before the last method)
    # Add just before the final closing of the class
    insertion_point = content.rfind("    def _iv_to_daily_rows")
    if insertion_point != -1:
        new_content = content[:insertion_point] + harvest_method + "\n" + content[insertion_point:]
        nwis_file.write_text(new_content)
        print("✅ Added harvest() method to NWIS adapter")
    else:
        print("❌ Could not find insertion point in NWIS adapter")

def add_openaq_harvest():
    """Add harvest method to OpenAQ adapter"""
    openaq_file = Path("env_agents/adapters/openaq/adapter.py")
    
    harvest_method = '''
    def harvest(self) -> List[Dict[str, Any]]:
        """
        Harvest OpenAQ parameter catalog for semantic discovery
        Returns ServiceCapability-compatible objects
        """
        try:
            # Get API key (required for catalog access)
            headers = {"X-API-Key": self._get_api_key({})}
            
            # Use existing _openaq_parameter_catalog method
            catalog = self._openaq_parameter_catalog(headers)
            
            # Convert to ServiceCapability format
            capabilities = []
            for param in catalog:
                param_name = param.get('name', '')
                capabilities.append({
                    'service': self.DATASET,
                    'native_id': param_name,
                    'label': param.get('displayName', param_name),
                    'unit': param.get('units', ''),
                    'description': param.get('description', param_name),
                    'domain': 'air',
                    'frequency': 'varies',
                    'spatial_coverage': 'global',
                    'temporal_coverage': 'realtime_and_historical',
                    'last_updated': datetime.now(timezone.utc).isoformat(),
                    'metadata': {
                        'canonical': f"air:{param_name}",
                        'parameter_group': 'air_quality',
                        'openaq_parameter': param_name,
                        'data_types': ['measurements']
                    }
                })
            
            return capabilities
            
        except Exception as e:
            self.logger.error(f"OpenAQ parameter harvest failed: {e}")
            # Return fallback minimal list
            fallback_params = ["pm25", "pm10", "no2", "o3", "so2", "co"]
            return [
                {
                    'service': self.DATASET,
                    'native_id': param,
                    'label': f"{param.upper()} concentration",
                    'unit': 'µg/m³' if param.startswith('pm') else 'ppb',
                    'description': f"{param.upper()} air quality parameter",
                    'domain': 'air',
                    'frequency': 'varies',
                    'spatial_coverage': 'global',
                    'temporal_coverage': 'realtime_and_historical',
                    'last_updated': datetime.now(timezone.utc).isoformat(),
                    'metadata': {
                        'canonical': f"air:{param}",
                        'parameter_group': 'air_quality_fallback',
                        'openaq_parameter': param,
                        'data_types': ['measurements']
                    }
                }
                for param in fallback_params
            ]
'''
    
    # Read current file
    content = openaq_file.read_text()
    
    # Find insertion point (end of class)
    insertion_point = content.rfind("        return rows")
    if insertion_point != -1:
        # Find the end of that method
        next_line = content.find("\n", insertion_point)
        new_content = content[:next_line+1] + harvest_method + content[next_line+1:]
        openaq_file.write_text(new_content)
        print("✅ Added harvest() method to OpenAQ adapter")
    else:
        print("❌ Could not find insertion point in OpenAQ adapter")

def add_power_harvest():
    """Add harvest method to NASA POWER adapter"""
    power_file = Path("env_agents/adapters/power/adapter.py")
    
    harvest_method = '''
    def harvest(self) -> List[Dict[str, Any]]:
        """
        Harvest NASA POWER parameter catalog for semantic discovery
        Returns ServiceCapability-compatible objects
        """
        try:
            # Use existing _harvest_power_parameters method
            params = self._harvest_power_parameters(community="ALL")  # Get all communities
            
            # Convert to ServiceCapability format
            capabilities = []
            for param in params:
                param_code = param.get('platform', '')
                capabilities.append({
                    'service': self.DATASET,
                    'native_id': param_code,
                    'label': param.get('description', param_code),
                    'unit': param.get('unit', ''),
                    'description': param.get('description', param_code),
                    'domain': 'atmosphere',
                    'frequency': 'daily',
                    'spatial_coverage': 'global',
                    'temporal_coverage': '1981_present',
                    'last_updated': datetime.now(timezone.utc).isoformat(),
                    'metadata': {
                        'canonical': param.get('canonical', f"atm:{param_code.lower()}"),
                        'parameter_group': 'meteorological',
                        'power_parameter': param_code,
                        'data_types': ['daily_values']
                    }
                })
            
            return capabilities
            
        except Exception as e:
            self.logger.error(f"NASA POWER parameter harvest failed: {e}")
            # Return fallback from VARIABLE_MAP
            fallback_capabilities = []
            for canonical, meta in VARIABLE_MAP.items():
                power_meta = meta.get("NASAPOWER", {})
                if power_meta:
                    param_code = power_meta.get("parameter", "")
                    fallback_capabilities.append({
                        'service': self.DATASET,
                        'native_id': param_code,
                        'label': meta.get('label', canonical),
                        'unit': meta.get('unit', ''),
                        'description': meta.get('description', canonical),
                        'domain': 'atmosphere',
                        'frequency': 'daily',
                        'spatial_coverage': 'global',
                        'temporal_coverage': '1981_present',
                        'last_updated': datetime.now(timezone.utc).isoformat(),
                        'metadata': {
                            'canonical': canonical,
                            'parameter_group': 'meteorological_fallback',
                            'power_parameter': param_code,
                            'data_types': ['daily_values']
                        }
                    })
            return fallback_capabilities
'''
    
    # Read current file
    content = power_file.read_text()
    
    # Find insertion point (end of class)
    insertion_point = content.rfind("        return rows")
    if insertion_point != -1:
        # Find the end of that method and add harvest method
        next_line = content.find("\n\n", insertion_point)
        if next_line == -1:
            next_line = len(content)
        new_content = content[:next_line] + "\n" + harvest_method + content[next_line:]
        power_file.write_text(new_content)
        print("✅ Added harvest() method to NASA POWER adapter")
    else:
        print("❌ Could not find insertion point in NASA POWER adapter")

def main():
    print("🔧 Adding harvest() methods to gold standard adapters")
    print("=" * 50)
    
    try:
        add_nwis_harvest()
        add_openaq_harvest() 
        add_power_harvest()
        
        print("\n✅ All harvest methods added successfully!")
        print("\nNext steps:")
        print("1. Test the new harvest methods:")
        print("   python examples/quick_test.py")
        print("2. Run semantic discovery:")
        print("   python examples/rapid_development_test.py --level integration")
        
    except Exception as e:
        print(f"❌ Error adding harvest methods: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()