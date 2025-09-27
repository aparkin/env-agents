
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
import re

from .units import normalize_unit, convertible

# ---- I hate hardcoding but ----
_RULE_MODULE_HINTS = {
    # Force-map dataset ids → rules module paths (explicit overrides)
    "USGS_NWIS": "env_agents.adapters.nwis.rules",
    "NASA_POWER": "env_agents.adapters.power.rules",
    "OpenAQ_v3": "env_agents.adapters.openaq.rules",
    # add others here as needed
}

import importlib, re

def _resolve_rules_module_path(dataset: str) -> list[str]:
    """
    Given a dataset id like 'OpenAQ_v3', return a list of module paths to try
    for a rules pack (most specific → most general).
    """
    ds = (dataset or "").strip()
    tried = []

    # 0) Explicit hint wins
    hint = _RULE_MODULE_HINTS.get(ds)
    if hint:
        tried.append(hint)

    # 1) Normalize (lowercase, strip spaces)
    slug = re.sub(r"[^a-z0-9_]+", "", ds.lower().replace(" ", "_"))

    # 2) Derive base by removing version suffixes: _v3, v3, -v3, _v10, etc.
    base = re.sub(r"[_-]?v\d+$", "", slug)  # openaq_v3 → openaq
    base = re.sub(r"\d+$", "", base)        # foo123 → foo (very defensive)

    # 3) Candidate module paths to try in order
    candidates = [
        f"env_agents.adapters.{slug}.rules",        # e.g., openaq_v3.rules
        f"env_agents.adapters.{slug}_rules",        # openaq_v3_rules
        f"env_agents.adapters.{base}.rules",        # openaq.rules
        f"env_agents.adapters.{base}_rules",        # openaq_rules
    ]
    # Dedup while preserving order
    seen = set()
    out = []
    for c in ([*tried] + candidates):
        if c and c not in seen:
            out.append(c); seen.add(c)
    return out


# ----------------------------
# Utilities
# ----------------------------

def _norm_label(s: Optional[str]) -> str:
    if not s:
        return ""
    s = s.lower().strip()
    # replace separators with space
    s = re.sub(r"[_\-\/]+", " ", s)
    # drop non-alnum+space
    s = re.sub(r"[^a-z0-9 %]+", "", s)
    # collapse spaces
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _starts_or_contains(a: str, b: str) -> bool:
    return a.startswith(b) or (b in a)

@dataclass
class CanonicalVar:
    id: str                     # e.g., "water:discharge_cfs"
    label: str                  # human label
    preferred_unit: Optional[str] = None
    observed_property_uri: Optional[str] = None
    unit_uri: Optional[str] = None
    domain: Optional[str] = None  # water | air | atm | soil | etc.

@dataclass
class NativeParam:
    dataset: str                # e.g., "USGS_NWIS"
    id: str                     # e.g., "00060"
    label: Optional[str]        # e.g., "Discharge"
    unit: Optional[str]         # e.g., "ft3/s"
    domain: Optional[str] = None

@dataclass
class MatchSuggestion:
    dataset: str
    native_id: str
    native_label: Optional[str]
    native_unit: Optional[str]
    canonical: str
    score: float
    reasons: List[str]

# ----------------------------
# Rule pack interface
# ----------------------------

@dataclass
class RulePack:
    exact_map: Dict[str, str]        # native_id -> canonical
    unit_aliases: Dict[str, str]     # unit alias normalization additions (optional)
    label_hints: Dict[str, str]      # native_id -> label hint (optional)

def load_rule_pack(dataset: str) -> Optional[RulePack]:
    """
    Attempts to import adapters.<dataset_name_lower>.rules and retrieve
    CANONICAL_MAP, UNIT_ALIASES, LABEL_HINTS. Missing module is OK.
    """
    mod_name = None
    if dataset.upper() == "NASA_POWER" or dataset.upper() == "POWER":
        mod_name = "env_agents.adapters.power.rules"
    elif dataset.upper() == "USGS_NWIS" or dataset.upper() == "NWIS":
        mod_name = "env_agents.adapters.nwis.rules"
    else:
        # Generic pattern: env_agents.adapters.<lower>/rules.py
        mod_name = f"env_agents.adapters.{dataset.lower()}.rules"
    try:
        m = __import__(mod_name, fromlist=["*"])
    except Exception:
        return None

    exact = getattr(m, "CANONICAL_MAP", {})
    units = getattr(m, "UNIT_ALIASES", {})
    hints = getattr(m, "LABEL_HINTS", {})
    # type fixes
    if not isinstance(exact, dict): exact = {}
    if not isinstance(units, dict): units = {}
    if not isinstance(hints, dict): hints = {}
    return RulePack(exact_map=exact, unit_aliases=units, label_hints=hints)

# ----------------------------
# Term Broker
# ----------------------------

