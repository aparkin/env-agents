# Enhanced Rule pack for OpenAQ v3 - Gold Standard Implementation

# High-confidence exact parameter name -> canonical variable mappings  
CANONICAL_MAP = {
    # Particulate matter
    "pm25": "air:pm25_mass_concentration",
    "pm10": "air:pm10_mass_concentration", 
    "pm1": "air:pm1_mass_concentration",
    
    # Gaseous pollutants
    "o3": "air:ozone_concentration",
    "no2": "air:nitrogen_dioxide_concentration", 
    "no": "air:nitrogen_monoxide_concentration",
    "nox": "air:nitrogen_oxides_concentration",
    "so2": "air:sulfur_dioxide_concentration",
    "co": "air:carbon_monoxide_concentration",
    
    # Volatile organic compounds
    "bc": "air:black_carbon_concentration",
    "voc": "air:volatile_organic_compounds",
    
    # Meteorological (when available from air quality stations)
    "temperature": "air:temperature_c",
    "humidity": "air:relative_humidity_percent",
    "pressure": "air:atmospheric_pressure_hpa",
    "wind_speed": "air:wind_speed_ms",
    "wind_direction": "air:wind_direction_degrees",
}

# Unit alias normalizations for air quality measurements
UNIT_ALIASES = {
    # Concentration units
    "µg/m3": "ug/m^3",
    "ug/m3": "ug/m^3",
    "μg/m³": "ug/m^3",
    "micrograms per cubic meter": "ug/m^3",
    "mg/m3": "mg/m^3",
    "mg/m³": "mg/m^3",
    "milligrams per cubic meter": "mg/m^3",
    
    # Gas concentration units  
    "ppm": "parts_per_million",
    "ppb": "parts_per_billion",
    "ppt": "parts_per_trillion",
    
    # Temperature units
    "°C": "degC",
    "celsius": "degC",
    "°F": "degF", 
    "fahrenheit": "degF",
    "K": "kelvin",
    
    # Pressure units
    "hpa": "hPa",
    "mbar": "mbar",
    "mmhg": "mmHg",
    "inhg": "inHg",
    "kpa": "kPa",
    "pa": "Pa",
    
    # Speed units
    "m/s": "meters_per_second", 
    "km/h": "kilometers_per_hour",
    "mph": "miles_per_hour",
    "knots": "knots",
    
    # Percentage and angles
    "%": "percent",
    "deg": "degrees",
    "°": "degrees",
}

# Label hints for parameter identification
LABEL_HINTS = {
    "pm25": "Fine particulate matter (PM2.5)",
    "pm10": "Inhalable particulate matter (PM10)",
    "pm1": "Ultrafine particulate matter (PM1)",
    "o3": "Ground-level ozone",
    "no2": "Nitrogen dioxide",
    "no": "Nitric oxide", 
    "nox": "Nitrogen oxides",
    "so2": "Sulfur dioxide",
    "co": "Carbon monoxide",
    "bc": "Black carbon",
    "voc": "Volatile organic compounds",
    "temperature": "Ambient air temperature",
    "humidity": "Relative humidity",
    "pressure": "Atmospheric pressure",
    "wind_speed": "Wind speed",
    "wind_direction": "Wind direction",
}

# Air quality domain-specific term patterns
TERM_PATTERNS = {
    "particulates": ["pm", "particulate matter", "particle", "aerosol", "dust"],
    "ozone": ["o3", "ozone", "ground-level ozone", "surface ozone"],
    "nitrogen_compounds": ["no", "no2", "nox", "nitrogen", "nitric", "dioxide"],
    "sulfur_compounds": ["so2", "sulfur", "sulphur", "dioxide"],
    "carbon_compounds": ["co", "carbon", "monoxide", "bc", "black carbon"],
    "meteorology": ["temperature", "humidity", "pressure", "wind", "weather"],
    "organics": ["voc", "organic", "hydrocarbon", "benzene", "toluene"],
}

# OpenAQ-specific aggregation period mappings
AGGREGATION_MAPPINGS = {
    "1 hour": "hourly",
    "24 hour": "daily", 
    "8 hour": "8hour_average",
    "instantaneous": "instantaneous",
    "1 minute": "minutely",
    "raw": "instantaneous",
}

# Data quality indicators from OpenAQ
QUALITY_INDICATORS = {
    "raw": "unprocessed",
    "corrected": "quality_controlled",
    "validated": "validated",
    "provisional": "provisional",
    "final": "final",
}