"""
Earth Engine Adapter Package

Provides access to Google Earth Engine assets as individual services
within the env-agents framework.
"""

from .production_adapter import ProductionEarthEngineAdapter as EarthEngineAdapter

__all__ = ['EarthEngineAdapter']