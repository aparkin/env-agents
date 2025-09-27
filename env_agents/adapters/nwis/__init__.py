# Package facade for USGS NWIS
from .adapter import USGSNWISAdapter

# Legacy aliases for backward compatibility
USGSNWISEnhancedAdapter = USGSNWISAdapter
UsgsNwisLiveAdapter = USGSNWISAdapter
NWISEnhancedAdapter = USGSNWISAdapter

__all__ = ["USGSNWISAdapter", "USGSNWISEnhancedAdapter", "UsgsNwisLiveAdapter", "NWISEnhancedAdapter"]