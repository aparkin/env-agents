# Enhanced Rule pack for NASA POWER - Gold Standard Implementation

# High-confidence exact POWER parameter -> canonical variable mappings
CANONICAL_MAP = {
    # Temperature variables
    "T2M": "atm:air_temperature_2m",              # Temperature at 2 Meters
    "T2M_MAX": "atm:air_temperature_2m_max",      # Temperature at 2 Meters Maximum
    "T2M_MIN": "atm:air_temperature_2m_min",      # Temperature at 2 Meters Minimum
    "T2MDEW": "atm:dew_point_temperature_2m",     # Dew/Frost Point at 2 Meters
    "T2MWET": "atm:wet_bulb_temperature_2m",      # Wet Bulb Temperature at 2 Meters
    
    # Precipitation
    "PRECTOTCORR": "atm:precipitation_corrected", # Precipitation Corrected
    "PRECTOT": "atm:precipitation_total",         # Precipitation
    
    # Solar radiation
    "ALLSKY_SFC_SW_DWN": "atm:solar_irradiance_surface_shortwave", # All Sky Surface Shortwave Downward Irradiance
    "CLRSKY_SFC_SW_DWN": "atm:solar_irradiance_clear_sky_shortwave", # Clear Sky Surface Shortwave Downward Irradiance  
    "ALLSKY_SFC_LW_DWN": "atm:longwave_irradiance_surface_downward", # All Sky Surface Longwave Downward Irradiance
    "ALLSKY_TOA_SW_DWN": "atm:solar_irradiance_toa_shortwave",     # Top-of-atmosphere Shortwave Downward Irradiance
    
    # Wind
    "WS2M": "atm:wind_speed_2m",                  # Wind Speed at 2 Meters
    "WS10M": "atm:wind_speed_10m",                # Wind Speed at 10 Meters  
    "WS50M": "atm:wind_speed_50m",                # Wind Speed at 50 Meters
    "WD2M": "atm:wind_direction_2m",              # Wind Direction at 2 Meters
    "WD10M": "atm:wind_direction_10m",            # Wind Direction at 10 Meters
    
    # Humidity and pressure
    "RH2M": "atm:relative_humidity_2m",           # Relative Humidity at 2 Meters
    "QV2M": "atm:specific_humidity_2m",           # Specific Humidity at 2 Meters
    "PS": "atm:surface_pressure",                 # Surface Pressure
    "SLP": "atm:sea_level_pressure",              # Sea Level Pressure
    
    # Cloud cover and visibility
    "CLOUD_AMT": "atm:cloud_amount_total",        # Cloud Amount
    "CLD_TOT_10M": "atm:cloud_amount_total",      # Total Cloud Amount
    
    # Evapotranspiration and energy
    "EVLAND": "atm:evapotranspiration_land",      # Evaporation Land
    "EVPTRNS": "atm:evapotranspiration_potential", # Evapotranspiration Potential
    
    # Soil moisture and temperature  
    "GWETROOT": "atm:soil_moisture_root_zone",    # Root Zone Soil Wetness
    "GWETTOP": "atm:soil_moisture_surface",       # Surface Soil Wetness
    "TS": "atm:soil_temperature_surface",         # Earth Skin Temperature
}

