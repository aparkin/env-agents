#!/usr/bin/env python3
"""
Production Environmental Data Acquisition for Pangenome Analysis

Efficiently acquires environmental data for 4,789 spatial clusters with:
- Phase 1: Fast services (NASA_POWER, SRTM, MODIS) - ~17.6 hours
- Phase 2: Google Embeddings - ~62.7 hours
- Automatic resume on interruption
- Rate limiting and polite server behavior
- Progress tracking and logging

Usage:
    python scripts/acquire_environmental_data.py --phase 1 --clusters clusters.csv --samples samples.csv
    python scripts/acquire_environmental_data.py --phase 2 --resume
    python scripts/acquire_environmental_data.py --status  # Check progress
"""

import argparse
import sys
import time
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from tqdm import tqdm

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from env_agents.adapters import CANONICAL_SERVICES
from env_agents.core.models import RequestSpec, Geometry


# Service configurations with rate limiting
# NOTE: Earth Engine has shared quotas - if running multiple EE services in parallel,
# they compete for the same quota. Recommended: run EE services sequentially or
# increase rate_limit to 5-10s when running in parallel.

# Phase 0: Fast unitary services (no Earth Engine quota conflicts)
PHASE0_SERVICES = {
    "NASA_POWER": {
        "rate_limit": 0.5,  # Min seconds between requests (2 req/sec)
        "timeout": 60,
        "time_range": ("2021-01-01", "2021-12-31")
    },
    "GBIF": {
        "rate_limit": 1.0,  # GBIF rate limits
        "timeout": 60,
        "time_range": ("2021-01-01", "2021-12-31"),
        "max_records": 10000
    },
    "OpenAQ": {
        "rate_limit": 1.0,  # OpenAQ API limits
        "timeout": 60,
        "time_range": ("2021-06-01", "2021-08-31"),  # Summer only for better coverage
        "max_records": 20000
    },
    "USGS_NWIS": {
        "rate_limit": 0.5,  # USGS is usually fast
        "timeout": 60,
        "time_range": ("2021-01-01", "2021-12-31")
    },
    "WQP": {
        "rate_limit": 2.0,  # Water Quality Portal can be slow
        "timeout": 90,
        "time_range": ("2021-01-01", "2021-12-31"),
        "retry_on_quota": False,
        "max_retries": 2,
        "backoff_seconds": 10
    },
    "SSURGO": {
        "rate_limit": 3.0,  # Spatial queries can be slow
        "timeout": 90,
        "time_range": None,  # Static data
        "retry_on_quota": False,
        "max_retries": 2,
        "backoff_seconds": 10
    },
    "OSM_Overpass": {
        "rate_limit": 3.0,  # Be polite to OSM, complex queries
        "timeout": 120,
        "time_range": None,  # Static data
        "retry_on_quota": True,  # Overpass has rate limits
        "max_retries": 3,
        "backoff_seconds": 30
    }
}

