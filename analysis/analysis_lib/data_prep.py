"""
Data preparation utilities for Phase 1.

Functions for extracting environmental data from database,
pivoting to wide format, and loading taxonomy.
"""
import pandas as pd
import sqlite3
from pathlib import Path
from typing import List, Optional, Union, Dict, Tuple
import json
from .utils import load_config, save_checkpoint, load_checkpoint


def extract_environmental_data(
    db_path: Union[str, Path],
    services: Optional[List[str]] = None,
    cluster_ids: Optional[List[int]] = None
) -> pd.DataFrame:
    """
    Extract environmental observations from database.

    Parameters
    ----------
    db_path : str or Path
        Path to SQLite database
    services : list of str, optional
        List of service names to include. If None, include all.
    cluster_ids : list of int, optional
        List of cluster IDs to include. If None, include all.

    Returns
    -------
    pd.DataFrame
        Long-format environmental data with columns:
        - cluster_id: int
        - service_name: str
        - variable: str
        - value: float
        - time: str (ISO timestamp)
        - latitude: float
        - longitude: float

    Examples
    --------
    >>> df = extract_environmental_data(
    ...     'pangenome_env.db',
    ...     services=['NASA_POWER', 'SoilGrids_pH']
    ... )
    >>> print(df.shape)
    (125000, 7)
    """
    conn = sqlite3.connect(db_path)

    # Base query
    # Note: Actual schema uses time_stamp, lat, lon (not time, latitude, longitude)
    query = """
    SELECT
        cluster_id,
        service_name,
        variable,
        value,
        time_stamp as time,
        lat as latitude,
        lon as longitude
    FROM env_observations
    WHERE 1=1
    """

    params = []

    # Filter by services
    if services:
        placeholders = ','.join(['?'] * len(services))
        query += f" AND service_name IN ({placeholders})"
        params.extend(services)

    # Filter by clusters
    if cluster_ids:
        placeholders = ','.join(['?'] * len(cluster_ids))
        query += f" AND cluster_id IN ({placeholders})"
        params.extend(cluster_ids)

    print(f"Extracting environmental data from {db_path}...")
    if services:
        print(f"  Services: {len(services)} selected")
    if cluster_ids:
        print(f"  Clusters: {len(cluster_ids)} selected")

    df = pd.read_sql_query(query, conn, params=params if params else None)

    conn.close()

    print(f"✅ Extracted {len(df):,} observations")
    print(f"   Clusters: {df['cluster_id'].nunique()}")
    print(f"   Services: {df['service_name'].nunique()}")
    print(f"   Variables: {df['variable'].nunique()}")

    return df


def pivot_to_wide(
    df_long: pd.DataFrame,
    agg_func: str = 'mean',
    add_service_prefix: bool = True
) -> pd.DataFrame:
    """
    Convert long-format environmental data to wide format.

    Parameters
    ----------
    df_long : pd.DataFrame
        Long-format data with cluster_id, service_name, variable, value columns
    agg_func : str or callable
        Aggregation function for multiple observations per cluster-variable.
        Options: 'mean', 'median', 'min', 'max', 'std', 'first', 'last'
    add_service_prefix : bool
        If True, prefix variable names with service_name (e.g., NASA_POWER__temperature)

    Returns
    -------
    pd.DataFrame
        Wide-format matrix with:
        - Index: cluster_id
        - Columns: environmental variables
        - Values: aggregated measurements

    Examples
    --------
    >>> df_wide = pivot_to_wide(df_long, agg_func='mean')
    >>> print(df_wide.shape)
    (4789, 180)
    """
    print(f"Pivoting to wide format (agg={agg_func})...")

    # Create composite variable name if requested
    if add_service_prefix:
        df_long = df_long.copy()
        df_long['full_variable'] = (
            df_long['service_name'].astype(str) + '__' +
            df_long['variable'].astype(str)
        )
        value_col = 'full_variable'
    else:
        value_col = 'variable'

    # Pivot
    df_wide = df_long.pivot_table(
        index='cluster_id',
        columns=value_col,
        values='value',
        aggfunc=agg_func
    )

    print(f"✅ Pivoted to wide format")
    print(f"   Shape: {df_wide.shape}")
    print(f"   Clusters: {len(df_wide)}")
    print(f"   Variables: {len(df_wide.columns)}")

    # Calculate data completeness
    completeness = df_wide.notna().sum() / len(df_wide)
    print(f"   Median completeness: {completeness.median():.1%}")
    print(f"   Variables with >70% data: {(completeness > 0.7).sum()}")

    return df_wide