# Unit alias normalizations for meteorological measurements
UNIT_ALIASES = {
    # Temperature units
    "C": "degC",
    "°C": "degC", 
    "celsius": "degC",
    "F": "degF",
    "°F": "degF",
    "fahrenheit": "degF", 
    "K": "kelvin",
    "kelvin": "K",
    
    # Precipitation units
    "mm/day": "mm/d",
    "mm/hr": "mm/h", 
    "mm day-1": "mm/d",
    "mm hr-1": "mm/h",
    "in/day": "in/d",
    "in/hr": "in/h",
    
    # Solar radiation units
    "MJ/m2/day": "MJ/m^2/d",
    "MJ m-2 day-1": "MJ/m^2/d",
    "W/m2": "W/m^2",
    "W m-2": "W/m^2",
    "kWh/m2/day": "kWh/m^2/d",
    "cal/cm2/day": "cal/cm^2/d",
    "langleys/day": "ly/d",
    
    # Wind speed units
    "m/s": "meters_per_second",
    "m s-1": "meters_per_second", 
    "km/h": "kilometers_per_hour",
    "km hr-1": "kilometers_per_hour",
    "mph": "miles_per_hour",
    "knots": "knots",
    "kt": "knots",
    
    # Pressure units
    "kPa": "kilopascals",
    "hPa": "hectopascals", 
    "mbar": "millibars",
    "mmHg": "mmHg",
    "inHg": "inHg",
    "atm": "atmospheres",
    
    # Humidity units
    "%": "percent",
    "g/kg": "grams_per_kilogram",
    "g kg-1": "grams_per_kilogram",
    
    # Dimensionless ratios
    "1": "dimensionless",
    "unitless": "dimensionless",
    "-": "dimensionless",
}

# Label hints for POWER parameters
LABEL_HINTS = {
    "T2M": "Air temperature at 2 meters",
    "T2M_MAX": "Maximum air temperature at 2 meters",
    "T2M_MIN": "Minimum air temperature at 2 meters", 
    "T2MDEW": "Dew point temperature at 2 meters",
    "T2MWET": "Wet bulb temperature at 2 meters",
    "PRECTOTCORR": "Bias corrected precipitation",
    "PRECTOT": "Total precipitation",
    "ALLSKY_SFC_SW_DWN": "Surface solar irradiance (all sky)",
    "CLRSKY_SFC_SW_DWN": "Surface solar irradiance (clear sky)",
    "ALLSKY_SFC_LW_DWN": "Surface longwave radiation (all sky)",
    "WS2M": "Wind speed at 2 meters",
    "WS10M": "Wind speed at 10 meters",
    "WS50M": "Wind speed at 50 meters", 
    "WD2M": "Wind direction at 2 meters",
    "WD10M": "Wind direction at 10 meters",
    "RH2M": "Relative humidity at 2 meters",
    "QV2M": "Specific humidity at 2 meters",
    "PS": "Surface pressure", 
    "SLP": "Sea level pressure",
    "CLOUD_AMT": "Total cloud amount",
    "EVLAND": "Evaporation from land",
    "EVPTRNS": "Potential evapotranspiration",
    "GWETROOT": "Root zone soil wetness",
    "GWETTOP": "Surface soil wetness",
    "TS": "Earth skin temperature",
}

# Meteorological domain-specific term patterns
TERM_PATTERNS = {
    "temperature": ["temp", "temperature", "thermal", "heat", "cold"],
    "precipitation": ["precip", "rain", "rainfall", "precipitation", "moisture"],
    "solar": ["solar", "radiation", "irradiance", "shortwave", "longwave", "sw", "lw"],
    "wind": ["wind", "speed", "direction", "velocity", "gust"],
    "humidity": ["humid", "moisture", "dew", "wet", "dry", "vapor", "vapour"],
    "pressure": ["pressure", "barometric", "atmospheric"],
    "clouds": ["cloud", "sky", "clear", "overcast", "coverage"],
    "soil": ["soil", "ground", "earth", "surface", "land"],
    "energy": ["energy", "flux", "evaporation", "evapotranspiration"],
}

# NASA POWER community classifications
COMMUNITY_MAPPINGS = {
    "RE": "renewable_energy",       # Renewable Energy
    "AG": "agroclimatology",       # Agroclimatology  
    "SB": "sustainable_buildings", # Sustainable Buildings
}

# Temporal aggregation mappings
TEMPORAL_AGGREGATIONS = {
    "DAILY": "daily",
    "MONTHLY": "monthly", 
    "CLIMATOLOGY": "climatology",
    "HOURLY": "hourly",
}