# Phase 1: Earth Engine services (run sequentially due to shared quotas)
# OPTIMIZED RATE LIMITS based on actual production data:
# - SRTM: 1.56s avg query time → 2.0s rate limit (1.5x buffer)
# - MODIS_NDVI: 8.65s avg query time → 3.0s rate limit (query itself is slow)
PHASE1_SERVICES = {
    "SRTM": {
        "asset_id": "USGS/SRTMGL1_003",
        "rate_limit": 2.0,  # Optimized: 1.56s avg + 0.5s buffer
        "timeout": 60,
        "time_range": ("2021-01-01", "2021-12-31"),
        "is_earth_engine": True,
        "retry_on_quota": True,
        "max_retries": 3,
        "backoff_seconds": 60
    },
    "MODIS_NDVI": {
        "asset_id": "MODIS/061/MOD13Q1",
        "rate_limit": 3.0,  # Queries themselves take ~8s, minimal additional wait
        "timeout": 90,
        "time_range": ("2021-01-01", "2021-12-31"),
        "is_earth_engine": True,
        "retry_on_quota": True,
        "max_retries": 3,
        "backoff_seconds": 60
    },
    "MODIS_LST": {
        "asset_id": "MODIS/061/MOD11A1",  # Daily land surface temperature
        "rate_limit": 3.0,
        "timeout": 90,
        "time_range": ("2021-01-01", "2021-12-31"),
        "is_earth_engine": True,
        "retry_on_quota": True,
        "max_retries": 3,
        "backoff_seconds": 60
    },
    "WORLDCLIM_BIO": {
        "asset_id": "WORLDCLIM/V1/BIO",  # Bioclimatic variables (static)
        "rate_limit": 2.0,
        "timeout": 60,
        "time_range": None,  # Static data
        "is_earth_engine": True,
        "retry_on_quota": True,
        "max_retries": 3,
        "backoff_seconds": 60
    },
    "SOILGRIDS_TEXTURE": {
        "asset_id": "OpenLandMap/SOL/SOL_TEXTURE-CLASS_USDA-TT_M/v02",
        "rate_limit": 2.0,
        "timeout": 60,
        "time_range": None,  # Static data
        "is_earth_engine": True,
        "retry_on_quota": True,
        "max_retries": 3,
        "backoff_seconds": 60
    },
    "SOILGRIDS_PH": {
        "asset_id": "OpenLandMap/SOL/SOL_PH-H2O_USDA-4C1A2A_M/v02",  # Soil pH (0-5cm depth)
        "rate_limit": 2.0,
        "timeout": 60,
        "time_range": None,
        "is_earth_engine": True,
        "retry_on_quota": True,
        "max_retries": 3,
        "backoff_seconds": 60
    },
    "SOILGRIDS_OC": {
        "asset_id": "OpenLandMap/SOL/SOL_ORGANIC-CARBON_USDA-6A1C_M/v02",  # Organic carbon
        "rate_limit": 2.0,
        "timeout": 60,
        "time_range": None,
        "is_earth_engine": True,
        "retry_on_quota": True,
        "max_retries": 3,
        "backoff_seconds": 60
    },
    "MODIS_EVI": {
        "asset_id": "MODIS/061/MOD13Q1",  # Same as NDVI but we'll get EVI band
        "rate_limit": 3.0,
        "timeout": 90,
        "time_range": ("2021-01-01", "2021-12-31"),
        "is_earth_engine": True,
        "retry_on_quota": True,
        "max_retries": 3,
        "backoff_seconds": 60
    },
    "MODIS_LANDCOVER": {
        "asset_id": "MODIS/006/MCD12Q1",  # Land cover classification
        "rate_limit": 2.0,
        "timeout": 60,
        "time_range": ("2021-01-01", "2021-12-31"),
        "is_earth_engine": True,
        "retry_on_quota": True,
        "max_retries": 3,
        "backoff_seconds": 60
    },
    "TERRACLIMATE": {
        "asset_id": "IDAHO_EPSCOR/TERRACLIMATE",  # Climate water balance (precip, ET, soil moisture)
        "rate_limit": 3.0,
        "timeout": 90,
        "time_range": ("2021-01-01", "2021-12-31"),
        "is_earth_engine": True,
        "retry_on_quota": True,
        "max_retries": 3,
        "backoff_seconds": 60
    },
    "GPM_PRECIP": {
        "asset_id": "NASA/GPM_L3/IMERG_V06",  # High-resolution precipitation
        "rate_limit": 3.0,
        "timeout": 90,
        "time_range": ("2021-01-01", "2021-12-31"),
        "is_earth_engine": True,
        "retry_on_quota": True,
        "max_retries": 3,
        "backoff_seconds": 60
    }
}