class TermBroker:
    """
    Matches native parameters to canonical variables using:
    - service rule packs (exact id maps + hints + unit aliases)
    - generic label+unit heuristics
    Produces scored suggestions for auto-accept and curation.
    """

    def __init__(self, registry_seed: Dict[str, Any]):
        """
        registry_seed: merged canonical registry dict like
          {
            "variables": {
              "water:discharge_cfs": {
                 "label": "...", "preferred_unit": "ft3/s",
                 "observed_property_uri": "...", "unit_uri": "...", "domain": "water"
              },
              ...
            }
          }
        """
        self._canon: Dict[str, CanonicalVar] = {}
        for cid, meta in (registry_seed.get("variables") or {}).items():
            self._canon[cid] = CanonicalVar(
                id=cid,
                label=str(meta.get("label") or cid),
                preferred_unit=meta.get("preferred_unit"),
                observed_property_uri=meta.get("observed_property_uri"),
                unit_uri=meta.get("unit_uri"),
                domain=meta.get("domain"),
            )

        # Precompute normalized label index
        self._canon_by_label = {}
        for c in self._canon.values():
            self._canon_by_label.setdefault(_norm_label(c.label), []).append(c)

    # ---- scoring helpers ----

    def _score_exact_rule(self, native_id: str, rp: Optional[RulePack]) -> Optional[Tuple[str, float, List[str]]]:
        if not rp or native_id not in rp.exact_map:
            return None
        return (rp.exact_map[native_id], 0.95, [f"exact:{native_id}"])

    def _score_label_hint(self, dataset: str, native_id: str, label: Optional[str], rp: Optional[RulePack]) -> Optional[Tuple[str, float, List[str]]]:
        if not rp:
            return None
        hint = rp.label_hints.get(native_id)
        if not hint:
            return None
        k = _norm_label(hint)
        cands = self._canon_by_label.get(k, [])
        if not cands:
            return None
        # if multiple, pick first; they share same normalized label
        return (cands[0].id, 0.70, [f"label_hint:{native_id}->{hint}"])

    def _score_label_generic(self, label: Optional[str]) -> List[Tuple[str, float, List[str]]]:
        if not label:
            return []
        nl = _norm_label(label)
        out = []
        # exact-normalized label
        if nl in self._canon_by_label:
            out.extend([(c.id, 0.25, [f"label_eq:{label}"]) for c in self._canon_by_label[nl]])
        # contains/startswith loosened
        for k, cands in self._canon_by_label.items():
            if k and _starts_or_contains(nl, k):
                out.extend([(c.id, 0.20, [f"label_contains:{label}->{k}"]) for c in cands])
            elif k and _starts_or_contains(k, nl):
                out.extend([(c.id, 0.10, [f"label_prefix:{label}->{k}"]) for c in cands])
        return out

    def _score_units(self, canonical: CanonicalVar, native_unit: Optional[str]) -> Tuple[float, List[str]]:
        bonus = 0.0
        reasons: List[str] = []
        if not canonical.preferred_unit or not native_unit:
            return bonus, reasons
        nu = normalize_unit(native_unit)
        pu = canonical.preferred_unit
        if nu == pu:
            bonus += 0.03; reasons.append("unit:eq")
        elif convertible(nu, pu):
            bonus += 0.02; reasons.append("unit:convertible")
        return bonus, reasons

    def match(self, dataset: str, natives: List[NativeParam],
              auto_accept_threshold: float = 0.90,
              suggest_threshold: float = 0.60) -> Tuple[List[MatchSuggestion], List[MatchSuggestion]]:
        """
        Returns (accepted, suggestions)
        - accepted: score ≥ auto_accept_threshold
        - suggestions: suggest_threshold ≤ score < auto_accept_threshold
        """
        rp = load_rule_pack(dataset)

        accepted: List[MatchSuggestion] = []
        suggest: List[MatchSuggestion] = []

        for n in natives:
            # aggregate candidate scores per canonical
            cand: Dict[str, Tuple[float, List[str]]] = {}

            # 1) exact rule pack id match
            ex = self._score_exact_rule(n.id, rp)
            if ex:
                cid, sc, rs = ex
                cand[cid] = (cand.get(cid, (0.0, []))[0] + sc, (cand.get(cid, (0.0, []))[1] + rs))

            # 2) label hint from rule pack
            lh = self._score_label_hint(dataset, n.id, n.label, rp)
            if lh:
                cid, sc, rs = lh
                cand[cid] = (cand.get(cid, (0.0, []))[0] + sc, (cand.get(cid, (0.0, []))[1] + rs))

            # 3) generic label scoring
            for cid, sc, rs in self._score_label_generic(n.label):
                cand[cid] = (cand.get(cid, (0.0, []))[0] + sc, (cand.get(cid, (0.0, []))[1] + rs))

            # 4) units bonus
            add_cand = list(cand.items())
            for cid, (sc, rs) in add_cand:
                cv = self._canon.get(cid)
                if not cv:
                    continue
                b, r2 = self._score_units(cv, n.unit)
                if b:
                    cand[cid] = (sc + b, rs + r2)

            # 5) domain bonus (tiny)
            add_cand = list(cand.items())
            for cid, (sc, rs) in add_cand:
                cv = self._canon.get(cid)
                if not cv:
                    continue
                if cv.domain and n.domain and cv.domain == n.domain:
                    cand[cid] = (sc + 0.01, rs + ["domain:eq"])

            if not cand:
                continue

            # pick best
            best_cid, (best_sc, best_rs) = max(cand.items(), key=lambda kv: kv[1][0])
            sug = MatchSuggestion(
                dataset=dataset,
                native_id=n.id,
                native_label=n.label,
                native_unit=n.unit,
                canonical=best_cid,
                score=round(best_sc, 3),
                reasons=best_rs,
            )
            if best_sc >= auto_accept_threshold:
                accepted.append(sug)
            elif best_sc >= suggest_threshold:
                suggest.append(sug)
            # else: drop

        # De-duplicate accepted by (dataset, native_id)
        dedup: Dict[Tuple[str,str], MatchSuggestion] = {}
        for s in accepted:
            key = (s.dataset, s.native_id)
            if key not in dedup or s.score > dedup[key].score:
                dedup[key] = s
        accepted = list(dedup.values())

        return accepted, suggest
