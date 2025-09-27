"""
Earth Engine Adapter Package

Provides access to Google Earth Engine assets as individual services
within the env-agents framework.
"""

from .gold_standard_adapter import EarthEngineAdapter

__all__ = ['EarthEngineAdapter']