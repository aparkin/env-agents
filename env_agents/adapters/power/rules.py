# Rule pack for NASA POWER
# Map POWER parameter ids (e.g., "T2M") to your canonical variables when safe.
CANONICAL_MAP = {
    # "T2M": "atm:t2m",
    # "PRECTOTCORR": "atm:precip",
    # "ALLSKY_SFC_SW_DWN": "atm:allsky_sfc_sw_down",
}
UNIT_ALIASES = {
    # extend unit aliases if POWER returns variants
}
LABEL_HINTS = {
    # optional: "T2M": "Air temperature at 2m"
}
