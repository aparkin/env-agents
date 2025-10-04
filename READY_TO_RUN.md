# Ready to Run - Environmental Data Acquisition

**Date**: 2025-10-03
**Status**: ✅ Database fixed, scripts tested, ready for full acquisition

---

## What Was Done

### 1. Fixed Database Issues ✓
- **Backed up database**: `pangenome_env.db.backup_20251003` (343 MB)
- **Fixed schema**: Changed PRIMARY KEY to include `cluster_id` → prevents data loss
- **Fixed --clear bug**: Now properly deletes observations when re-running services

### 2. Created Management Tools ✓
- **Diagnostic script**: `scripts/diagnose_database_integrity.py`
- **Test script**: `scripts/test_acquisition_readiness.py`
- **Parallel run script**: `scripts/run_acquisition_batch.py`

### 3. Organized Documentation ✓
- **Main guide**: `docs/DATABASE_MANAGEMENT.md` - Complete database management reference
- **Troubleshooting**: `docs/troubleshooting/` - Diagnosis and recovery guides
- **Archived**: One-time fix scripts moved to `archive/`

---

## Pre-Flight Checklist

Run the readiness test:
```bash
python scripts/test_acquisition_readiness.py
```

**Expected output:**
- ✅ Database schema correct
- ✅ 4,789 spatial clusters found
- ⚠️  Earth Engine credentials needed (for most services)
- ⚠️  OpenAQ API key optional

**If you see issues:**
- Database problems → See `docs/DATABASE_MANAGEMENT.md`
- Credentials → Run `earthengine authenticate`

---

## Running Acquisition

### Recommended Approach: Phased Execution

#### **Phase 1: Essential Services (~16 hours)**

These give you core climate and soil data for preliminary analysis:

```bash
python scripts/run_acquisition_batch.py --phase 1
```

Services:
- NASA_POWER (temperature, precipitation, wind, solar)
- SOILGRIDS_PH (pH at multiple depths)
- SOILGRIDS_OC (organic carbon)
- SOILGRIDS_TEXTURE (clay/sand/silt)
- SRTM (elevation)
- TERRACLIMATE (water balance)

**After Phase 1 completes**, you can start analysis! Run diagnostic:
```bash
python scripts/diagnose_database_integrity.py
```

#### **Phase 2: Vegetation & Landcover (~12 hours)**

```bash
python scripts/run_acquisition_batch.py --phase 2
```

Services:
- MODIS_NDVI (vegetation productivity)
- MODIS_EVI (enhanced vegetation index)
- MODIS_LANDCOVER (land cover types)
- WORLDCLIM_BIO (19 bioclimatic variables)

#### **Phase 3: High-Dimensional Features (~24 hours)**

```bash
python scripts/run_acquisition_batch.py --phase 3
```

Services:
- GOOGLE_EMBEDDINGS (64D satellite image embeddings)

**Note**: This is slow! Consider running in parallel with Phase 4 if you have capacity.

#### **Phase 4: Supplementary Data (~9 hours, optional)**

```bash
python scripts/run_acquisition_batch.py --phase 4
```

Services:
- GBIF (species occurrence records)
- USGS_NWIS (water quality, sparse coverage)

---

### Custom Service Selection

Run specific services:
```bash
python scripts/run_acquisition_batch.py \
  --services NASA_POWER SOILGRIDS_PH SRTM \
  --max-parallel 3
```

Or run single service:
```bash
python scripts/acquire_environmental_data.py --service NASA_POWER --clear
```

---

## Monitoring Progress

### Real-Time Display

The batch script shows live progress with:
- Service status (Running/Complete/Failed)
- Progress bars
- Success/No Data/Failed counts
- Total observations
- Elapsed time

### Check Logs

```bash
# Follow latest log
tail -f notebooks/pangenome_env_data/logs/acquisition_*.log

# Count completed services
ls -1 notebooks/pangenome_env_data/logs/ | wc -l
```

### Database Status

```bash
# Run diagnostic (shows recovery rates)
python scripts/diagnose_database_integrity.py

# Quick query
sqlite3 notebooks/pangenome_env_data/pangenome_env.db \
  "SELECT service_name, COUNT(*) FROM env_observations GROUP BY service_name;"
```

---

## Expected Timeline

### Conservative Estimates (Sequential)

| Phase | Services | Hours | Can Start Analysis? |
|-------|----------|-------|---------------------|
| 1 | Essential (6 services) | 16h | ✅ YES |
| 2 | Vegetation (4 services) | 12h | ✅ YES |
| 3 | Embeddings (1 service) | 24h | After Phase 1-2 |
| 4 | Supplementary (2 services) | 9h | Optional |
| **Total** | **13 services** | **61h** (~2.5 days) |  |