# Phase 2: Google Embeddings (separate from other EE to manage quotas)
# OPTIMIZED: 44s avg query time → 5s rate limit (query itself is very slow, minimal wait needed)
PHASE2_SERVICES = {
    "GOOGLE_EMBEDDINGS": {
        "asset_id": "GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL",
        "rate_limit": 5.0,  # Queries take ~44s themselves, minimal additional wait
        "timeout": 120,
        "time_range": ("2021-01-01", "2021-12-31"),
        "is_earth_engine": True,
        "retry_on_quota": True,
        "max_retries": 3,
        "backoff_seconds": 60
    }
}


class EnvironmentalDataAcquisition:
    """Manages production environmental data acquisition with resume capability"""

    def __init__(self, db_path: str = "./pangenome_env_data/pangenome_env.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True, parents=True)

        # Setup logging
        log_dir = self.db_path.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"acquisition_{datetime.now():%Y%m%d_%H%M%S}.log"

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

        self._setup_database()
        self.adapters_cache = {}

    def _setup_database(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS genome_samples (
            genome_id TEXT PRIMARY KEY,
            lat REAL, lon REAL, date_collected TEXT,
            env_class TEXT, biosample_id TEXT,
            species TEXT, phylum TEXT
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS spatial_clusters (
            cluster_id INTEGER PRIMARY KEY,
            center_lat REAL, center_lon REAL,
            bbox_minlat REAL, bbox_minlon REAL,
            bbox_maxlat REAL, bbox_maxlon REAL,
            point_count INTEGER
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS env_observations (
            obs_id TEXT,
            cluster_id INTEGER,
            service_name TEXT,
            variable TEXT,
            value REAL,
            unit TEXT,
            time_stamp TEXT,
            lat REAL,
            lon REAL,
            PRIMARY KEY (obs_id, service_name)
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS cluster_processing (
            cluster_id INTEGER,
            service_name TEXT,
            status TEXT,
            obs_count INTEGER,
            processing_time REAL,
            error_message TEXT,
            completed_at TEXT,
            PRIMARY KEY (cluster_id, service_name)
        )
        """)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_env_cluster_service ON env_observations(cluster_id, service_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cluster_status ON cluster_processing(cluster_id, service_name, status)")

        conn.commit()
        conn.close()

    def load_genome_samples(self, samples_csv: str):
        """Load genome samples from CSV"""
        self.logger.info(f"Loading genome samples from {samples_csv}")
        df = pd.read_csv(samples_csv, sep='\t' if samples_csv.endswith('.tsv') else ',')

        conn = sqlite3.connect(self.db_path)
        sample_data = []
        for _, row in df.iterrows():
            sample_data.append((
                row.get('genome_id'), row.get('lat'), row.get('lon'),
                row.get('date'), row.get('env_class'),
                row.get('ncbi_biosample_accession_id'),
                row.get('species'), row.get('phylum')
            ))

        conn.executemany("""
        INSERT OR REPLACE INTO genome_samples
        (genome_id, lat, lon, date_collected, env_class, biosample_id, species, phylum)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_data)

        conn.commit()
        conn.close()
        self.logger.info(f"Loaded {len(sample_data):,} genome samples")

    def load_clusters(self, clusters_csv: str):
        """Load spatial clusters from CSV"""
        self.logger.info(f"Loading spatial clusters from {clusters_csv}")
        df = pd.read_csv(clusters_csv)

        conn = sqlite3.connect(self.db_path)
        cluster_data = []
        for _, row in df.iterrows():
            bbox = row['bbox']  # Assuming bbox is stored as string or list
            if isinstance(bbox, str):
                bbox = eval(bbox)  # Convert string representation to list

            cluster_data.append((
                row['cluster_id'],
                row['center_lat'], row['center_lon'],
                bbox[0], bbox[1], bbox[2], bbox[3],
                row['point_count']
            ))

        conn.executemany("""
        INSERT OR REPLACE INTO spatial_clusters
        (cluster_id, center_lat, center_lon, bbox_minlat, bbox_minlon, bbox_maxlat, bbox_maxlon, point_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, cluster_data)

        conn.commit()
        conn.close()
        self.logger.info(f"Loaded {len(cluster_data):,} spatial clusters")

    def get_pending_clusters(self, service_name: str) -> List[int]:
        """Get list of cluster IDs not yet processed for a service"""
        conn = sqlite3.connect(self.db_path)

        # Skip clusters that have been processed (success OR no_data)
        # Only retry failures (errors, timeouts, etc.)
        cursor = conn.execute("""
        SELECT cluster_id FROM spatial_clusters
        WHERE cluster_id NOT IN (
            SELECT cluster_id FROM cluster_processing
            WHERE service_name = ? AND status IN ('success', 'no_data')
        )
        ORDER BY cluster_id
        """, (service_name,))

        pending = [row[0] for row in cursor.fetchall()]
        conn.close()
        return pending

    def clear_service_data(self, service_name: str, status_filter: str = None):
        """
        Clear processing records for a service to allow re-processing

        Args:
            service_name: Name of service to clear
            status_filter: Optional status to filter (e.g., 'no_data', 'failed')
                          If None, clears ALL records for the service
        """
        conn = sqlite3.connect(self.db_path)

        if status_filter:
            deleted = conn.execute("""
            DELETE FROM cluster_processing
            WHERE service_name = ? AND status = ?
            """, (service_name, status_filter))
            self.logger.info(f"Cleared {deleted.rowcount} '{status_filter}' records for {service_name}")
        else:
            deleted = conn.execute("""
            DELETE FROM cluster_processing
            WHERE service_name = ?
            """, (service_name,))
            self.logger.info(f"Cleared ALL {deleted.rowcount} records for {service_name}")

        # Also clear observations for this service (if table exists)
        if status_filter is None:  # Only clear observations if clearing all records
            try:
                obs_deleted = conn.execute("""
                DELETE FROM environmental_observations
                WHERE dataset = ?
                """, (service_name,))
                self.logger.info(f"Cleared {obs_deleted.rowcount} observations for {service_name}")
            except sqlite3.OperationalError as e:
                if "no such table" in str(e):
                    self.logger.debug("environmental_observations table doesn't exist yet (no observations stored)")
                else:
                    raise

        conn.commit()
        conn.close()

    def get_cluster_geometry(self, cluster_id: int) -> tuple:
        """Get cluster center and tight bbox"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
        SELECT center_lat, center_lon, bbox_minlat, bbox_minlon, bbox_maxlat, bbox_maxlon
        FROM spatial_clusters WHERE cluster_id = ?
        """, (cluster_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        center_lat, center_lon, minlat, minlon, maxlat, maxlon = row

        # Use actual cluster bbox from DBSCAN clustering
        # For single-point clusters (minlat==maxlat), add small buffer (~500m)
        # For multi-point clusters, use actual extent
        if minlat == maxlat and minlon == maxlon:
            # Single point - add 0.005° buffer (~500m at equator)
            minlat = center_lat - 0.005
            maxlat = center_lat + 0.005
            minlon = center_lon - 0.005
            maxlon = center_lon + 0.005

        return Geometry(type="bbox", coordinates=[minlon, minlat, maxlon, maxlat])

    def get_or_create_adapter(self, service_name: str, config: Dict):
        """Get cached adapter or create new one. IMPORTANT: Earth Engine adapters are NOT cached."""
        cache_key = f"{service_name}_{config.get('asset_id', '')}"

        # CRITICAL FIX: Earth Engine adapters should NOT be cached/reused
        # Each query needs a fresh adapter instance to avoid state issues
        # This matches the working notebook pattern where adapters are created per-query
        if config.get('is_earth_engine', False):
            EARTH_ENGINE = CANONICAL_SERVICES["EARTH_ENGINE"]
            return EARTH_ENGINE(asset_id=config['asset_id'])  # Fresh instance every time

        # Cache non-EE adapters (they're stateless and safe to reuse)
        if cache_key not in self.adapters_cache:
            # Map service name to canonical name (most match directly)
            service_map = {
                "NASA_POWER": "NASA_POWER",
                "GBIF": "GBIF",
                "OpenAQ": "OpenAQ",
                "USGS_NWIS": "USGS_NWIS",
                "WQP": "WQP",
                "SSURGO": "SSURGO",
                "OSM_Overpass": "OSM_Overpass"
            }
            canonical_name = service_map.get(service_name, service_name)
            adapter_class = CANONICAL_SERVICES[canonical_name]
            self.adapters_cache[cache_key] = adapter_class()

        return self.adapters_cache[cache_key]

    def process_cluster(self, cluster_id: int, service_name: str, config: Dict) -> tuple:
        """Process single cluster for a service with retry logic for quota errors"""
        geometry = self.get_cluster_geometry(cluster_id)
        if not geometry:
            return ("error", 0, 0, "Cluster geometry not found")

        max_retries = config.get('max_retries', 1) if config.get('retry_on_quota') else 1
        backoff = config.get('backoff_seconds', 60)

        for attempt in range(max_retries):
            try:
                adapter = self.get_or_create_adapter(service_name, config)

                spec = RequestSpec(
                    geometry=geometry,
                    time_range=config['time_range'],
                    variables=None,
                    extra={"timeout": config['timeout']}
                )

                start_time = time.time()
                result = adapter._fetch_rows(spec)
                elapsed = time.time() - start_time

                if result and len(result) > 0:
                    # Store observations
                    obs_count = self._store_observations(cluster_id, service_name, result)
                    return ("success", obs_count, elapsed, None)
                else:
                    return ("no_data", 0, elapsed, "No data returned from service")

            except Exception as e:
                error_msg = str(e).lower()

                # Check for transient errors (timeout, quota, rate limit, network)
                if config.get('retry_on_quota') and attempt < max_retries - 1:
                    if any(keyword in error_msg for keyword in ['quota', 'rate limit', 'too many requests', 'user rate limit exceeded', 'timeout']):
                        self.logger.warning(f"Transient error for {service_name} cluster {cluster_id}, attempt {attempt+1}/{max_retries}. Retrying after {backoff}s...")
                        time.sleep(backoff)
                        continue  # Retry

                # Not a quota error or out of retries
                self.logger.error(f"Error processing cluster {cluster_id} for {service_name}: {str(e)}")
                return ("error", 0, 0, str(e)[:200])

        return ("error", 0, 0, "Max retries exceeded")

    def _store_observations(self, cluster_id: int, service_name: str, rows: List[Dict]) -> int:
        """Store environmental observations"""
        conn = sqlite3.connect(self.db_path)

        obs_data = []
        for row in rows:
            obs_data.append((
                row.get('observation_id'),
                cluster_id,
                service_name,
                row.get('variable'),
                row.get('value'),
                row.get('unit'),
                row.get('time'),
                row.get('latitude'),
                row.get('longitude')
            ))

        conn.executemany("""
        INSERT OR REPLACE INTO env_observations
        (obs_id, cluster_id, service_name, variable, value, unit, time_stamp, lat, lon)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, obs_data)

        conn.commit()
        conn.close()
        return len(obs_data)

    def mark_cluster_processed(self, cluster_id: int, service_name: str, status: str,
                               obs_count: int, processing_time: float, error_msg: Optional[str]):
        """Record cluster processing status"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
        INSERT OR REPLACE INTO cluster_processing
        (cluster_id, service_name, status, obs_count, processing_time, error_message, completed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (cluster_id, service_name, status, obs_count, processing_time, error_msg,
              datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def run_phase(self, phase: int, max_clusters: Optional[int] = None):
        """Run acquisition phase with rate limiting and progress tracking"""
        if phase == 0:
            services = PHASE0_SERVICES
        elif phase == 1:
            services = PHASE1_SERVICES
        elif phase == 2:
            services = PHASE2_SERVICES
        else:
            raise ValueError(f"Invalid phase: {phase}. Must be 0, 1, or 2.")

        phase_name = f"Phase {phase}"
        self.logger.info(f"Starting {phase_name} with {len(services)} services")

        for service_name, config in services.items():
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"Processing service: {service_name}")
            self.logger.info(f"{'='*60}")

            pending = self.get_pending_clusters(service_name)

            if max_clusters:
                pending = pending[:max_clusters]

            self.logger.info(f"Found {len(pending):,} pending clusters")

            if not pending:
                self.logger.info(f"No pending clusters for {service_name}")
                continue

            total_obs = 0
            successful = 0
            failed = 0
            no_data = 0

            with tqdm(total=len(pending), desc=service_name) as pbar:
                for cluster_id in pending:
                    # Process cluster
                    status, obs_count, elapsed, error_msg = self.process_cluster(
                        cluster_id, service_name, config
                    )

                    # Update statistics
                    if status == "success":
                        successful += 1
                        total_obs += obs_count
                    elif status == "no_data":
                        no_data += 1
                    else:
                        failed += 1

                    # Record status
                    self.mark_cluster_processed(
                        cluster_id, service_name, status, obs_count, elapsed, error_msg
                    )

                    # Update progress bar
                    pbar.set_postfix({
                        'success': successful,
                        'no_data': no_data,
                        'failed': failed,
                        'obs': total_obs
                    })
                    pbar.update(1)

                    # Rate limiting - be polite to servers
                    time.sleep(config['rate_limit'])

            # Service summary
            self.logger.info(f"\n{service_name} Summary:")
            self.logger.info(f"  Success: {successful:,} clusters")
            self.logger.info(f"  No data: {no_data:,} clusters")
            self.logger.info(f"  Failed: {failed:,} clusters")
            self.logger.info(f"  Total observations: {total_obs:,}")

        self.logger.info(f"\n{phase_name} complete!")

    def get_status(self) -> Dict:
        """Get current processing status"""
        conn = sqlite3.connect(self.db_path)

        # Overall progress
        cursor = conn.execute("""
        SELECT service_name, status, COUNT(*) as count, SUM(obs_count) as total_obs
        FROM cluster_processing
        GROUP BY service_name, status
        """)

        status_data = cursor.fetchall()

        # Total clusters
        cursor = conn.execute("SELECT COUNT(*) FROM spatial_clusters")
        total_clusters = cursor.fetchone()[0]

        conn.close()

        return {
            'total_clusters': total_clusters,
            'status_by_service': status_data
        }

    def print_status(self):
        """Print current processing status"""
        status = self.get_status()

        print("\n" + "="*60)
        print("ENVIRONMENTAL DATA ACQUISITION STATUS")
        print("="*60)
        print(f"\nTotal spatial clusters: {status['total_clusters']:,}")

        if status['status_by_service']:
            print("\nProgress by service:")
            print(f"{'Service':<25} {'Status':<12} {'Clusters':<12} {'Observations':<15}")
            print("-"*60)

            for service, stat, count, obs in status['status_by_service']:
                obs_str = f"{obs:,}" if obs else "0"
                print(f"{service:<25} {stat:<12} {count:<12} {obs_str:<15}")
        else:
            print("\nNo processing activity recorded yet.")


def main():
    # Build list of all available services dynamically
    all_services = list(PHASE0_SERVICES.keys()) + list(PHASE1_SERVICES.keys()) + list(PHASE2_SERVICES.keys())

    parser = argparse.ArgumentParser(
        description="Acquire environmental data for pangenome analysis",
        epilog="""
Examples:
  # Test with 10 clusters
  %(prog)s --phase 1 --clusters clusters.csv --samples samples.tsv --max-clusters 10

  # Run Phase 1 and Phase 2 in parallel (separate terminals)
  Terminal 1: %(prog)s --phase 1 --clusters clusters.csv --samples samples.tsv
  Terminal 2: %(prog)s --phase 2

  # Run specific service only
  %(prog)s --service NASA_POWER --clusters clusters.csv --samples samples.tsv

  # Check status
  %(prog)s --status

  # Clear all data for SRTM and start fresh
  %(prog)s --clear SRTM

  # Clear only no_data records (to retry with fixed adapter)
  %(prog)s --clear SRTM --clear-status no_data
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--phase', type=int, choices=[0, 1, 2],
                       help='Phase to run (0=unitary services, 1=EE terrain/NDVI, 2=embeddings). Can run Phase 0 with anything!')
    parser.add_argument('--service',
                       choices=all_services,
                       help='Run specific service only (allows fine-grained parallelization)')
    parser.add_argument('--clusters', help='Path to clusters CSV file')
    parser.add_argument('--samples', help='Path to genome samples TSV file')
    parser.add_argument('--max-clusters', type=int, help='Limit number of clusters (for testing)')
    parser.add_argument('--status', action='store_true', help='Show processing status and exit')
    parser.add_argument('--clear', help='Clear data for a service to allow reprocessing (e.g., --clear SRTM)')
    parser.add_argument('--clear-status', help='Clear only specific status records (e.g., --clear-status no_data)')
    parser.add_argument('--db', default='./pangenome_env_data/pangenome_env.db',
                       help='Database path (SQLite supports concurrent reads/writes)')

    args = parser.parse_args()

    # Initialize acquisition system
    acq = EnvironmentalDataAcquisition(db_path=args.db)

    # Clear service data
    if args.clear:
        confirm = input(f"⚠️  Clear {'all' if not args.clear_status else args.clear_status} records for {args.clear}? (yes/no): ")
        if confirm.lower() == 'yes':
            acq.clear_service_data(args.clear, args.clear_status)
            print(f"✅ Cleared {args.clear}")
        else:
            print("Cancelled")
        return

    # Status check
    if args.status:
        acq.print_status()
        return

    # Load data if provided
    if args.samples:
        acq.load_genome_samples(args.samples)

    if args.clusters:
        acq.load_clusters(args.clusters)

    # Run specific service
    if args.service:
        # Map service name to config
        all_services = {**PHASE0_SERVICES, **PHASE1_SERVICES, **PHASE2_SERVICES}
        if args.service not in all_services:
            print(f"Error: Service {args.service} not found")
            return

        config = all_services[args.service]
        acq.logger.info(f"Running single service: {args.service}")

        pending = acq.get_pending_clusters(args.service)
        if args.max_clusters:
            pending = pending[:args.max_clusters]

        if not pending:
            acq.logger.info(f"No pending clusters for {args.service}")
            return

        acq.logger.info(f"Processing {len(pending):,} clusters for {args.service}")

        total_obs = 0
        successful = 0
        failed = 0
        no_data = 0

        with tqdm(total=len(pending), desc=args.service) as pbar:
            for cluster_id in pending:
                status, obs_count, elapsed, error_msg = acq.process_cluster(
                    cluster_id, args.service, config
                )

                if status == "success":
                    successful += 1
                    total_obs += obs_count
                elif status == "no_data":
                    no_data += 1
                else:
                    failed += 1

                acq.mark_cluster_processed(
                    cluster_id, args.service, status, obs_count, elapsed, error_msg
                )

                pbar.set_postfix({
                    'success': successful,
                    'no_data': no_data,
                    'failed': failed,
                    'obs': total_obs
                })
                pbar.update(1)
                time.sleep(config['rate_limit'])

        acq.logger.info(f"{args.service} complete: {successful:,} successful, {total_obs:,} observations")
        return

    # Run phase
    if args.phase:
        acq.run_phase(args.phase, max_clusters=args.max_clusters)
    else:
        print("Please specify --phase, --service, or use --status")
        parser.print_help()


if __name__ == "__main__":
    main()