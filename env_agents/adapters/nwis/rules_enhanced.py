# Enhanced Rule pack for USGS NWIS - Gold Standard Implementation

# High-confidence exact native id -> canonical variable mappings
CANONICAL_MAP = {
    # Water flow and levels
    "00060": "water:discharge_cfs",           # Discharge, cubic feet per second
    "00061": "water:discharge_instantaneous", # Discharge, instantaneous
    "00065": "water:gage_height_ft",          # Gage height, feet
    
    # Water temperature
    "00010": "water:temperature_c",           # Temperature, water, degrees Celsius
    "00020": "water:temperature_f",           # Temperature, water, degrees Fahrenheit
    
    # Water chemistry - dissolved constituents
    "00095": "water:specific_conductance",    # Specific conductance, microsiemens per centimeter
    "00300": "water:dissolved_oxygen",        # Dissolved oxygen, milligrams per liter
    "00400": "water:ph",                      # pH, standard units
    "00403": "water:ph_lab",                  # pH, water, unfiltered, laboratory
    
    # Nutrients
    "00618": "water:nitrate_nitrogen",        # Nitrate, water, filtered, milligrams per liter as nitrogen
    "00631": "water:nitrite_plus_nitrate_n",  # Nitrite plus nitrate, dissolved
    "00665": "water:phosphorus_total",        # Phosphorus, water, unfiltered, milligrams per liter
    
    # Turbidity and solids
    "00076": "water:turbidity",               # Turbidity, water, unfiltered, nephelometric turbidity ratio units
    "80154": "water:suspended_sediment",      # Suspended sediment concentration, milligrams per liter
    
    # Major ions
    "00940": "water:chloride",                # Chloride, water, filtered, milligrams per liter
    "00945": "water:sulfate",                 # Sulfate, water, filtered, milligrams per liter
    "00915": "water:calcium",                 # Calcium, water, filtered, milligrams per liter
    "00925": "water:magnesium",               # Magnesium, water, filtered, milligrams per liter
    
    # Meteorological (often co-collected)
    "00045": "water:precipitation_total",     # Precipitation, total, inches
    "00020": "air:temperature_c",            # Air temperature (when measured at water sites)
}

# Unit alias normalizations extending core units table
UNIT_ALIASES = {
    # Flow units
    "cfs": "ft3/s",
    "ft^3/s": "ft3/s", 
    "cubic feet per second": "ft3/s",
    "cms": "m3/s",
    "m^3/s": "m3/s",
    "cubic meters per second": "m3/s",
    
    # Temperature units
    "deg c": "degC",
    "degrees celsius": "degC",
    "deg f": "degF", 
    "degrees fahrenheit": "degF",
    
    # Conductivity units
    "us/cm": "uS/cm",
    "microsiemens per centimeter": "uS/cm",
    "umho/cm": "uS/cm",
    
    # Concentration units
    "mg/l": "mg/L",
    "milligrams per liter": "mg/L",
    "ppm": "mg/L",  # parts per million (for water)
    
    # Turbidity units
    "ntu": "NTU",
    "nephelometric turbidity units": "NTU",
    "fnu": "FNU",
    
    # Length units
    "ft": "feet",
    "feet": "ft",
    "m": "meters",
    "meters": "m",
    "in": "inches",
    "inches": "in",
}

# Label hints for improved semantic matching
LABEL_HINTS = {
    "00060": "Stream discharge",
    "00065": "Gage height", 
    "00010": "Water temperature",
    "00095": "Specific conductance",
    "00300": "Dissolved oxygen",
    "00400": "pH",
    "00618": "Nitrate as nitrogen",
    "00665": "Total phosphorus",
    "00076": "Turbidity",
    "80154": "Suspended sediment concentration",
    "00940": "Chloride",
    "00945": "Sulfate",
    "00915": "Calcium",
    "00925": "Magnesium",
    "00045": "Total precipitation",
}

# Domain-specific term patterns for enhanced matching
TERM_PATTERNS = {
    "flow": ["discharge", "flow", "streamflow", "river flow"],
    "level": ["gage height", "stage", "water level", "elevation"],
    "temperature": ["temp", "temperature", "thermal"],
    "chemistry": ["conductivity", "ph", "dissolved", "concentration"],
    "nutrients": ["nitrogen", "phosphorus", "nitrate", "nitrite", "nutrient"],
    "solids": ["turbidity", "sediment", "suspended", "clarity"],
    "ions": ["chloride", "sulfate", "calcium", "magnesium", "sodium", "ion"],
}

# Quality assurance mappings for NWIS-specific QC flags
QC_FLAG_MAPPINGS = {
    "A": "approved",           # Approved for publication -- Processing and review completed
    "P": "provisional",        # Provisional data subject to revision  
    "e": "estimated",          # Estimated
    "R": "revised",           # Revised
    "": "unknown",            # No qualification code
}

# Statistical code mappings for daily values
STAT_CODE_MAPPINGS = {
    "00001": "maximum",
    "00002": "minimum", 
    "00003": "mean",
    "00006": "sum",
    "00008": "median",
}