### With Parallelization (4 concurrent)

| Phase | Services | Wall Clock Time |
|-------|----------|-----------------|
| 1 | 6 services (4 parallel) | ~6h |
| 2 | 4 services (4 parallel) | ~4h |
| 3 | 1 service | ~24h |
| 4 | 2 services (2 parallel) | ~5h |
| **Total** | **13 services** | **~39h** (~1.6 days) |

**Recommendation**: Run Phase 1, verify results, then continue. Don't wait for everything!

---

## What to Expect

### Normal Behavior

✅ **"no_data" status** - Some locations don't have data from all services (expected)
✅ **Retry messages** - APIs timeout occasionally, script auto-retries (expected)
✅ **Progress varies** - Some clusters faster than others (expected)

### Warning Signs

⚠️  **All clusters showing "failed"** - Check credentials or internet
⚠️  **Zero observations despite "success"** - Run diagnostic immediately
⚠️  **Script crashes immediately** - Check logs for specific error

---

## After Completion

### 1. Verify Data Integrity

```bash
python scripts/diagnose_database_integrity.py
```

**Look for:**
- Recovery rates > 95% for all services
- Total observations ~17M (all phases) or ~12M (phases 1-2)

### 2. Check Database Size

```bash
ls -lh notebooks/pangenome_env_data/pangenome_env.db
```

**Expected:**
- After Phase 1: ~500-800 MB
- After Phase 1-2: ~1.5-2 GB
- After all phases: ~2.5-3 GB

### 3. Start Analysis!

```bash
cd analysis/notebooks/01_data_prep/
jupyter lab 01a_extract_pivot.ipynb
```

The analysis notebooks will:
1. Extract data from database
2. Pivot to wide format (clusters × variables)
3. Merge with taxonomy
4. Analyze missing data patterns
5. Characterize variables

---

## Troubleshooting

### Service Fails Immediately

**Check:**
```bash
# View specific service log
tail -100 notebooks/pangenome_env_data/logs/acquisition_*.log | grep ERROR

# Test single cluster
python scripts/acquire_environmental_data.py --service NASA_POWER --limit 1
```

### Quota/Rate Limit Errors

**Earth Engine services (MODIS, Google Embeddings, SoilGrids, etc.)**:
- Wait 1 hour and resume (script will skip completed clusters)
- Or reduce parallel count: `--max-parallel 2`

### Out of Disk Space

**Check space:**
```bash
df -h .
```

**If low (<10 GB free)**:
1. Delete old log files: `rm notebooks/pangenome_env_data/logs/acquisition_2025*.log`
2. Vacuum database: `sqlite3 pangenome_env.db "VACUUM;"`
3. Remove backup once verified: `rm pangenome_env.db.backup_*`

### Want to Start Over

**Complete reset:**
```bash
# Backup current
cp notebooks/pangenome_env_data/pangenome_env.db{,.old}

# Delete database
rm notebooks/pangenome_env_data/pangenome_env.db

# Recreate
python scripts/acquire_environmental_data.py --init-db
python scripts/acquire_environmental_data.py --load-samples notebooks/date_and_latlon_samples_extended.tsv

# Re-run acquisition
python scripts/run_acquisition_batch.py --phase 1
```

---

## Quick Reference Commands

```bash
# Test readiness
python scripts/test_acquisition_readiness.py

# Run Phase 1 (essential services)
python scripts/run_acquisition_batch.py --phase 1

# Monitor logs
tail -f notebooks/pangenome_env_data/logs/acquisition_*.log

# Check status
python scripts/diagnose_database_integrity.py

# Run custom services
python scripts/run_acquisition_batch.py --services NASA_POWER SRTM --max-parallel 2

# Single service
python scripts/acquire_environmental_data.py --service NASA_POWER --clear

# Backup database
cp notebooks/pangenome_env_data/pangenome_env.db{,.backup_$(date +%Y%m%d)}
```

---

## Getting Help

1. **Check logs first**: `notebooks/pangenome_env_data/logs/acquisition_*.log`
2. **Run diagnostic**: `python scripts/diagnose_database_integrity.py`
3. **See documentation**: `docs/DATABASE_MANAGEMENT.md`
4. **Troubleshooting guides**: `docs/troubleshooting/`

---

## You're Ready!

✅ Database fixed and backed up
✅ Scripts tested and ready
✅ Documentation complete

**Next command:**
```bash
python scripts/run_acquisition_batch.py --phase 1
```

Good luck! 🚀
