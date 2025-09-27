"""
Water Quality Portal (WQP) adapter.

Provides access to comprehensive water quality data from the Water Quality Portal
with rich metadata including parameter definitions, regulatory context, and environmental applications.
"""

from .adapter import WQPAdapter

# Legacy alias for backward compatibility
EnhancedWQPAdapter = WQPAdapter

__all__ = ['WQPAdapter', 'EnhancedWQPAdapter']