"""
Environmental Agents Core Module
Core functionality for environmental data adapters

UNIFIED INTERFACE: Use SimpleEnvRouter as the single router
"""

# Unified router interface
from .simple_router import SimpleEnvRouter
from .models import Geometry, RequestSpec
from .errors import FetchError

# Legacy routers deprecated
# from .router import EnvRouter  # DEPRECATED - use SimpleEnvRouter
# from .unified_router import UnifiedEnvRouter  # DEPRECATED - use SimpleEnvRouter

__all__ = ["SimpleEnvRouter", "Geometry", "RequestSpec", "FetchError"]