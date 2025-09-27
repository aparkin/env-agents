"""
Simple contract test to verify basic adapter functionality.
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from env_agents.adapters.power.adapter import NASAPOWEREnhancedAdapter
from env_agents.adapters.base import BaseAdapter
from env_agents.core.models import RequestSpec, Geometry

def test_basic_contract():
    """Test basic contract compliance for one adapter."""
    
    # Test instantiation
    adapter = NASAPOWEREnhancedAdapter()
    assert adapter is not None
    
    # Test inheritance
    assert isinstance(adapter, BaseAdapter)
    
    # Test required constants
    assert hasattr(adapter, 'DATASET')
    assert hasattr(adapter, 'SOURCE_URL')
    assert hasattr(adapter, 'SOURCE_VERSION')
    assert hasattr(adapter, 'LICENSE')
    
    # Test capabilities method
    capabilities = adapter.capabilities()
    assert isinstance(capabilities, dict)
    assert 'variables' in capabilities
    assert isinstance(capabilities['variables'], list)
    
    # Test _fetch_rows method exists
    assert hasattr(adapter, '_fetch_rows')
    assert callable(adapter._fetch_rows)
    
    print("✅ Basic contract test passed!")

if __name__ == "__main__":
    test_basic_contract()