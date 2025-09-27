"""
env-agents: Extensible Environmental Data Retrieval Framework

Simple 3-method interface for environmental data services:
1. register() - Add environmental services
2. discover() - Find services and capabilities  
3. fetch() - Get environmental data

Perfect for agents and interactive analysis!
"""

# Primary interface (Simplified Phase 2)
from .core.simple_router import SimpleEnvRouter

# Core data models
from .core.models import RequestSpec, Geometry

# Advanced interfaces (for power users)
from .core.unified_router import UnifiedEnvRouter
from .core.metadata_schema import ServiceMetadata
from .core.discovery_engine import DiscoveryQuery, SearchResult

# Legacy interfaces (backward compatibility)
from .core.router import EnvRouter
from .core.registry import RegistryManager

__version__ = '1.0.0'
__all__ = [
    # Primary interface (recommended)
    'SimpleEnvRouter',
    
    # Core models
    'RequestSpec', 
    'Geometry',
    
    # Advanced interfaces
    'UnifiedEnvRouter', 
    'ServiceMetadata',
    'DiscoveryQuery',
    'SearchResult',
    
    # Legacy interfaces (backward compatibility)
    'EnvRouter',
    'RegistryManager',
    
    # Modules
    'core', 
    'adapters'
]

# Make SimpleEnvRouter the default import
EnvRouter = SimpleEnvRouter  # Alias for backward compatibility
