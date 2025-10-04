# Database Management Guide

Complete guide for creating, managing, and maintaining the environmental data database.

---

## Table of Contents

1. [Initial Database Setup](#initial-database-setup)
2. [Running Data Acquisition](#running-data-acquisition)
3. [Monitoring Progress](#monitoring-progress)
4. [Database Maintenance](#database-maintenance)
5. [Troubleshooting](#troubleshooting)
6. [Database Schema](#database-schema)

---

## Initial Database Setup

### Prerequisites

```bash
# Install env-agents
pip install -e .

# Verify installation
ea --version

# Check credentials are configured
ls credentials/
# Should see: ee_credentials.json, openaq_api_key.txt, etc.
```

### Create Fresh Database

The database is created automatically on first run, but you can initialize it explicitly:

```bash
python scripts/acquire_environmental_data.py --init-db
```

This creates:
- `notebooks/pangenome_env_data/pangenome_env.db` (main database)
- Tables: `env_observations`, `cluster_processing`, `spatial_clusters`, `genome_samples`
- Indexes for efficient querying

### Load Sample Data

```bash
# Load genome samples and create spatial clusters
python scripts/acquire_environmental_data.py --load-samples notebooks/date_and_latlon_samples_extended.tsv
```

This:
1. Reads genome locations from TSV
2. Creates spatial clusters (groups nearby genomes)
3. Populates `genome_samples` and `spatial_clusters` tables

### Verify Setup

```bash
# Check database exists and has tables
sqlite3 notebooks/pangenome_env_data/pangenome_env.db ".tables"
# Should show: cluster_processing  env_observations  genome_samples  spatial_clusters

# Check cluster count
sqlite3 notebooks/pangenome_env_data/pangenome_env.db "SELECT COUNT(*) FROM spatial_clusters;"
# Should show: 4789
```

---

## Running Data Acquisition

### Single Service

```bash
# Run one service for all clusters
python scripts/acquire_environmental_data.py --service NASA_POWER

# Run with specific time range
python scripts/acquire_environmental_data.py \
  --service NASA_POWER \
  --start-date 2021-01-01 \
  --end-date 2021-12-31
```

### Multiple Services Sequentially

```bash
# Run multiple services in sequence
for service in NASA_POWER SRTM MODIS_NDVI; do
  python scripts/acquire_environmental_data.py --service $service
done
```

### Parallel Execution (Recommended)

Use the provided script for parallel execution with progress monitoring:

```bash
# Run Phase 1 services (4 services in parallel)
python scripts/run_acquisition_batch.py --phase 1

# Or specify custom services
python scripts/run_acquisition_batch.py \
  --services NASA_POWER SOILGRIDS_PH SOILGRIDS_OC SRTM \
  --max-parallel 4
```

See [run_acquisition_batch.py](#parallel-run-script) below for details.

### Re-running Services (Clearing Data)

If you need to re-run a service (e.g., after fixing a bug or changing parameters):

```bash
# Clear and re-run specific service
python scripts/acquire_environmental_data.py --service NASA_POWER --clear

# Clear only failed/no_data records, keeping successes
python scripts/acquire_environmental_data.py --service NASA_POWER --clear-status failed
python scripts/acquire_environmental_data.py --service NASA_POWER --clear-status no_data
```

**Important**: `--clear` without `--clear-status` deletes ALL records and observations for that service.

---

## Monitoring Progress

### Real-Time Monitoring

During acquisition, logs are written to:
```
notebooks/pangenome_env_data/logs/acquisition_YYYYMMDD_HHMMSS.log
```

Monitor with:
```bash
tail -f notebooks/pangenome_env_data/logs/acquisition_*.log
```

### Database Status Check

```bash
# Quick status
python scripts/diagnose_database_integrity.py

# Detailed cluster-level status for a service
sqlite3 notebooks/pangenome_env_data/pangenome_env.db \
  "SELECT status, COUNT(*) FROM cluster_processing WHERE service_name='NASA_POWER' GROUP BY status;"
```

### Expected vs Actual Observations

The diagnostic script compares expected observations (from cluster_processing.obs_count) vs actual rows in env_observations:

```bash
python scripts/diagnose_database_integrity.py > status_report.txt
```

Output shows:
- Recovery rate per service (should be >95%)
- Services needing re-run
- Observation counts

---

## Database Maintenance

### Backup Database

Before major operations:

```bash
# Create timestamped backup
DATE=$(date +%Y%m%d_%H%M%S)
cp notebooks/pangenome_env_data/pangenome_env.db \
   notebooks/pangenome_env_data/pangenome_env.db.backup_$DATE
```

### Restore from Backup

```bash
# List backups
ls -lh notebooks/pangenome_env_data/*.backup_*

# Restore specific backup
cp notebooks/pangenome_env_data/pangenome_env.db.backup_20251003 \
   notebooks/pangenome_env_data/pangenome_env.db
```

### Vacuum Database (Reclaim Space)

After clearing large amounts of data:

```bash
sqlite3 notebooks/pangenome_env_data/pangenome_env.db "VACUUM;"
```

### Export Data

```bash
# Export observations for a service to CSV
sqlite3 -header -csv notebooks/pangenome_env_data/pangenome_env.db \
  "SELECT * FROM env_observations WHERE service_name='NASA_POWER';" \
  > nasa_power_export.csv

# Export cluster summary
sqlite3 -header -csv notebooks/pangenome_env_data/pangenome_env.db \
  "SELECT cluster_id, COUNT(*) as genome_count, center_lat, center_lon
   FROM spatial_clusters
   GROUP BY cluster_id;" \
  > cluster_summary.csv
```

### Reset Everything (Nuclear Option)

To start completely fresh:

```bash
# 1. Backup current database
cp notebooks/pangenome_env_data/pangenome_env.db \
   notebooks/pangenome_env_data/pangenome_env.db.old

# 2. Delete database
rm notebooks/pangenome_env_data/pangenome_env.db

# 3. Recreate from scratch
python scripts/acquire_environmental_data.py --init-db
python scripts/acquire_environmental_data.py --load-samples notebooks/date_and_latlon_samples_extended.tsv

# 4. Run acquisition
python scripts/run_acquisition_batch.py --phase 1
```

---

## Troubleshooting

### Problem: "No such table: env_observations"

**Cause**: Database not initialized
**Fix**:
```bash
python scripts/acquire_environmental_data.py --init-db
```

### Problem: "All clusters already processed, nothing to do"

**Cause**: cluster_processing shows "success" for all clusters
**Fix**: Use `--clear` to force re-processing:
```bash
python scripts/acquire_environmental_data.py --service NASA_POWER --clear
```

### Problem: Very few observations despite "success" status

**Cause**: Data integrity issue (old bug, now fixed)
**Fix**:
1. Run diagnostic: `python scripts/diagnose_database_integrity.py`
2. Clear and re-run affected services:
```bash
python scripts/acquire_environmental_data.py --service NASA_POWER --clear
```

### Problem: "Quota exceeded" or "Rate limit" errors

**Cause**: API rate limits (especially Earth Engine services)
**Fix**: Script automatically retries with exponential backoff. If persistent:
```bash
# Wait an hour and resume
python scripts/acquire_environmental_data.py --service MODIS_NDVI
# (Will skip already-processed clusters)
```

### Problem: Service hangs or takes forever

**Cause**: Some services are very slow (GPM_PRECIP, GOOGLE_EMBEDDINGS)
**Fix**:
- Check logs for progress
- Consider running in `screen` or `tmux` session
- For GPM_PRECIP: Consider skipping (redundant with NASA_POWER)

### Problem: Missing credentials

**Cause**: Service requires API keys not configured
**Fix**:
```bash
# Earth Engine (most services)
earthengine authenticate

# OpenAQ
echo "YOUR_API_KEY" > credentials/openaq_api_key.txt

# USGS (usually works without key)
# No action needed
```

---

## Database Schema

### Tables

#### `env_observations`
Stores all environmental observations.

```sql
CREATE TABLE env_observations (
    obs_id TEXT,              -- Unique observation identifier
    cluster_id INTEGER,       -- Spatial cluster ID
    service_name TEXT,        -- Source service (e.g., NASA_POWER)
    variable TEXT,            -- Variable name (e.g., nasa_power:T2M)
    value REAL,               -- Measured value
    unit TEXT,                -- Unit (e.g., degC, mm)
    time_stamp TEXT,          -- ISO timestamp
    lat REAL,                 -- Latitude
    lon REAL,                 -- Longitude
    PRIMARY KEY (cluster_id, service_name, variable, time_stamp, obs_id)
);
```

**Indexes**:
- `idx_env_cluster_service` on `(cluster_id, service_name)`
- `idx_env_service` on `(service_name)`
- `idx_env_cluster` on `(cluster_id)`

#### `cluster_processing`
Tracks processing status per cluster per service.

```sql
CREATE TABLE cluster_processing (
    cluster_id INTEGER,       -- Spatial cluster ID
    service_name TEXT,        -- Service name
    status TEXT,              -- success | failed | no_data | error
    obs_count INTEGER,        -- Number of observations returned
    processing_time REAL,     -- Time in seconds
    error_message TEXT,       -- Error details if failed
    completed_at TEXT,        -- ISO timestamp of completion
    PRIMARY KEY (cluster_id, service_name)
);
```

**Index**: `idx_cluster_status` on `(cluster_id, service_name, status)`

#### `spatial_clusters`
Spatial clusters of genome samples.

```sql
CREATE TABLE spatial_clusters (
    cluster_id INTEGER PRIMARY KEY,
    center_lat REAL,          -- Cluster center latitude
    center_lon REAL,          -- Cluster center longitude
    bbox_minlat REAL,         -- Bounding box
    bbox_minlon REAL,
    bbox_maxlat REAL,
    bbox_maxlon REAL,
    sample_ids TEXT           -- JSON array of sample IDs in cluster
);
```

#### `genome_samples`
Individual genome sample locations.

```sql
CREATE TABLE genome_samples (
    sample_id TEXT PRIMARY KEY,
    genome_id TEXT,
    latitude REAL,
    longitude REAL,
    collection_date TEXT,
    cluster_id INTEGER,
    FOREIGN KEY (cluster_id) REFERENCES spatial_clusters(cluster_id)
);
```

### Query Examples

```sql
-- Get all observations for a cluster
SELECT * FROM env_observations
WHERE cluster_id = 9
ORDER BY service_name, variable, time_stamp;

-- Count observations per service
SELECT service_name, COUNT(*) as obs_count
FROM env_observations
GROUP BY service_name
ORDER BY obs_count DESC;

-- Find failed clusters
SELECT cluster_id, service_name, error_message
FROM cluster_processing
WHERE status = 'failed';

-- Get cluster locations
SELECT cluster_id, center_lat, center_lon
FROM spatial_clusters
ORDER BY cluster_id;

-- Check processing completeness
SELECT
    service_name,
    COUNT(CASE WHEN status='success' THEN 1 END) as success,
    COUNT(CASE WHEN status='failed' THEN 1 END) as failed,
    COUNT(CASE WHEN status='no_data' THEN 1 END) as no_data,
    COUNT(CASE WHEN status='error' THEN 1 END) as error
FROM cluster_processing
GROUP BY service_name;
```

---

## Best Practices

### 1. Always Backup Before Major Operations
```bash
cp notebooks/pangenome_env_data/pangenome_env.db{,.backup}
```

### 2. Use Diagnostic Script to Verify Data Integrity
```bash
python scripts/diagnose_database_integrity.py
```

### 3. Run Expensive Services Last
Order: Fast → Moderate → Slow
- Fast: SRTM, WORLDCLIM_BIO (minutes)
- Moderate: NASA_POWER, SoilGrids, TerraClimate (hours)
- Slow: MODIS services, GOOGLE_EMBEDDINGS (many hours)

### 4. Monitor Logs During Long Runs
```bash
tail -f notebooks/pangenome_env_data/logs/acquisition_*.log
```

### 5. Use Parallel Execution for Multiple Services
```bash
python scripts/run_acquisition_batch.py --phase 1
```

### 6. Keep Database Optimized
```bash
# After clearing large amounts of data
sqlite3 notebooks/pangenome_env_data/pangenome_env.db "VACUUM;"
sqlite3 notebooks/pangenome_env_data/pangenome_env.db "ANALYZE;"
```

---

## Appendix: Service List

| Service | Type | Avg Time/Cluster | Total Expected Obs |
|---------|------|------------------|-------------------|
| SRTM | Topography | <1 sec | 4,051 |
| NASA_POWER | Climate | 3 sec | 10,487,910 |
| WORLDCLIM_BIO | Climate | 2 sec | 68,324 |
| TERRACLIMATE | Climate | 5 sec | 638,204 |
| SOILGRIDS_PH | Soil | 3 sec | 21,342 |
| SOILGRIDS_OC | Soil | 3 sec | 21,342 |
| SOILGRIDS_TEXTURE | Soil | 3 sec | 21,342 |
| MODIS_NDVI | Vegetation | 10 sec | 985,497 |
| MODIS_EVI | Vegetation | 10 sec | 985,497 |
| MODIS_LANDCOVER | Landcover | 8 sec | 57,050 |
| GOOGLE_EMBEDDINGS | Satellite ML | 20 sec | 267,648 |
| GBIF | Biodiversity | 5 sec | 1,436,700 |
| OpenAQ | Air Quality | 8 sec | 1,727,925 |
| USGS_NWIS | Water Quality | 10 sec | 146,046 |
| GPM_PRECIP | Precipitation | 60 sec+ | 125,700 |

**Total**: ~17M observations across 15 services
