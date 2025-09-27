"""
Test WQP dynamic characteristic discovery
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from env_agents.adapters.wqp.adapter import EnhancedWQPAdapter

def test_wqp_dynamic_discovery():
    """Test WQP dynamic EPA characteristics discovery."""
    
    print("Testing WQP dynamic EPA characteristics discovery...")
    
    # Test adapter instantiation
    adapter = EnhancedWQPAdapter()
    print("✅ WQP adapter instantiated")
    
    # Test EPA characteristics fetch
    print("\nFetching EPA characteristics...")
    epa_chars = adapter.fetch_epa_characteristics()
    print(f"✅ Fetched {len(epa_chars)} EPA characteristics")
    
    if epa_chars:
        # Show sample characteristics
        print(f"\nSample EPA characteristics:")
        for i, char in enumerate(epa_chars[:5]):  # Show first 5
            print(f"  {i+1}. {char['name']} ({char['units']}) - {char['group']}")
    
    # Test enhanced parameter metadata (combines hardcoded + EPA)
    print("\nTesting enhanced parameter metadata...")
    enhanced_params = adapter.get_enhanced_parameter_metadata()
    print(f"✅ Combined parameters: {len(enhanced_params)} total")
    
    # Test capabilities
    print("\nTesting capabilities...")
    capabilities = adapter.capabilities()
    variables = capabilities.get('variables', [])
    print(f"✅ Capabilities variables: {len(variables)} available")
    
    print(f"\nSample variables from capabilities:")
    for i, var in enumerate(variables[:3]):  # Show first 3
        if isinstance(var, dict):
            print(f"  {i+1}. {var.get('name', 'Unknown')} - {var.get('description', '')[:100]}...")
    
    print("\n🎉 WQP dynamic discovery test completed!")

if __name__ == "__main__":
    test_wqp_dynamic_discovery()