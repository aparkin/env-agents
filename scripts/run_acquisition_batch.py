#!/usr/bin/env python3
"""
Run environmental data acquisition in parallel batches with progress monitoring.

Features:
- Run multiple services concurrently (default: 4 at a time)
- Real-time progress display with rich formatting
- Automatic recovery from failures
- Summary statistics on completion
"""
import subprocess
import sys
import time
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import argparse
from collections import defaultdict

try:
    from rich.console import Console
    from rich.table import Table
    from rich.live import Live
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID
    from rich.layout import Layout
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("⚠️  Install 'rich' for better progress display: pip install rich")


# Service definitions organized by phase
PHASES = {
    1: {
        'name': 'Essential Climate & Soil',
        'services': ['NASA_POWER', 'SOILGRIDS_PH', 'SOILGRIDS_OC', 'SOILGRIDS_TEXTURE', 'SRTM', 'TERRACLIMATE'],
        'estimated_hours': 16
    },
    2: {
        'name': 'Vegetation & Landcover',
        'services': ['MODIS_NDVI', 'MODIS_EVI', 'MODIS_LANDCOVER', 'WORLDCLIM_BIO'],
        'estimated_hours': 12
    },
    3: {
        'name': 'High-Dimensional Features',
        'services': ['GOOGLE_EMBEDDINGS'],
        'estimated_hours': 24
    },
    4: {
        'name': 'Supplementary Data',
        'services': ['GBIF', 'USGS_NWIS'],
        'estimated_hours': 9
    }
}


