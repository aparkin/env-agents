# env_agents/core/router.py

from __future__ import annotations
import pandas as pd
from typing import Dict, Any, List
from .registry import RegistryManager
from .models import RequestSpec, CORE_COLUMNS
from .errors import FetchError
from datetime import datetime, timezone
from .ids import compute_observation_id as _cid

from datetime import datetime, timezone

from .term_broker import TermBroker
from .semantics import attach_semantics


class EnvRouter:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.registry = RegistryManager(base_dir)
        self.adapters: Dict[str, Any] = {}

    def register(self, adapter) -> None:
        adapter._router_ref = self
        self.adapters[adapter.DATASET] = adapter

    def list_adapters(self) -> List[str]:
        return sorted(self.adapters.keys())

    def capabilities(self) -> Dict[str, Any]:
        caps = {}
        for k, a in self.adapters.items():
            try:
                caps[k] = a.capabilities()
            except Exception as e:
                caps[k] = {"error": str(e)}
        return caps

    def _attach_meta(self, df: pd.DataFrame, adapter) -> pd.DataFrame:
        df.attrs["schema"] = {"core_columns": CORE_COLUMNS}
        df.attrs["capabilities"] = adapter.capabilities()
        df.attrs["variable_registry"] = self.registry.merged()
        return df

    def fetch(self, dataset: str, spec: RequestSpec) -> pd.DataFrame:
        if dataset not in self.adapters:
            raise FetchError(f"Adapter not registered: {dataset}")
        adapter = self.adapters[dataset]

        # 1) Fetch from adapter
        df = adapter.fetch(spec)

        # 2) Ensure all core columns exist (structure guard)
        for col in CORE_COLUMNS:
            if col not in df.columns:
                df[col] = None

        # 3) Ensure retrieval timestamp (only if missing)
        if ("retrieval_timestamp" not in df.columns) or df["retrieval_timestamp"].isna().all():
            df["retrieval_timestamp"] = datetime.now(timezone.utc).isoformat()

        # 4) Attach semantics (ontology URIs, preferred units, conversions, and/or canonical variable mapping)
        #    Build broker from merged registry; broker will also pick up per-service rules packs.
        # semantics
        try:
            registry = self.registry.merged()
            from env_agents.core.term_broker import TermBroker
            from env_agents.core.semantics import attach_semantics
            broker = TermBroker(registry)
            df = attach_semantics(df, broker, dataset)
        except Exception:
            pass

        # ensure semantic columns exist even if attach_semantics no-oped
        for _col in ("observed_property_uri", "unit_uri", "preferred_unit"):
            if _col not in df.columns:
                df[_col] = None


        # 5) Final guard: keep IDs canonical if anything changed (e.g., variable remapped)
        #    Recompute observation_id unconditionally to avoid subtle drift.
        if "observation_id" not in df.columns or df["observation_id"].isna().any():
            df["observation_id"] = _cid(df)
        else:
            recomputed = _cid(df)
            # If adapter provided IDs but semantics changed a key, overwrite with canonical IDs
            if not recomputed.equals(df["observation_id"]):
                df["observation_id"] = recomputed

        # 6) Preserve any new semantic cols while ordering cores first
        core_first = [c for c in CORE_COLUMNS if c in df.columns]
        extras = [c for c in df.columns if c not in CORE_COLUMNS]
        df = df[core_first + extras]

        # 7) Attach meta (schema, capabilities, registry)
        return self._attach_meta(df, adapter)

    def refresh_capabilities(self, *, extra_by_dataset: dict | None = None, write: bool = True) -> dict:
        """
        Call adapter.capabilities() for all registered adapters and persist the
        results into registry/registry_harvest.json via RegistryManager.

        - extra_by_dataset: optional dict of {DATASET: extra_kwargs} to pass through
          to adapter.capabilities(extra).
        - write=False returns the dict without touching disk.
        """
        harvest: dict[str, dict] = {}
        for ds, adapter in self.adapters.items():
            try:
                extra = (extra_by_dataset or {}).get(ds)
                caps  = adapter.capabilities(extra)
                harvest[ds] = {
                "dataset": caps.get("dataset", getattr(adapter, "DATASET", ds)),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "variables": caps.get("variables", []),               # list of {canonical, platform, unit, description?, uri?}
                "attributes_schema": caps.get("attributes_schema", {}),# declared native attributes
                "rate_limits": caps.get("rate_limits", {}),
                "notes": caps.get("notes", ""),
                # Optional extras many adapters may provide:
                **({"statistics": caps["statistics"]} if "statistics" in caps else {}),
                **({"units": caps["units"]}             if "units" in caps else {}),
                **({"discovery_status": caps["discovery_status"]} if "discovery_status" in caps else {}),
                **({"capabilities_schema_version": caps["capabilities_schema_version"]} if "capabilities_schema_version" in caps else {}),
                }
            except Exception as e:
                harvest[ds] = {"dataset": ds, "error": str(e)}

        if write:
            self.registry.write_harvest(harvest)
            # Important: ensure subsequent calls see the new harvest
            if hasattr(self.registry, "reload"):
                self.registry.reload()
            elif hasattr(self.registry, "invalidate_cache"):
                self.registry.invalidate_cache()

        return harvest
