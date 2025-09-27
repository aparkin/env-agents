"""
GBIF (Global Biodiversity Information Facility) adapter.

Provides access to global biodiversity occurrence records with comprehensive
metadata including taxonomic context, conservation status, and ecological applications.
"""

from .adapter import GBIFAdapter

# Legacy alias for backward compatibility
EnhancedGBIFAdapter = GBIFAdapter

__all__ = ['GBIFAdapter', 'EnhancedGBIFAdapter']