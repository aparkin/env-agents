# Canonical Environmental Data Adapters
# Updated after Phase 2A: Standardized Naming

from .base import BaseAdapter

# CANONICAL ADAPTERS (Standard Services) - Clean Naming
from .power.adapter import NASAPowerAdapter as NASA_POWER
from .soil.soilgrids_wcs_adapter import SoilGridsWCSAdapter as SoilGrids
from .openaq.adapter import OpenAQAdapter as OpenAQ
from .gbif.adapter import GBIFAdapter as GBIF
from .wqp.adapter import WQPAdapter as WQP
from .overpass.adapter import OverpassAdapter as OSM_Overpass
from .air.adapter import EPAAQSAdapter as EPA_AQS
from .nwis.adapter import USGSNWISAdapter as USGS_NWIS
from .ssurgo.adapter import SSURGOAdapter as SSURGO

# META-SERVICES - Clean Naming
from .earth_engine.gold_standard_adapter import EarthEngineAdapter as EARTH_ENGINE

# Canonical service list for programmatic access
CANONICAL_SERVICES = {
    'NASA_POWER': NASA_POWER,
    'SoilGrids': SoilGrids,
    'OpenAQ': OpenAQ,
    'GBIF': GBIF,
    'WQP': WQP,
    'OSM_Overpass': OSM_Overpass,
    'EPA_AQS': EPA_AQS,
    'USGS_NWIS': USGS_NWIS,
    'SSURGO': SSURGO,
    'EARTH_ENGINE': EARTH_ENGINE
}

# All available adapters (for backward compatibility)
__all__ = [
    'BaseAdapter',
    'NASA_POWER',
    'SoilGrids',
    'OpenAQ',
    'GBIF',
    'WQP',
    'OSM_Overpass',
    'EPA_AQS',
    'USGS_NWIS',
    'SSURGO',
    'EARTH_ENGINE',
    'CANONICAL_SERVICES'
]