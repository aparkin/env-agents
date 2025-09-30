# Database Management for Environmental Data Acquisition

## Quick Reference

### Check Status

```bash
python ../scripts/acquire_environmental_data.py --status
```

Shows progress for all services including:
- Total clusters processed
- Success/no_data/failed counts
- Total observations collected

### Clear Service Data

#### Clear ALL data for a service (complete restart)

```bash
python ../scripts/acquire_environmental_data.py --clear SRTM
```

This will:
- Delete ALL cluster processing records for SRTM
- Delete ALL observations from SRTM
- Require "yes" confirmation
- Allow complete re-processing from scratch

#### Clear only specific status (selective retry)

```bash
# Clear only "no_data" records (retry clusters that returned no data)
python ../scripts/acquire_environmental_data.py --clear SRTM --clear-status no_data

# Clear only "failed" records (retry errors but keep successes)
python ../scripts/acquire_environmental_data.py --clear SRTM --clear-status failed
```

This will:
- Delete only records with specified status
- Keep other status records intact
- Keep ALL observations (doesn't delete data)
- Useful for retrying after fixing adapter issues

## Common Scenarios

### Scenario 1: Adapter was broken, fix and retry everything

```bash
# Clear all SRTM data
python ../scripts/acquire_environmental_data.py --clear SRTM
# Type "yes" when prompted

# Start fresh
python ../scripts/acquire_environmental_data.py --service SRTM \
    --clusters clusters_optimized.csv \
    --samples df_gtdb_tagged_cleaneed.tsv
```

### Scenario 2: Had "no_data" results, want to retry with fixed adapter

```bash
# Clear only no_data records
python ../scripts/acquire_environmental_data.py --clear SRTM --clear-status no_data
# Type "yes" when prompted

# Resume (will retry no_data clusters, skip successes)
python ../scripts/acquire_environmental_data.py --service SRTM \
    --clusters clusters_optimized.csv \
    --samples df_gtdb_tagged_cleaneed.tsv
```

### Scenario 3: Service had transient errors, retry failures only

```bash
# Clear only failed records
python ../scripts/acquire_environmental_data.py --clear SRTM --clear-status failed

# Resume (will retry failures, skip successes and no_data)
python ../scripts/acquire_environmental_data.py --service SRTM \
    --clusters clusters_optimized.csv \
    --samples df_gtdb_tagged_cleaneed.tsv
```

### Scenario 4: Check what's left to do

```bash
python ../scripts/acquire_environmental_data.py --status
```

Example output:
```
Service: SRTM
  Total clusters: 4789
  Processed: 450 (success: 374, no_data: 76)
  Remaining: 4339
  Observations: 374
```

## Direct SQL Queries (Advanced)

### Check specific service status

```bash
cd notebooks
sqlite3 pangenome_env_data/pangenome_env.db
```

```sql
-- Count by status
SELECT status, COUNT(*)
FROM cluster_processing
WHERE service_name = 'SRTM'
GROUP BY status;

-- Find failed clusters
SELECT cluster_id, error_message
FROM cluster_processing
WHERE service_name = 'SRTM' AND status = 'failed';

-- Check processing time stats
SELECT
    service_name,
    COUNT(*) as count,
    AVG(processing_time) as avg_time,
    MIN(processing_time) as min_time,
    MAX(processing_time) as max_time
FROM cluster_processing
WHERE status = 'success'
GROUP BY service_name;

-- Find clusters outside SRTM coverage (-56 to 60 degrees)
SELECT cluster_id, center_lat, center_lon
FROM spatial_clusters
WHERE center_lat NOT BETWEEN -56 AND 60;
```

### Manual cleanup (if needed)

```sql
-- Delete all SRTM records
DELETE FROM cluster_processing WHERE service_name = 'SRTM';
DELETE FROM environmental_observations WHERE dataset = 'SRTM';

-- Delete only no_data SRTM records
DELETE FROM cluster_processing WHERE service_name = 'SRTM' AND status = 'no_data';

-- Commit changes
.quit
```

## Resume Logic

The script automatically resumes by:
1. Loading all cluster IDs from `spatial_clusters` table
2. Excluding clusters with `status IN ('success', 'no_data')` for the service
3. Processing remaining clusters

**Important:** "no_data" results are considered "done" and won't be retried unless you explicitly clear them with `--clear-status no_data`.

## Why "no_data" is Permanent

Some clusters legitimately have no data:
- **Ocean locations** (no SRTM elevation data)
- **Polar regions** (outside SRTM coverage: -56°S to 60°N)
- **No species observations** (for GBIF in that area)
- **No air quality sensors** (for OpenAQ in remote areas)

Retrying these endlessly wastes time. The script marks them as "no_data" and moves on.

**When to retry "no_data":**
- Adapter was broken (returned no_data incorrectly)
- Wrong geometry/parameters (fixed the query)
- Service was down (temporary outage)

## Database Files

- **Location:** `notebooks/pangenome_env_data/pangenome_env.db`
- **Format:** SQLite3 with WAL mode (concurrent writes supported)
- **Current size:** ~31 MB
- **Expected final:** 5-7 GB (all services completed)

## Backup

Before major operations:

```bash
cd notebooks/pangenome_env_data
cp pangenome_env.db pangenome_env.db.backup
```

## Troubleshooting

### "Database is locked"
SQLite WAL mode supports concurrent reads and one writer. If you see this:
- Only one write operation allowed at a time
- Check for stuck processes: `ps aux | grep acquire_environmental`
- Kill stuck process: `kill <PID>`

### Too many "no_data" results
Check if clusters are outside service coverage:
```sql
-- For SRTM, check latitudes
SELECT COUNT(*) FROM spatial_clusters
WHERE center_lat NOT BETWEEN -56 AND 60;
```

### Want to see progress in real-time
```bash
# Terminal 1: Run acquisition
python ../scripts/acquire_environmental_data.py --service SRTM ...

# Terminal 2: Watch progress
watch -n 5 "python ../scripts/acquire_environmental_data.py --status"
```