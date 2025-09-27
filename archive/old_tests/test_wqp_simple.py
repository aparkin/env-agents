"""
Simple test of WQP adapter with dynamic characteristics (with fallback)
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from env_agents.adapters.wqp.adapter import EnhancedWQPAdapter

def test_wqp_simple():
    """Test WQP adapter with graceful fallback."""
    
    print("Testing WQP adapter...")
    
    # Test adapter instantiation
    adapter = EnhancedWQPAdapter()
    print("✅ WQP adapter instantiated")
    
    # Test enhanced parameter metadata (should work with fallback)
    enhanced_params = adapter.get_enhanced_parameter_metadata()
    print(f"✅ Enhanced parameters: {len(enhanced_params)} total")
    
    # Test capabilities
    capabilities = adapter.capabilities()
    variables = capabilities.get('variables', [])
    print(f"✅ Capabilities variables: {len(variables)} available")
    
    # Show variable count improvement
    if len(enhanced_params) > 8:  # Original was 8 hardcoded
        print(f"🎉 SUCCESS: Variable count increased from 8 to {len(enhanced_params)}!")
    else:
        print(f"📝 Using fallback with {len(enhanced_params)} variables")
    
    return len(enhanced_params)

if __name__ == "__main__":
    count = test_wqp_simple()
    print(f"Final count: {count}")