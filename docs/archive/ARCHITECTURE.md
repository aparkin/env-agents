# env-agents: Semantics-Centered Architecture (v0.2)

A modular, ontology-aware framework for discovering, fetching, and harmonizing public environmental data via uniform adapters—returning tidy, analysis-ready tables with rich, machine-readable metadata.

This update introduces a **Term Broker**, **service rule packs**, and a **single units/ontology layer** so new services and parameters can be added with *minimal* hand curation.

---

## Why this update?

If adapters decide canonical variables and do unit handling, the system becomes hard to maintain. We centralize semantics so adapters only fetch native rows and (optionally) expose native catalogs.

**Key ideas**

- **Adapters are thin**: fetch rows + provide a `harvest()` of native parameters (if available).
- **Broker is smart**: maps native → canonical once, with confidence scoring and provenance.
- **Units are global**: one unit alias table (UCUM-like strings), optional Pint conversions, and QUDT URIs—used everywhere, not per adapter.
- **Registry is durable**: seed canonicals + harvested catalogs + accepted overrides + unknown deltas.
- **Auto-expansion**: new upstream parameters are harvested; high-confidence matches are auto-accepted; the rest go to a small review queue.

---

## Canonical Row Model (unchanged)

Each adapter returns one tidy DataFrame with **core columns** (no sparse kitchen-sink). Service-specific richness is in `attributes` with an `attributes_schema` declared in `capabilities()`.

Core columns (always present):

- `observation_id, dataset, source_url, source_version, license, retrieval_timestamp`
- `geometry_type, latitude, longitude, geom_wkt, spatial_id, site_name, admin, elevation_m`
- `time, temporal_coverage, variable, value, unit, depth_top_cm, depth_bottom_cm, qc_flag`
- `attributes, provenance`

Adapters should also add `attributes["terms"] = [f"{DATASET}:param:{native_id}"]` so the native variable is traceable.

---

## Semantics Pipeline

```
Adapter.harvest() ─┐
Adapter.capabilities() (fallback) ➜  Router.refresh_capabilities()
                                        ├─ writes registry/harvest/{dataset}.json
                                        ├─ TermBroker.match() over harvest items
                                        │     ├─ service rule pack (exact code maps, aliases, label hints)
                                        │     ├─ generic label+unit rules
                                        │     └─ confidence + provenance
                                        ├─ auto-accept ≥ 0.90 → registry_overrides.json
                                        └─ 0.60–0.89 → registry_delta.json for review
                                      
Adapter.fetch() → tidy rows → Router.attach_meta(df) → attach_semantics(df, merged_registry)
```

**At fetch-time** we do *not* guess semantics. We consult the **accepted overrides + seed** to attach URIs and optionally compute `value_converted` to preferred units.

---

## Files and Responsibilities

```
env_agents/
  core/
    units.py           # normalize units (UCUM-like) + QUDT URIs; Pint conversions if available
    term_broker.py     # matching engine + scoring + suggestions
    semantics.py       # attach_semantics (URIs & conversions), normalize_units helper
    router_ext.py      # refresh_capabilities(router): harvest + broker + write registry files
  adapters/
    power/rules.py     # tiny CANONICAL_MAP, UNIT_ALIASES, optional LABEL_HINTS
    nwis/rules.py      # tiny CANONICAL_MAP, UNIT_ALIASES
  registry/
    registry_seed.json       # curated canonicals (URIs + preferred units)
    registry_overrides.json  # accepted dataset→native mappings
    registry_delta.json      # to-review suggestions
    harvest/                 # auto-harvested catalogs (json by dataset)
    vendor/                  # optional vendored catalogs (e.g., NWIS pmcodes snapshot)
  cli/
    ea.py              # small CLI: list-unknowns, promote (not required for runtime)
```

Adapters keep their existing `fetch()`; adding a `harvest()` is recommended but optional—`refresh_capabilities` falls back to `capabilities()["variables"]` when `harvest()` is missing.

---

## Confidence & Auto-accept Rules

TermBroker score (0–1) from independent signals:

- Service rule pack **exact id** map → +0.95  
- Service **label hint** → +0.70  
- Generic **label equality** (normalized) → +0.25  
- Generic **label fuzzy-ish** (contains / startswith) → +0.10–0.20  
- **Units** sanity: equals preferred (+0.03), in alt units (+0.02), convertible/known (+0.01)  
- **Domain** hint match (adapter may declare `"domain"`) → +0.01

Thresholds (configurable):
- **≥ 0.90**: auto-accept to `registry_overrides.json`
- **0.60–0.89**: write to `registry_delta.json` for review
- **< 0.60**: leave unmapped (rows carry `raw:{dataset}:{native}` until curated)

Every suggestion carries **provenance**: which rules matched, which unit alias was used, and what catalog item was considered.

---

## Units & Ontologies (one layer)

- **UCUM-like strings** (e.g., `"ft3/s"`, `"degC"`, `"µg/m^3"`) standardized by `core/units.py`.
- **QUDT URIs** provided per unit (`"http://qudt.org/vocab/unit/FT3-PER-SEC"` etc.).
- **Observed property URIs** per **canonical variable** in `registry_seed.json` (often CF Standard Names).
- **Pint** is optional. If present, it does conversions (including offsets). If not, `units.py` falls back to a small conversion table for common pairs.

Add unit aliases **once**; all services benefit.

---

## Operations

### Refresh catalogs & mappings
In notebooks:
```python
from env_agents.core.router_ext import refresh_capabilities
report = refresh_capabilities(router, auto_accept_threshold=0.9, suggest_threshold=0.6)
```

- Calls each adapter’s `harvest()` (or uses `capabilities()` fallback), writes `registry/harvest/*.json`.
- Runs TermBroker; updates `registry_overrides.json` and `registry_delta.json`.

### Review & promote (optional helper CLI)
```
$ ea list-unknowns
$ ea promote --dataset USGS_NWIS --native 00095 --canonical water:specific_conductance_us_cm
```

### CI suggestions
- Nightly `refresh_capabilities` with **no auto-accept** to create a PR with updated `harvest/` and `delta`.
- Manual promotion triggers a small PR that only touches `registry_overrides.json`.

---

## Adapter Checklist

- Keep `fetch()` contract as-is.
- Add `attributes["terms"] = [f"{DATASET}:param:{native_id}"]` on each row (native trace).
- Implement `harvest()` returning native params (`id`, `label`, `unit`, `domain?`). If not feasible now, ensure `capabilities()["variables"]` includes `platform` (native id) and `unit` so fallback harvest works.

---

## Minimal Curation Footprint

- **Day 1**: seed a few dozen canonicals (water discharge/height/temp; air PM2.5/O3; atm temp/precip/irradiance; key soils).
- **Broker** + rule packs auto-map 70–95% of service catalogs.
- **New upstream params** land in `delta` for one-click acceptance.
- **Unit alias additions** immediately apply everywhere.

---

## Roadmap

- Add OpenAQ, AQS rule packs.
- Add WQP/NWIS scripted harvesters (reading vendored TSVs or stable endpoints).
- JSON-LD export (`to_jsonld`) for SOSA/SSN + PROV-O using canonical variable URIs & unit URIs.
- Lightweight UI for reviewing `registry_delta.json`.
