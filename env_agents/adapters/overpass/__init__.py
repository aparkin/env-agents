"""
OpenStreetMap Overpass API adapter.

Provides access to OpenStreetMap geographic features with comprehensive
metadata including infrastructure context, urban planning applications,
and geospatial analytics.
"""

from .adapter import OverpassAdapter

# Legacy alias for backward compatibility
EnhancedOverpassAdapter = OverpassAdapter

__all__ = ['OverpassAdapter', 'EnhancedOverpassAdapter']