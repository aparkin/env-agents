# Historical Documentation Archive

This directory contains archived documentation from previous versions of env-agents.

**Note:** These documents are kept for historical reference only. For current documentation, see [docs/README.md](../README.md).

---

## Archive Organization

### `2025-09-30-dev-notes/`

**Developer notes from production optimization (September 2025)**

These files document the major optimization effort that resulted in 77% performance improvement:

- `ADAPTER_REVIEW.md` - Best practices review of all adapters
- `CHANGELOG_PRODUCTION_ADAPTER.md` - Earth Engine adapter optimization summary
- `CLEANUP_SUMMARY.md` - Legacy code cleanup details
- `EARTH_ENGINE_OPTIMIZATION.md` - Root cause analysis and fixes for EE hanging
- `TIMEOUT_FIX.md` - Threading-based timeout solution

**Replaced by:** [docs/development/LESSONS_LEARNED.md](../development/LESSONS_LEARNED.md) and [docs/operations/EARTH_ENGINE_NOTES.md](../operations/EARTH_ENGINE_NOTES.md)

### `2025-09-29/`

**Service documentation from initial production deployment**

Documentation specific to the initial 16-service pangenome pipeline configuration:

- `CONFIGURED_SERVICES.md` - Original service list
- `EARTH_ENGINE_ASSETS.md` - Earth Engine asset catalog
- `QUICK_START_SERVICES.md` - Quick start for individual services
- `RUN_SERVICES_INDIVIDUALLY.md` - Running services one at a time
- `SERVICE_PLAN.md` - Original deployment plan
- `USGS_NWIS_FIX_SUMMARY.md` - USGS NWIS adapter fixes

**Replaced by:** [docs/SERVICES.md](../SERVICES.md) and [docs/operations/PANGENOME_PIPELINE.md](../operations/PANGENOME_PIPELINE.md)

### `legacy/` (Pre-production)

**Architecture and development docs from initial framework development**

Historical documents from the early development phases:

- Architecture documents (various versions)
- Implementation plans
- Service assessment reports
- Status updates
- Roadmaps

These documents capture the evolution of the framework but are superseded by current documentation.

**Replaced by:** [docs/development/ARCHITECTURE.md](../development/ARCHITECTURE.md) and [docs/API_REFERENCE.md](../API_REFERENCE.md)

---

## Why Archive?

These documents are preserved because they:

1. **Document decision-making** - Show why certain architectural choices were made
2. **Capture lessons learned** - Real-world problems and solutions
3. **Track evolution** - How the framework evolved from concept to production
4. **Provide context** - Background for understanding current implementation

However, they are **not maintained** and may contain outdated information.

---

## Finding Current Documentation

**Instead of using archived docs, see:**

### For Users
- [Installation](../INSTALLATION.md)
- [Quick Start](../QUICK_START.md)
- [Services Guide](../SERVICES.md)
- [API Reference](../API_REFERENCE.md)

### For Operators
- [Database Management](../operations/DATABASE_MANAGEMENT.md)
- [Pangenome Pipeline](../operations/PANGENOME_PIPELINE.md)
- [Earth Engine Operations](../operations/EARTH_ENGINE_NOTES.md)

### For Developers
- [Architecture](../development/ARCHITECTURE.md)
- [Local Development](../development/LOCAL_DEVELOPMENT.md)
- [Lessons Learned](../development/LESSONS_LEARNED.md)
- [Adding Services](../EXTENDING_SERVICES.md)

---

**Back to:** [Documentation Index](../README.md)