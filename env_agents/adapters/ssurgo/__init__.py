"""
SSURGO (Soil Survey Geographic Database) enhanced adapter.

Provides access to NRCS SSURGO soil survey data with Earth Engine gold standard
metadata richness including pedological context, agricultural applications,
and comprehensive soil property descriptions.
"""

from .adapter import SSURGOAdapter

__all__ = ['SSURGOAdapter']