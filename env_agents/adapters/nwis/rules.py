
# Rule pack for USGS NWIS

# Exact native id -> canonical variable id
CANONICAL_MAP = {
    "00060": "water:discharge_cfs",   # Discharge
    "00065": "water:gage_height_ft",  # Gage height
    "00010": "water:water_temp_c",    # Temperature, water
    # add more as you curate...
}

# Unit alias normalizations extending core units table (optional)
UNIT_ALIASES = {
    "cfs": "ft3/s",
    "ft^3/s": "ft3/s",
    "cms": "m3/s",
    "deg c": "degC",
    "deg f": "degF",
}

# Optional label hints (native_id -> canonical label string)
LABEL_HINTS = {
    "00060": "Stream discharge",
    "00065": "Gage height",
    "00010": "Water temperature",
}
