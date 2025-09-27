# Soil data adapters
# Using WCS-based adapter for production reliability
from .soilgrids_wcs_adapter import SoilGridsWCSAdapter as SoilGridsAdapter

# Legacy adapters moved to legacy_versions/ folder to avoid confusion
# from .legacy_versions.adapter import SoilGridsAdapter as SoilGridsAdapterLegacy
# from .legacy_versions.wcs_adapter import SoilGridsWCSAdapter as SoilGridsWCSAdapterIntermediate

__all__ = ['SoilGridsAdapter']