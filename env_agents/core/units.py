
from __future__ import annotations

from typing import Optional, Tuple

# Optional Pint support (preferred for robust conversions)
try:
    import pint  # type: ignore
    _ureg = pint.UnitRegistry(autoconvert_offset_to_baseunit=True)
    # Define common aliases that Pint doesn't include by default
    # Volumetric flow
    _ureg.define("cfs = foot**3 / second = ft3_per_s")
    _ureg.define("cms = meter**3 / second = m3_per_s")
    # Concentration
    _ureg.define("ug_per_m3 = microgram / meter**3")
    _ureg.define("mg_per_m3 = milligram / meter**3")
    # Temperatures handled natively by Pint
except Exception:  # Pint not available
    pint = None
    _ureg = None  # type: ignore

# -------------------------------
# Unit normalization (UCUM-like)
# -------------------------------

# Preferred, normalized strings we use across the project.
# Keep ASCII by default to avoid file-system / CSV encoding issues.
# Example: use "ug/m^3" instead of "µg/m^3".
_UNIT_ALIASES = {
    # volume flow
    "ft3/s": "ft3/s",
    "ft^3/s": "ft3/s",
    "cfs": "ft3/s",
    "ft3 sec-1": "ft3/s",
    "ft^3 sec-1": "ft3/s",
    "cubic feet per second": "ft3/s",
    "cubic foot per second": "ft3/s",
    "m3/s": "m3/s",
    "m^3/s": "m3/s",
    "cms": "m3/s",
    "cubic meters per second": "m3/s",
    "cubic metre per second": "m3/s",

    # length
    "ft": "ft",
    "feet": "ft",
    "foot": "ft",
    "m": "m",
    "meter": "m",
    "metre": "m",

    # temperature
    "degc": "degC",
    "°c": "degC",
    "c": "degC",
    "deg c": "degC",
    "deg c.": "degC",
    "degC": "degC",
    "celsius": "degC",
    "degree celsius": "degC",
    "degf": "degF",
    "°f": "degF",
    "f": "degF",
    "degF": "degF",
    "fahrenheit": "degF",
    "k": "K",
    "kelvin": "K",
    "°k": "K",

    # mass concentration
    "ug/m3": "ug/m^3",
    "µg/m3": "ug/m^3",
    "ug/m^3": "ug/m^3",
    "microgram per cubic meter": "ug/m^3",
    "micrograms per cubic meter": "ug/m^3",
    "mg/m3": "mg/m^3",
    "mg/m^3": "mg/m^3",
    "milligram per cubic meter": "mg/m^3",

    # precipitation depth rate (daily)
    "mm/day": "mm/day",
    "mm d-1": "mm/day",
    "mm per day": "mm/day",
    "inch/day": "in/day",
    "in/day": "in/day",
    "in d-1": "in/day",
    "inches per day": "in/day",
}

# QUDT URIs for normalized units (add as needed)
_QUDT = {
    "ft3/s": "http://qudt.org/vocab/unit/FT3-PER-SEC",
    "m3/s": "http://qudt.org/vocab/unit/M3-PER-SEC",
    "ft": "http://qudt.org/vocab/unit/FT",
    "m": "http://qudt.org/vocab/unit/M",
    "degC": "http://qudt.org/vocab/unit/DEG_C",
    "degF": "http://qudt.org/vocab/unit/DEG_F",
    "K": "http://qudt.org/vocab/unit/K",
    "ug/m^3": "http://qudt.org/vocab/unit/MicroGM-PER-M3",
    "mg/m^3": "http://qudt.org/vocab/unit/MilliGM-PER-M3",
    "mm/day": "http://qudt.org/vocab/unit/MM-PER-DAY",
    "in/day": "http://qudt.org/vocab/unit/IN-PER-DAY",
}

def normalize_unit(u: Optional[str]) -> Optional[str]:
    """Return our normalized UCUM-like unit string, or None if unparseable/empty."""
    if not u:
        return None
    s = str(u).strip()
    if not s:
        return None
    key = s.lower().replace("\\u00b5", "µ").replace("μ", "µ").strip()
    return _UNIT_ALIASES.get(key, s)  # if unknown, keep original

def qudt_uri(u: Optional[str]) -> Optional[str]:
    """Return QUDT URI for a normalized unit string (or None)."""
    nu = normalize_unit(u)
    if not nu:
        return None
    return _QUDT.get(nu)

# -------------------------------
# Conversions
# -------------------------------

# Minimal fallback conversions for when Pint is unavailable.
# For linear conversions, factor/offset pairs: v_to = v_from * factor + offset.
# For temperature, we handle separately below.
_FALLBACK_LINEAR = {
    ("m3/s", "ft3/s"): (35.3146667, 0.0),
    ("ft3/s", "m3/s"): (1.0 / 35.3146667, 0.0),
    ("mg/m^3", "ug/m^3"): (1000.0, 0.0),
    ("ug/m^3", "mg/m^3"): (1/1000.0, 0.0),
    ("mm/day", "in/day"): (1.0 / 25.4, 0.0),
    ("in/day", "mm/day"): (25.4, 0.0),
    ("m", "ft"): (3.280839895, 0.0),
    ("ft", "m"): (1/3.280839895, 0.0),
}

def _convert_temp_fallback(value: float, u_from: str, u_to: str) -> Optional[float]:
    if u_from == u_to:
        return value
    # Celsius <-> Kelvin
    if u_from == "degC" and u_to == "K":
        return value + 273.15
    if u_from == "K" and u_to == "degC":
        return value - 273.15
    # Celsius <-> Fahrenheit
    if u_from == "degC" and u_to == "degF":
        return (value * 9.0/5.0) + 32.0
    if u_from == "degF" and u_to == "degC":
        return (value - 32.0) * 5.0/9.0
    # Fahrenheit <-> Kelvin (via C)
    if u_from == "degF" and u_to == "K":
        return (value - 32.0) * 5.0/9.0 + 273.15
    if u_from == "K" and u_to == "degF":
        return (value - 273.15) * 9.0/5.0 + 32.0
    return None

def convertible(u_from: Optional[str], u_to: Optional[str]) -> bool:
    nu_from = normalize_unit(u_from)
    nu_to = normalize_unit(u_to)
    if not nu_from or not nu_to:
        return False
    if nu_from == nu_to:
        return True
    if pint and _ureg:
        try:
            (_ureg.Quantity(1, nu_from)).to(nu_to)
            return True
        except Exception:
            pass
    if (nu_from, nu_to) in _FALLBACK_LINEAR:
        return True
    # temperature fallback
    if _convert_temp_fallback(0.0, nu_from, nu_to) is not None:
        return True
    return False

def convert_value(value: Optional[float], u_from: Optional[str], u_to: Optional[str]) -> Optional[float]:
    """Convert scalar value between units; returns None if not convertible or value is None."""
    if value is None:
        return None
    nu_from = normalize_unit(u_from)
    nu_to = normalize_unit(u_to)
    if not nu_from or not nu_to:
        return None
    if nu_from == nu_to:
        return float(value)
    # Pint path
    if pint and _ureg:
        try:
            q = _ureg.Quantity(value, nu_from).to(nu_to)
            return float(q.magnitude)
        except Exception:
            # fall back below
            pass
    # Fallback linear
    if (nu_from, nu_to) in _FALLBACK_LINEAR:
        factor, offset = _FALLBACK_LINEAR[(nu_from, nu_to)]
        return float(value) * factor + offset
    # Fallback temperature
    t = _convert_temp_fallback(float(value), nu_from, nu_to)
    if t is not None:
        return float(t)
    return None
