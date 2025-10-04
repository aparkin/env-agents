# Database Integrity Diagnosis

**Date**: 2025-10-03
**Issue**: Massive data loss in `env_observations` table - only **9.9%** of expected observations present

---

## Summary

The database shows severe data integrity issues with **13 of 15 services** critically affected:

- **Expected**: 16,994,578 observations
- **Actual**: 1,688,469 observations
- **Lost**: 15,306,109 observations (90.1% loss!)

## Root Cause Analysis

### The Problem

The `env_observations` table uses `PRIMARY KEY (obs_id, service_name)` with `INSERT OR REPLACE` logic. When observations are re-inserted with the same `obs_id`, they **replace** (not add to) existing observations.

### Why This Happened

1. **Table Schema**:
   ```sql
   CREATE TABLE env_observations (
       obs_id TEXT,
       service_name TEXT,
       ...
       PRIMARY KEY (obs_id, service_name)
   )
   ```

2. **Insert Logic** (line 547 of `acquire_environmental_data.py`):
   ```sql
   INSERT OR REPLACE INTO env_observations
   (obs_id, cluster_id, service_name, variable, value, ...)
   VALUES (?, ?, ?, ?, ?, ...)
   ```

3. **The obs_id doesn't include cluster_id in a unique way**, so:
   - Cluster 1 + NASA_POWER + WS10M + 2021-01-01 → `NASA_POWER_WS10M_20210101_366`
   - Cluster 2 + NASA_POWER + WS10M + 2021-01-01 → `NASA_POWER_WS10M_20210101_367` (different counter!)
   - But later runs might re-use counter values, causing replacements

4. **When services were re-run**, new observations replaced old ones instead of being skipped (due to cluster_processing status being cleared by `--clear` commands)

### The --clear Bug (secondary issue)

The `clear_service_data()` function (line 383-422) has a bug:
```python
obs_deleted = conn.execute("""
DELETE FROM environmental_observations  # ❌ Wrong table name!
WHERE dataset = ?
""", (service_name,))
```

The actual table is `env_observations` (not `environmental_observations`), so:
- ✅ `cluster_processing` records were cleared
- ❌ Observations remained in database
- Result: Re-runs added/replaced observations inconsistently

---

## Impact Assessment

### Critical Services (< 50% recovery, 0.0-0.1%)

| Service | Expected Obs | Actual Obs | Recovery | Clusters Affected |
|---------|-------------|-----------|----------|------------------|
| NASA_POWER | 10,487,910 | 5,475 | 0.1% | 4,789 |
| GBIF | 1,436,700 | 300 | 0.0% | 4,789 |
| MODIS_EVI | 985,497 | 276 | 0.0% | 3,674 |
| MODIS_NDVI | 985,497 | 276 | 0.0% | 3,674 |
| TERRACLIMATE | 638,204 | 168 | 0.0% | 3,799 |
| GOOGLE_EMBEDDINGS | 267,648 | 320 | 0.1% | 4,050 |
| GPM_PRECIP | 125,700 | 60 | 0.0% | 2,095 |
| WORLDCLIM_BIO | 68,324 | 19 | 0.0% | 3,596 |
| MODIS_LANDCOVER | 57,050 | 26 | 0.0% | 4,512 |
| SOILGRIDS_OC | 21,342 | 6 | 0.0% | 3,557 |
| SOILGRIDS_PH | 21,342 | 6 | 0.0% | 3,557 |
| SOILGRIDS_TEXTURE | 21,342 | 6 | 0.0% | 3,557 |
| SRTM | 4,051 | 1 | 0.0% | 4,051 |

### Warning (50-90% recovery)

| Service | Expected Obs | Actual Obs | Recovery | Clusters Affected |
|---------|-------------|-----------|----------|------------------|
| USGS_NWIS | 146,046 | 96,732 | 66.2% | 20 |

### OK (> 90% recovery)

| Service | Expected Obs | Actual Obs | Recovery | Clusters Affected |
|---------|-------------|-----------|----------|------------------|
| OpenAQ | 1,727,925 | 1,584,798 | 91.7% | 847 |

