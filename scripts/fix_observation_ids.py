#!/usr/bin/env python3
"""
Fix observation IDs in the database by recomputing them using the canonical function.

This script reads existing observations and recomputes their observation_ids
without re-fetching any data from upstream services.

Usage:
    python scripts/fix_observation_ids.py
    python scripts/fix_observation_ids.py --db notebooks/pangenome_env_data/pangenome_env.db --dry-run
"""

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import List, Dict
import pandas as pd
from tqdm import tqdm

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from env_agents.core.ids import compute_observation_id


def get_service_stats(db_path: str) -> List[Dict]:
    """Get observation counts per service"""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("""
        SELECT service_name, COUNT(*) as obs_count
        FROM env_observations
        GROUP BY service_name
        ORDER BY service_name
    """)
    stats = [{'service': row[0], 'count': row[1]} for row in cursor.fetchall()]
    conn.close()
    return stats


def check_id_collisions(db_path: str) -> Dict:
    """Check current state of observation IDs"""
    conn = sqlite3.connect(db_path)

    # Total observations
    total_obs = conn.execute("SELECT COUNT(*) FROM env_observations").fetchone()[0]

    # Unique IDs
    unique_ids = conn.execute("SELECT COUNT(DISTINCT obs_id) FROM env_observations").fetchone()[0]

    # NULL IDs
    null_ids = conn.execute("SELECT COUNT(*) FROM env_observations WHERE obs_id IS NULL").fetchone()[0]

    conn.close()

    return {
        'total_observations': total_obs,
        'unique_ids': unique_ids,
        'null_ids': null_ids,
        'collisions': total_obs - unique_ids
    }


def fix_observation_ids(db_path: str, chunk_size: int = 50000, dry_run: bool = False):
    """
    Recompute observation IDs for all observations in the database.
    Processes in chunks to manage memory.
    """

    print("=" * 80)
    print("OBSERVATION ID MIGRATION")
    print("=" * 80)
    print()

    # Check current state
    print("Analyzing current state...")
    stats = get_service_stats(db_path)
    id_stats = check_id_collisions(db_path)

    print(f"\nCurrent State:")
    print(f"  Total observations: {id_stats['total_observations']:,}")
    print(f"  Unique IDs: {id_stats['unique_ids']:,}")
    print(f"  NULL IDs: {id_stats['null_ids']:,}")
    print(f"  ID collisions: {id_stats['collisions']:,}")
    print()

    print("Observations by service:")
    for s in stats:
        print(f"  {s['service']:20s} {s['count']:>10,} observations")
    print()

    if dry_run:
        print("DRY RUN - No changes will be made")
        print()
        return

    # Confirm
    response = input("Proceed with ID migration? [yes/no] ")
    if response.lower() != 'yes':
        print("Cancelled")
        return

    print("\nStarting migration...")
    print(f"Processing in chunks of {chunk_size:,} observations")
    print()

    conn = sqlite3.connect(db_path)

    # Get total count for progress bar
    total_count = conn.execute("SELECT COUNT(*) FROM env_observations").fetchone()[0]

    # Process in chunks using ROWID
    updated_count = 0

    with tqdm(total=total_count, desc="Fixing observation IDs", unit="obs") as pbar:
        offset = 0

        while True:
            # Fetch chunk using cursor instead of read_sql_query to preserve ROWID
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT ROWID, cluster_id, service_name, variable, value, unit,
                       time_stamp, lat, lon, obs_id
                FROM env_observations
                LIMIT {chunk_size} OFFSET {offset}
            """)

            rows = cursor.fetchall()
            cursor.close()

            if len(rows) == 0:
                break

            # Convert to DataFrame
            df = pd.DataFrame(rows, columns=[
                'rowid', 'cluster_id', 'service_name', 'variable', 'value', 'unit',
                'time_stamp', 'lat', 'lon', 'obs_id'
            ])

            # Prepare DataFrame for compute_observation_id
            # Map database columns to expected column names
            df_for_id = df.rename(columns={
                'time_stamp': 'time',
                'lat': 'latitude',
                'lon': 'longitude',
                'service_name': 'dataset'  # Use service_name as dataset
            })

            # Add missing columns with defaults if needed
            for col in ['spatial_id', 'depth_top_cm', 'depth_bottom_cm', 'temporal_coverage']:
                if col not in df_for_id.columns:
                    df_for_id[col] = ""

            # Compute new observation IDs
            new_ids = compute_observation_id(df_for_id)

            # Update database
            updates = []
            for idx, (rowid, new_id) in enumerate(zip(df['rowid'], new_ids)):
                updates.append((new_id, rowid))

            conn.executemany("""
                UPDATE env_observations
                SET obs_id = ?
                WHERE ROWID = ?
            """, updates)

            conn.commit()

            updated_count += len(updates)
            pbar.update(len(updates))

            offset += chunk_size

    conn.close()

    print()
    print(f"✓ Updated {updated_count:,} observations")
    print()

    # Check final state
    print("Verifying results...")
    final_stats = check_id_collisions(db_path)

    print(f"\nFinal State:")
    print(f"  Total observations: {final_stats['total_observations']:,}")
    print(f"  Unique IDs: {final_stats['unique_ids']:,}")
    print(f"  NULL IDs: {final_stats['null_ids']:,}")
    print(f"  ID collisions: {final_stats['collisions']:,}")
    print()

    if final_stats['null_ids'] == 0 and final_stats['collisions'] < id_stats['collisions']:
        print("✅ Migration successful!")
        print(f"   Reduced collisions from {id_stats['collisions']:,} to {final_stats['collisions']:,}")
    else:
        print("⚠️  Warning: Unexpected ID collision count after migration")
        print("   Some collisions may be legitimate (e.g., identical static values)")

    print()
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description='Fix observation IDs in database')
    parser.add_argument('--db', default='notebooks/pangenome_env_data/pangenome_env.db',
                       help='Path to database')
    parser.add_argument('--chunk-size', type=int, default=50000,
                       help='Number of observations to process at once (default: 50000)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without making changes')

    args = parser.parse_args()

    # Check database exists
    if not Path(args.db).exists():
        print(f"Error: Database not found at {args.db}")
        return 1

    try:
        fix_observation_ids(args.db, args.chunk_size, args.dry_run)
        return 0
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 1
    except Exception as e:
        print(f"\n\nError: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
