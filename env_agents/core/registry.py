from __future__ import annotations
import json, os
from typing import Dict, Any
import pathlib, datetime

class RegistryManager:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.seed_path = os.path.join(base_dir, "env_agents", "registry", "registry_seed.json")
        self.harvest_path = os.path.join(base_dir, "env_agents", "registry", "registry_harvest.json")
        self.overrides_path = os.path.join(base_dir, "env_agents", "registry", "registry_overrides.json")
        self.delta_path = os.path.join(base_dir, "env_agents", "registry", "registry_delta.json")
        for p in [self.seed_path, self.harvest_path, self.overrides_path, self.delta_path]:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            if not os.path.exists(p):
                with open(p, "w", encoding="utf-8") as f:
                    json.dump({} if "seed" not in p else {"variables":{}, "units":{}, "methods":{}, "qc_flags":{}}, f, indent=2, ensure_ascii=False)
        self._reg_dir = pathlib.Path(base_dir) / "registry"
        self._reg_dir.mkdir(parents=True, exist_ok=True)
        
    def _load(self, p: str) -> Dict[str, Any]:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, p: str, obj: Dict[str, Any]):
        with open(p, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, ensure_ascii=False)

    def merged(self) -> Dict[str, Any]:
        def merge(a,b):
            out = dict(a); out.update(b); return out
        seed = self._load(self.seed_path)
        harv = self._load(self.harvest_path)
        over = self._load(self.overrides_path)
        return {
            "variables": merge(seed.get("variables",{}), merge(harv.get("variables",{}), over.get("variables",{}))),
            "units":     merge(seed.get("units",{}),     merge(harv.get("units",{}),     over.get("units",{}))),
            "methods":   merge(seed.get("methods",{}),   merge(harv.get("methods",{}),   over.get("methods",{}))),
            "qc_flags":  merge(seed.get("qc_flags",{}),  merge(harv.get("qc_flags",{}),  over.get("qc_flags",{}))),
        }

    def record_unknown(self, dataset: str, native: str, example: Dict[str, Any]):
        delta = self._load(self.delta_path)
        bucket = delta.setdefault(dataset, {})
        bucket.setdefault(native, []).append(example)
        self._save(self.delta_path, delta)

    def write_harvest(self, harvest: dict) -> None:
        path = self._reg_dir / "registry_harvest.json"
        # merge with existing if present
        old = {}
        if path.exists():
            try:
                old = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                old = {}
        old.update(harvest)
        path.write_text(json.dumps(old, indent=2), encoding="utf-8")