class ServiceMonitor:
    """Monitor running services and display progress"""

    def __init__(self, db_path: str, use_rich: bool = True):
        self.db_path = db_path
        self.use_rich = use_rich and RICH_AVAILABLE
        self.console = Console() if self.use_rich else None
        self.processes: Dict[str, subprocess.Popen] = {}
        self.log_handles: Dict[str, any] = {}
        self.start_times: Dict[str, float] = {}
        self.status: Dict[str, str] = {}
        self.stats: Dict[str, Dict] = defaultdict(lambda: {'success': 0, 'failed': 0, 'no_data': 0})

    def get_service_progress(self, service_name: str) -> Dict:
        """Query database for service progress"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get cluster counts by status
            cursor.execute("""
                SELECT status, COUNT(*) as count, SUM(obs_count) as obs
                FROM cluster_processing
                WHERE service_name = ?
                GROUP BY status
            """, (service_name,))

            progress = {'success': 0, 'failed': 0, 'no_data': 0, 'error': 0, 'total_obs': 0}

            for row in cursor.fetchall():
                status, count, obs = row
                progress[status] = count
                if obs:
                    progress['total_obs'] += obs

            # Get total clusters
            cursor.execute("SELECT COUNT(*) FROM spatial_clusters")
            progress['total_clusters'] = cursor.fetchone()[0]

            conn.close()
            return progress

        except Exception:
            return {'success': 0, 'failed': 0, 'no_data': 0, 'total_clusters': 0, 'total_obs': 0}

    def create_progress_table(self) -> Table:
        """Create rich table showing service progress"""
        table = Table(title="Service Acquisition Progress", show_header=True, header_style="bold magenta")

        table.add_column("Service", style="cyan", width=20)
        table.add_column("Status", width=12)
        table.add_column("Progress", width=15)
        table.add_column("Success", justify="right", width=8)
        table.add_column("No Data", justify="right", width=8)
        table.add_column("Failed", justify="right", width=8)
        table.add_column("Obs", justify="right", width=12)
        table.add_column("Time", justify="right", width=10)

        for service in sorted(self.processes.keys()):
            progress = self.get_service_progress(service)
            total = progress['total_clusters']
            processed = progress['success'] + progress['no_data'] + progress['failed'] + progress['error']

            # Determine status
            if service in self.status and self.status[service] == 'completed':
                status_str = "[green]✓ Complete[/green]"
            elif self.processes[service].poll() is not None and self.status.get(service) != 'completed':
                status_str = "[red]✗ Stopped[/red]"
            else:
                status_str = "[yellow]⟳ Running[/yellow]"

            # Progress bar
            if total > 0:
                pct = (processed / total) * 100
                bar_width = 10
                filled = int((pct / 100) * bar_width)
                bar = "█" * filled + "░" * (bar_width - filled)
                progress_str = f"{bar} {pct:>5.1f}%"
            else:
                progress_str = "No data"

            # Elapsed time
            if service in self.start_times:
                elapsed = time.time() - self.start_times[service]
                hours = int(elapsed // 3600)
                mins = int((elapsed % 3600) // 60)
                time_str = f"{hours:02d}:{mins:02d}"
            else:
                time_str = "--:--"

            table.add_row(
                service,
                status_str,
                progress_str,
                str(progress['success']),
                str(progress['no_data']),
                str(progress['failed']),
                f"{progress['total_obs']:,}",
                time_str
            )

        return table

    def print_simple_progress(self):
        """Simple text-based progress display (no rich)"""
        print("\n" + "="*80)
        print(f"Service Progress - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)

        for service in sorted(self.processes.keys()):
            progress = self.get_service_progress(service)
            total = progress['total_clusters']
            processed = progress['success'] + progress['no_data'] + progress['failed']

            if service in self.status and self.status[service] == 'completed':
                status = "✓ Complete"
            elif self.processes[service].poll() is not None:
                status = "✗ Stopped"
            else:
                status = "⟳ Running"

            pct = (processed / total * 100) if total > 0 else 0

            elapsed = time.time() - self.start_times.get(service, time.time())
            mins = int(elapsed // 60)

            print(f"{service:20s} {status:12s} {processed:4d}/{total:4d} ({pct:5.1f}%) "
                  f"✓ {progress['success']:4d}  ✗ {progress['failed']:3d}  "
                  f"obs: {progress['total_obs']:8,d}  time: {mins:3d}m")

        print("="*80)

    def start_service(self, service_name: str):
        """Start a service acquisition process"""
        cmd = ['python', 'scripts/acquire_environmental_data.py', '--service', service_name, '--db', self.db_path]

        # Create log file for this service
        log_dir = Path('notebooks/pangenome_env_data/logs')
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f'{service_name.lower()}.log'

        # Open log file for writing
        log_handle = open(log_file, 'w')

        process = subprocess.Popen(
            cmd,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )

        # Store process and log handle
        self.processes[service_name] = process
        self.log_handles[service_name] = log_handle
        self.start_times[service_name] = time.time()
        self.status[service_name] = 'running'

    def check_service_completion(self, service_name: str) -> bool:
        """Check if service has completed"""
        process = self.processes[service_name]

        if process.poll() is not None:
            # Process finished - close log handle
            if service_name in self.log_handles:
                self.log_handles[service_name].close()
                del self.log_handles[service_name]

            if process.returncode == 0:
                self.status[service_name] = 'completed'
                return True
            else:
                self.status[service_name] = 'failed'
                return True

        return False

    def run_services(self, services: List[str], max_parallel: int = 4):
        """Run services in parallel batches"""
        remaining = list(services)
        completed = []
        failed = []

        if self.use_rich:
            with Live(self.create_progress_table(), refresh_per_second=1, console=self.console) as live:
                while remaining or self.processes:
                    # Start new services if slots available
                    while len(self.processes) < max_parallel and remaining:
                        service = remaining.pop(0)
                        self.start_service(service)
                        time.sleep(2)  # Stagger starts

                    # Check for completions
                    for service in list(self.processes.keys()):
                        if self.check_service_completion(service):
                            if self.status[service] == 'completed':
                                completed.append(service)
                            else:
                                failed.append(service)
                            del self.processes[service]

                    # Update display
                    live.update(self.create_progress_table())
                    time.sleep(5)  # Update every 5 seconds

        else:
            # Simple mode without rich
            while remaining or self.processes:
                # Start new services if slots available
                while len(self.processes) < max_parallel and remaining:
                    service = remaining.pop(0)
                    self.start_service(service)
                    print(f"Started: {service}")
                    time.sleep(2)

                # Check for completions
                for service in list(self.processes.keys()):
                    if self.check_service_completion(service):
                        if self.status[service] == 'completed':
                            completed.append(service)
                            print(f"✓ Completed: {service}")
                        else:
                            failed.append(service)
                            print(f"✗ Failed: {service}")
                        del self.processes[service]

                # Print progress
                if self.processes:
                    self.print_simple_progress()

                time.sleep(10)  # Update every 10 seconds

        return completed, failed

    def print_summary(self, completed: List[str], failed: List[str]):
        """Print final summary"""
        if self.use_rich:
            summary = Table(title="Acquisition Summary", show_header=True, header_style="bold green")
            summary.add_column("Service", style="cyan")
            summary.add_column("Status", width=12)
            summary.add_column("Success", justify="right")
            summary.add_column("No Data", justify="right")
            summary.add_column("Failed", justify="right")
            summary.add_column("Total Obs", justify="right")

            for service in completed + failed:
                progress = self.get_service_progress(service)
                status = "[green]✓ Complete[/green]" if service in completed else "[red]✗ Failed[/red]"

                summary.add_row(
                    service,
                    status,
                    str(progress['success']),
                    str(progress['no_data']),
                    str(progress['failed']),
                    f"{progress['total_obs']:,}"
                )

            self.console.print(summary)

        else:
            print("\n" + "="*80)
            print("SUMMARY")
            print("="*80)
            print(f"Completed: {len(completed)}")
            print(f"Failed: {len(failed)}")

            if failed:
                print(f"\nFailed services: {', '.join(failed)}")
                print("Check logs: notebooks/pangenome_env_data/logs/")

            print("\nRun diagnostic to verify:")
            print("  python scripts/diagnose_database_integrity.py")


def main():
    parser = argparse.ArgumentParser(description='Run environmental data acquisition in parallel')
    parser.add_argument('--phase', type=int, choices=[1, 2, 3, 4],
                       help='Run predefined phase (1=essential, 2=vegetation, 3=embeddings, 4=supplementary)')
    parser.add_argument('--services', nargs='+',
                       help='Specific services to run (space-separated)')
    parser.add_argument('--max-parallel', type=int, default=4,
                       help='Maximum services to run in parallel (default: 4)')
    parser.add_argument('--db-path', default='notebooks/pangenome_env_data/pangenome_env.db',
                       help='Path to database')

    args = parser.parse_args()

    # Determine which services to run
    if args.phase:
        phase_info = PHASES[args.phase]
        services = phase_info['services']
        print(f"Running Phase {args.phase}: {phase_info['name']}")
        print(f"Services: {', '.join(services)}")
        print(f"Estimated time: {phase_info['estimated_hours']} hours\n")
    elif args.services:
        services = args.services
        print(f"Running custom services: {', '.join(services)}\n")
    else:
        parser.error("Must specify either --phase or --services")

    # Confirm
    response = input(f"Run {len(services)} services with max {args.max_parallel} parallel? [y/N] ")
    if response.lower() != 'y':
        print("Cancelled")
        return 1

    # Run acquisition
    monitor = ServiceMonitor(args.db_path, use_rich=RICH_AVAILABLE)

    print("\nStarting acquisition...")
    print("Monitor logs: tail -f notebooks/pangenome_env_data/logs/acquisition_*.log\n")

    start_time = time.time()

    try:
        completed, failed = monitor.run_services(
            services,
            max_parallel=args.max_parallel
        )

    except KeyboardInterrupt:
        print("\n\nInterrupted by user!")
        print("Services will continue running in background.")
        print("Check logs: notebooks/pangenome_env_data/logs/")
        return 1

    # Summary
    elapsed = time.time() - start_time
    hours = int(elapsed // 3600)
    mins = int((elapsed % 3600) // 60)

    print(f"\n\nTotal time: {hours}h {mins}m")

    monitor.print_summary(completed, failed)

    # Next steps
    if failed:
        print("\n⚠️  Some services failed. Check logs and re-run:")
        for service in failed:
            print(f"  python scripts/acquire_environmental_data.py --service {service} --db {monitor.db_path}")

    if completed:
        print("\n✓ Next steps:")
        print("  1. Verify: python scripts/diagnose_database_integrity.py")
        print("  2. Continue analysis: cd analysis/notebooks/")

    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())
