# env_agents/core/semantics.py
from __future__ import annotations
import pandas as pd
from typing import Any

RAW_PREFIX = "raw:"

def _get_native_hint(attrs: Any) -> tuple[str|None, str|None, str|None]:
    """
    Returns (native_id, native_label, native_unit) if present.
    """
    if not isinstance(attrs, dict):
        return None, None, None
    nat = attrs.get("native")
    if isinstance(nat, dict):
        return nat.get("id"), nat.get("label"), nat.get("unit")
    return None, None, None

def attach_semantics(df: pd.DataFrame, broker, dataset: str) -> pd.DataFrame:
    """
    Adds (or ensures) semantic columns:
      - observed_property_uri
      - unit_uri
      - preferred_unit
      - value_converted (optional, when conversion is known)

    May also remap df['variable'] from 'raw:*' to canonical when confident.
    Never mutates df['value'] or df['unit'].
    """
    # Ensure columns exist even for empty frames
    for col in ("observed_property_uri", "unit_uri", "preferred_unit"):
        if col not in df.columns:
            df[col] = None
    if df.empty:
        return df

    # Work row-by-row (small frames) or vectorize later if needed
    for i in df.index:
        var = df.at[i, "variable"] if "variable" in df.columns else None
        unit = df.at[i, "unit"] if "unit" in df.columns else None

        # Try to promote raw variables using native hints
        if isinstance(var, str) and var.startswith(RAW_PREFIX):
            attrs = df.at[i, "attributes"] if "attributes" in df.columns else None
            native_id, native_label, native_unit = _get_native_hint(attrs)
            try:
                # Prefer an explicit native id; broker should look in rule pack first, then registry
                mapped = None
                if native_id:
                    mapped = broker.match_one(dataset, native_id=native_id, native_label=native_label, native_unit=native_unit)
                elif native_label or native_unit:
                    mapped = broker.match_one(dataset, native_label=native_label, native_unit=native_unit)

                if mapped and mapped.get("canonical") and float(mapped.get("confidence", 1.0)) >= 0.9:
                    df.at[i, "variable"] = mapped["canonical"]
                    # Attach a light trace
                    if "attributes" in df.columns and isinstance(attrs, dict):
                        attrs = dict(attrs)
                        attrs["mapping_source"] = mapped.get("source", "rules/registry")
                        df.at[i, "attributes"] = attrs
            except Exception:
                # fail soft
                pass

        # Lookup canonical metadata
        var = df.at[i, "variable"] if "variable" in df.columns else None
        meta = None
        try:
            meta = broker.lookup_canonical(var) if var else None
        except Exception:
            meta = None

        # Fill semantic columns
        if meta:
            if "observed_property_uri" in meta and df.at[i, "observed_property_uri"] in (None, pd.NA):
                df.at[i, "observed_property_uri"] = meta.get("observed_property_uri")
            if "unit_uri" in meta and df.at[i, "unit_uri"] in (None, pd.NA):
                df.at[i, "unit_uri"] = meta.get("unit_uri")
            if df.at[i, "preferred_unit"] in (None, pd.NA):
                df.at[i, "preferred_unit"] = meta.get("preferred_unit") or unit

            # Optional conversion (non-destructive)
            try:
                if "value" in df.columns:
                    v = df.at[i, "value"]
                    preferred = meta.get("preferred_unit")
                    if v is not None and unit and preferred and preferred != unit:
                        conv = broker.convert_value(var, v, unit)
                        if conv is not None:
                            # Create the column if not present
                            if "value_converted" not in df.columns:
                                df["value_converted"] = None
                            df.at[i, "value_converted"] = conv
            except Exception:
                pass
        else:
            # No meta: still make sure preferred_unit has something sensible
            if df.at[i, "preferred_unit"] in (None, pd.NA):
                df.at[i, "preferred_unit"] = unit

    return df
