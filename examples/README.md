# Environmental Services Framework - Examples

**Version**: 1.0.0  
**Status**: Current examples using enhanced adapters

This directory contains current, working examples demonstrating the environmental services framework.

## 🚀 Available Examples

### `quick_start.py`
**Purpose**: Minimal working example of the framework  
**Usage**: 
```bash
python examples/quick_start.py
```

**Demonstrates**:
- Initializing an enhanced adapter (NASA POWER)
- Service capability discovery
- Creating data requests with RequestSpec and Geometry
- Retrieving standardized environmental data
- Understanding the 20-column output schema

**Expected Output**: Successfully retrieves temperature and precipitation data for San Francisco

## 🏃 Running Examples

### Prerequisites
```bash
# Install framework
pip install -e .

# Run from project root directory
python examples/quick_start.py
```

### No Authentication Required
The current examples use services that don't require API keys:
- NASA POWER: Public access
- Other services: Can be tested with optional credentials

## 📁 Archive Notice

**Legacy examples** have been moved to `archive/legacy_code/examples/` as they used outdated adapter classes and import paths that are no longer compatible with the current framework structure.

The current examples use:
- **Enhanced Adapters**: `enhanced_adapter.py` classes
- **Current Imports**: Proper module paths for the production framework
- **Standardized Patterns**: RequestSpec, Geometry, and 20-column output schema

## 🔧 Adding New Examples

When adding new examples:

1. **Use Enhanced Adapters**: Import from `env_agents.adapters.{service}.enhanced_adapter`
2. **Follow Patterns**: Use RequestSpec and Geometry classes
3. **Handle Errors**: Include proper error handling and informative output
4. **Document Purpose**: Clear docstring explaining what the example demonstrates
5. **Verify Functionality**: Test examples work with current framework

### Template Structure
```python
#!/usr/bin/env python3
"""
Example Name - Brief Description
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from env_agents.adapters.{service}.enhanced_adapter import ServiceAdapter
from env_agents.core.models import RequestSpec, Geometry

def main():
    # Example implementation
    pass

if __name__ == "__main__":
    exit(main())
```

This ensures examples remain current and functional as the framework evolves.