---

## Fix Strategy

### Step 1: Backup Current Database

```bash
cp notebooks/pangenome_env_data/pangenome_env.db \
   notebooks/pangenome_env_data/pangenome_env.db.backup_20251003
```

### Step 2: Fix the Schema (Recommended)

**Option A**: Change PRIMARY KEY to include cluster_id:
```sql
ALTER TABLE env_observations ...  -- SQLite doesn't support this directly
-- Need to recreate table with:
PRIMARY KEY (cluster_id, service_name, variable, time_stamp)
```

**Option B**: Remove PRIMARY KEY constraint and use UNIQUE index:
```sql
CREATE UNIQUE INDEX idx_obs_unique
ON env_observations(cluster_id, service_name, variable, time_stamp, depth_top_cm, depth_bottom_cm);
```

**Option C**: Keep current schema but change INSERT to INSERT OR IGNORE:
- Less safe (could silently skip legitimate new observations)
- But simpler to implement

### Step 3: Fix the --clear Bug

Edit `scripts/acquire_environmental_data.py` line 411:
```python
# Before:
DELETE FROM environmental_observations
WHERE dataset = ?

# After:
DELETE FROM env_observations
WHERE service_name = ?
```

### Step 4: Re-run All Affected Services

Services to re-run (in priority order):

1. **High-value services** (start here):
   ```bash
   python scripts/acquire_environmental_data.py --service NASA_POWER --clear
   python scripts/acquire_environmental_data.py --service MODIS_NDVI --clear
   python scripts/acquire_environmental_data.py --service MODIS_EVI --clear
   python scripts/acquire_environmental_data.py --service TERRACLIMATE --clear
   python scripts/acquire_environmental_data.py --service GOOGLE_EMBEDDINGS --clear
   ```

2. **Medium-value services**:
   ```bash
   python scripts/acquire_environmental_data.py --service SOILGRIDS_PH --clear
   python scripts/acquire_environmental_data.py --service SOILGRIDS_OC --clear
   python scripts/acquire_environmental_data.py --service SOILGRIDS_TEXTURE --clear
   python scripts/acquire_environmental_data.py --service SRTM --clear
   python scripts/acquire_environmental_data.py --service WORLDCLIM_BIO --clear
   python scripts/acquire_environmental_data.py --service MODIS_LANDCOVER --clear
   ```

3. **Lower-priority services**:
   ```bash
   python scripts/acquire_environmental_data.py --service GBIF --clear
   python scripts/acquire_environmental_data.py --service USGS_NWIS --clear
   python scripts/acquire_environmental_data.py --service GPM_PRECIP --clear  # Very slow!
   ```

### Step 5: Verify Recovery

After each batch, run:
```bash
python scripts/diagnose_database_integrity.py
```

---

## Estimated Timeline

Based on logs:
- **NASA_POWER**: ~4 hours (4,789 clusters, mostly "no_data")
- **MODIS services**: ~6 hours each (image processing)
- **GOOGLE_EMBEDDINGS**: ~24 hours (slow Earth Engine API)
- **GPM_PRECIP**: ~48 hours (extremely slow, consider skipping)
- **Other services**: ~2-4 hours each

**Total estimated time**: 4-6 days for all services

---

## Prevention

1. **Fix schema** to prevent replacements
2. **Fix --clear bug** to properly clean observations
3. **Add validation** after each service run:
   - Compare cluster_processing.obs_count vs actual observations
   - Alert if discrepancy > 10%
4. **Add checkpoint system** to save intermediate results
5. **Consider** using transaction batches with rollback on error

---

## Files Created

- `scripts/diagnose_database_integrity.py` - Diagnostic tool
- `DATABASE_INTEGRITY_DIAGNOSIS.md` - This document

---

## Next Steps

1. Review this diagnosis
2. Decide on fix strategy (recommend Option A: proper PRIMARY KEY)
3. Backup database
4. Implement schema fix
5. Fix --clear bug
6. Re-run services in priority order
7. Validate with diagnostic script
8. Proceed with analysis once data is complete