def load_taxonomy(
    taxonomy_file: Union[str, Path],
    min_genomes: int = 1
) -> pd.DataFrame:
    """
    Load taxonomic data for clusters.

    Parameters
    ----------
    taxonomy_file : str or Path
        Path to GTDB taxonomy TSV file
        Expected columns: cluster_id, genome_count, phylum, class, order, etc.
    min_genomes : int
        Minimum genomes per cluster to include

    Returns
    -------
    pd.DataFrame
        Taxonomy with cluster_id as index and taxonomic levels as columns

    Examples
    --------
    >>> df_tax = load_taxonomy('df_gtdb_tagged_cleaneed.tsv')
    >>> print(df_tax.columns)
    Index(['genome_count', 'phylum', 'class', 'order', 'family', 'genus'])
    """
    print(f"Loading taxonomy from {taxonomy_file}...")

    df = pd.read_csv(taxonomy_file, sep='\t')

    print(f"✅ Loaded {len(df):,} rows")

    # Filter by genome count
    if min_genomes > 1:
        before = len(df)
        df = df[df['genome_count'] >= min_genomes].copy()
        print(f"   Filtered to {len(df):,} clusters with ≥{min_genomes} genomes ({before - len(df)} removed)")

    # Ensure cluster_id is set as index
    if 'cluster_id' in df.columns:
        df = df.set_index('cluster_id')

    # Report taxonomic levels
    tax_levels = [col for col in df.columns if col in ['phylum', 'class', 'order', 'family', 'genus', 'species']]
    print(f"   Taxonomic levels: {', '.join(tax_levels)}")

    # Count unique taxa at each level
    for level in tax_levels:
        n_unique = df[level].nunique()
        print(f"   {level.capitalize()}: {n_unique} unique")

    return df


def create_presence_absence_matrix(
    df_taxonomy: pd.DataFrame,
    taxonomic_level: str = 'phylum',
    min_prevalence: float = 0.01
) -> pd.DataFrame:
    """
    Create presence/absence matrix for taxa.

    Parameters
    ----------
    df_taxonomy : pd.DataFrame
        Taxonomy DataFrame with cluster_id as index
    taxonomic_level : str
        Taxonomic level to use ('phylum', 'class', 'order', etc.)
    min_prevalence : float
        Minimum fraction of clusters where taxon must be present (0-1)

    Returns
    -------
    pd.DataFrame
        Binary matrix with cluster_id as index and taxa as columns
        Values: 1 (present) or 0 (absent)

    Examples
    --------
    >>> df_pa = create_presence_absence_matrix(df_tax, level='phylum', min_prevalence=0.01)
    >>> print(df_pa.sum(axis=0))  # Count clusters per phylum
    Pseudomonadota    3421
    Actinomycetota    2103
    ...
    """
    print(f"Creating presence/absence matrix for {taxonomic_level}...")

    # Get one-hot encoding
    df_pa = pd.get_dummies(df_taxonomy[taxonomic_level], prefix=taxonomic_level)

    # Filter by prevalence
    n_clusters = len(df_pa)
    min_count = int(min_prevalence * n_clusters)
    prevalence = df_pa.sum(axis=0) / n_clusters

    taxa_to_keep = prevalence[prevalence >= min_prevalence].index
    df_pa = df_pa[taxa_to_keep]

    print(f"✅ Created presence/absence matrix")
    print(f"   Taxonomic level: {taxonomic_level}")
    print(f"   Taxa retained: {len(taxa_to_keep)} (≥{min_prevalence:.1%} prevalence)")
    print(f"   Taxa removed: {len(prevalence) - len(taxa_to_keep)} (too rare)")

    # Show top taxa
    counts = df_pa.sum(axis=0).sort_values(ascending=False)
    print(f"\n   Top 5 {taxonomic_level}:")
    for taxon, count in counts.head(5).items():
        taxon_name = taxon.replace(f'{taxonomic_level}_', '')
        print(f"     {taxon_name}: {count} clusters ({count/n_clusters:.1%})")

    return df_pa


