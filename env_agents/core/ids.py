# env_agents/core/ids.py
from __future__ import annotations
import hashlib
import numpy as np
import pandas as pd

LATLON_DP = 6  # spec: hash on 6 dp

def _decide_instant_or_daily(t_raw, cov_hint: str | None) -> str:
    """
    Returns 'instant' or 'daily' using:
    1) temporal_coverage hint if provided,
    2) otherwise: if time-of-day != 00:00:00 -> instant, else daily.
    """
    if cov_hint:
        s = str(cov_hint).lower()
        if "instant" in s:
            return "instant"
        if "daily" in s:
            return "daily"

    # Fallback: inspect the parsed datetime
    if t_raw is None or (isinstance(t_raw, float) and np.isnan(t_raw)):
        return "daily"  # arbitrary but stable for missing time
    try:
        dt = pd.to_datetime(t_raw, utc=True)
        # If any sub-day component exists, treat as instant
        if getattr(dt, "hour", 0) or getattr(dt, "minute", 0) or getattr(dt, "second", 0):
            return "instant"
        return "daily"
    except Exception:
        # Last resort: string heuristic
        return "instant" if ("T" in str(t_raw)) else "daily"

def _norm_time_for_id(t_raw, cov_hint: str | None) -> str:
    if t_raw is None or (isinstance(t_raw, float) and np.isnan(t_raw)):
        return ""
    try:
        dt = pd.to_datetime(t_raw, utc=True)
    except Exception:
        # If totally unparseable, just return the raw string (stable)
        return str(t_raw)

    mode = _decide_instant_or_daily(t_raw, cov_hint)
    if mode == "instant":
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        return dt.strftime("%Y-%m-%d")

def compute_observation_id(df: pd.DataFrame) -> pd.Series:
    lat = pd.to_numeric(df.get("latitude"), errors="coerce").round(LATLON_DP)
    lon = pd.to_numeric(df.get("longitude"), errors="coerce").round(LATLON_DP)

    cov = df.get("temporal_coverage")
    cov_vals = cov if cov is not None else pd.Series([""] * len(df), index=df.index)

    # build the normalized time string with coverage hint
    time_norm = pd.Series(index=df.index, dtype=object)
    for i in df.index:
        time_norm.loc[i] = _norm_time_for_id(df.at[i, "time"] if "time" in df.columns else None,
                                             cov_vals.at[i] if i in cov_vals.index else None)

    # Helper function to safely get series with fillna
    def get_series(df, col, default=""):
        if col in df.columns:
            return df[col].fillna(default).astype(str)
        else:
            return pd.Series([default] * len(df), index=df.index, dtype=str)
    
    parts = (
        get_series(df, "dataset") + "|" +
        get_series(df, "spatial_id") + "|" +
        time_norm.astype(str) + "|" +
        get_series(df, "variable") + "|" +
        get_series(df, "depth_top_cm") + "|" +
        get_series(df, "depth_bottom_cm") + "|" +
        lat.map(lambda v: "" if pd.isna(v) else f"{float(v):.{LATLON_DP}f}") + "|" +
        lon.map(lambda v: "" if pd.isna(v) else f"{float(v):.{LATLON_DP}f}")
    )
    return parts.map(lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest())

