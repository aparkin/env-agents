#!/usr/bin/env python3
"""
Diagnose database integrity issues by comparing cluster_processing
expected observations vs actual observations in env_observations.
"""
import sqlite3
import pandas as pd
from pathlib import Path

def diagnose_integrity(db_path: str):
    """Compare expected vs actual observations per service"""
    conn = sqlite3.connect(db_path)

    print("="*80)
    print("DATABASE INTEGRITY DIAGNOSIS")
    print("="*80)

    # Get expected observations from cluster_processing
    expected_df = pd.read_sql_query("""
        SELECT
            service_name,
            status,
            COUNT(*) as clusters,
            SUM(obs_count) as expected_obs
        FROM cluster_processing
        GROUP BY service_name, status
        ORDER BY service_name, status
    """, conn)

    # Get actual observations from env_observations
    actual_df = pd.read_sql_query("""
        SELECT
            service_name,
            COUNT(*) as actual_obs,
            COUNT(DISTINCT cluster_id) as clusters_with_data,
            COUNT(DISTINCT obs_id) as unique_obs_ids
        FROM env_observations
        GROUP BY service_name
    """, conn)

    # Summarize by service
    summary = expected_df[expected_df['status'] == 'success'].copy()
    summary = summary.rename(columns={'clusters': 'clusters_expected', 'expected_obs': 'expected_obs'})
    summary = summary.merge(actual_df, on='service_name', how='outer')
    summary = summary.fillna(0)

    # Calculate discrepancy
    summary['obs_recovery_rate'] = summary['actual_obs'] / summary['expected_obs'].replace(0, 1)
    summary['cluster_recovery_rate'] = summary['clusters_with_data'] / summary['clusters_expected'].replace(0, 1)

    # Flag problematic services
    summary['status'] = 'OK'
    summary.loc[summary['obs_recovery_rate'] < 0.5, 'status'] = 'CRITICAL'
    summary.loc[(summary['obs_recovery_rate'] >= 0.5) & (summary['obs_recovery_rate'] < 0.9), 'status'] = 'WARNING'

    print("\nSERVICE INTEGRITY REPORT")
    print("-"*80)
    print(f"{'Service':<20} {'Status':<10} {'Expected Obs':<15} {'Actual Obs':<15} {'Recovery %':<12}")
    print("-"*80)

    for _, row in summary.sort_values('obs_recovery_rate').iterrows():
        service = row['service_name']
        status = row['status']
        expected = int(row['expected_obs'])
        actual = int(row['actual_obs'])
        recovery = row['obs_recovery_rate'] * 100

        status_icon = {'CRITICAL': '🔴', 'WARNING': '🟡', 'OK': '🟢'}.get(status, '⚪')
        print(f"{service:<20} {status_icon} {status:<8} {expected:>14,} {actual:>14,} {recovery:>10.1f}%")

    print("-"*80)

    # Summary statistics
    critical = summary[summary['status'] == 'CRITICAL']
    warning = summary[summary['status'] == 'WARNING']
    ok = summary[summary['status'] == 'OK']

    print(f"\nSUMMARY:")
    print(f"  🔴 Critical (< 50% recovery): {len(critical)} services")
    print(f"  🟡 Warning (50-90% recovery): {len(warning)} services")
    print(f"  🟢 OK (> 90% recovery): {len(ok)} services")

    total_expected = summary['expected_obs'].sum()
    total_actual = summary['actual_obs'].sum()
    print(f"\n  Total expected observations: {int(total_expected):,}")
    print(f"  Total actual observations: {int(total_actual):,}")
    print(f"  Overall recovery rate: {total_actual/total_expected*100:.1f}%")

    # Services to re-run
    print("\n" + "="*80)
    print("RECOMMENDED ACTIONS")
    print("="*80)

    to_rerun = summary[summary['status'].isin(['CRITICAL', 'WARNING'])].copy()
    to_rerun = to_rerun.sort_values('expected_obs', ascending=False)

    if len(to_rerun) > 0:
        print("\n⚠️  The following services need to be re-run:\n")
        for _, row in to_rerun.iterrows():
            service = row['service_name']
            expected = int(row['expected_obs'])
            actual = int(row['actual_obs'])
            missing = expected - actual
            print(f"  • {service}")
            print(f"    - Missing: {missing:,} observations ({(1-row['obs_recovery_rate'])*100:.1f}% loss)")
            print(f"    - Clusters affected: {int(row['clusters_expected'])}")
            print(f"    - Command: python scripts/acquire_environmental_data.py --service {service} --clear")
            print()

        print("\n🔧 STEPS TO FIX:")
        print("  1. Back up current database:")
        print("     cp notebooks/pangenome_env_data/pangenome_env.db notebooks/pangenome_env_data/pangenome_env.db.backup")
        print()
        print("  2. For each service above, run:")
        print("     python scripts/acquire_environmental_data.py --service <SERVICE> --clear")
        print()
        print("  3. Re-run this diagnostic to verify recovery")
        print()
        print("⏱️  Estimated time: Several days for all services")
    else:
        print("\n✅ All services have good data integrity (> 90% recovery)")

    print("\n" + "="*80)

    # Detailed service breakdown
    print("\nDETAILED SERVICE BREAKDOWN")
    print("-"*80)

    for service in summary['service_name'].unique():
        service_data = summary[summary['service_name'] == service].iloc[0]

        print(f"\n{service}:")
        print(f"  Expected: {int(service_data['expected_obs']):,} obs from {int(service_data['clusters_expected'])} clusters")
        print(f"  Actual: {int(service_data['actual_obs']):,} obs from {int(service_data['clusters_with_data'])} clusters")
        print(f"  Unique obs_ids: {int(service_data['unique_obs_ids']):,}")

        # Check for obs_id collisions
        if service_data['actual_obs'] > service_data['unique_obs_ids']:
            collisions = int(service_data['actual_obs'] - service_data['unique_obs_ids'])
            print(f"  ⚠️  WARNING: {collisions} obs_id collisions detected!")

        # Sample observations
        sample_obs = pd.read_sql_query(f"""
            SELECT obs_id, cluster_id, variable, time_stamp
            FROM env_observations
            WHERE service_name = '{service}'
            ORDER BY RANDOM()
            LIMIT 3
        """, conn)

        if len(sample_obs) > 0:
            print(f"  Sample obs_ids:")
            for _, obs in sample_obs.iterrows():
                print(f"    - {obs['obs_id'][:60]}...")

    conn.close()

    return summary

if __name__ == '__main__':
    import sys

    db_path = sys.argv[1] if len(sys.argv) > 1 else 'notebooks/pangenome_env_data/pangenome_env.db'

    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        sys.exit(1)

    diagnose_integrity(db_path)