def merge_env_taxonomy(
    df_env: pd.DataFrame,
    df_taxonomy: pd.DataFrame,
    how: str = 'inner'
) -> pd.DataFrame:
    """
    Merge environmental and taxonomic data.

    Parameters
    ----------
    df_env : pd.DataFrame
        Environmental data (wide format) with cluster_id as index
    df_taxonomy : pd.DataFrame
        Taxonomy data with cluster_id as index
    how : str
        Join type: 'inner', 'left', 'right', 'outer'

    Returns
    -------
    pd.DataFrame
        Combined dataset with both environmental and taxonomic columns

    Examples
    --------
    >>> df_combined = merge_env_taxonomy(df_env, df_tax, how='inner')
    >>> print(df_combined.shape)
    (4789, 195)  # 180 env vars + 15 tax columns
    """
    print(f"Merging environmental and taxonomic data (join={how})...")

    df_merged = df_env.join(df_taxonomy, how=how)

    print(f"✅ Merged datasets")
    print(f"   Shape: {df_merged.shape}")
    print(f"   Clusters: {len(df_merged)}")
    print(f"   Total columns: {len(df_merged.columns)}")

    # Check for missing data
    missing_env = df_merged[df_env.columns].isna().all(axis=1).sum()
    missing_tax = df_merged[df_taxonomy.columns].isna().all(axis=1).sum()

    if missing_env > 0:
        print(f"   ⚠️  {missing_env} clusters missing all environmental data")
    if missing_tax > 0:
        print(f"   ⚠️  {missing_tax} clusters missing taxonomy")

    return df_merged


def analyze_missing_data(df: pd.DataFrame) -> Dict:
    """
    Analyze missing data patterns.

    Parameters
    ----------
    df : pd.DataFrame
        Wide-format data matrix

    Returns
    -------
    dict
        Missing data report with:
        - completeness_by_variable: Series
        - completeness_by_cluster: Series
        - missing_patterns: DataFrame (top patterns)
        - correlation_of_missingness: DataFrame

    Examples
    --------
    >>> report = analyze_missing_data(df_wide)
    >>> print(f"Variables with >70% data: {(report['completeness_by_variable'] > 0.7).sum()}")
    """
    print("Analyzing missing data patterns...")

    n_clusters = len(df)
    n_variables = len(df.columns)

    # Completeness by variable
    completeness_var = df.notna().sum() / n_clusters
    completeness_var = completeness_var.sort_values(ascending=False)

    # Completeness by cluster
    completeness_cluster = df.notna().sum(axis=1) / n_variables
    completeness_cluster = completeness_cluster.sort_values(ascending=False)

    # Missing data patterns (which variables co-occur as missing?)
    missing_matrix = df.isna().astype(int)

    # Correlation of missingness
    missing_corr = missing_matrix.corr()

    # Summary statistics
    print(f"✅ Missing data analysis complete")
    print(f"\n   Variable completeness:")
    print(f"     Mean: {completeness_var.mean():.1%}")
    print(f"     Median: {completeness_var.median():.1%}")
    print(f"     >70%: {(completeness_var > 0.7).sum()} variables")
    print(f"     >50%: {(completeness_var > 0.5).sum()} variables")
    print(f"     <10%: {(completeness_var < 0.1).sum()} variables (very sparse)")

    print(f"\n   Cluster completeness:")
    print(f"     Mean: {completeness_cluster.mean():.1%}")
    print(f"     Median: {completeness_cluster.median():.1%}")
    print(f"     >50%: {(completeness_cluster > 0.5).sum()} clusters")

    report = {
        'completeness_by_variable': completeness_var,
        'completeness_by_cluster': completeness_cluster,
        'correlation_of_missingness': missing_corr,
        'n_clusters': n_clusters,
        'n_variables': n_variables
    }

    return report


# Re-export utils functions for convenience
__all__ = [
    'extract_environmental_data',
    'pivot_to_wide',
    'load_taxonomy',
    'create_presence_absence_matrix',
    'merge_env_taxonomy',
    'analyze_missing_data',
    'save_checkpoint',
    'load_checkpoint'
]
