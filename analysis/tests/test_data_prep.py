"""
Unit tests for data preparation functions.

Run: pytest tests/test_data_prep.py -v
"""
import pytest
import pandas as pd
import sys
from pathlib import Path

# Add analysis_lib to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis_lib import data_prep, utils


def test_checkpoint_save_load(tmp_path):
    """Test checkpoint saving and loading."""
    # Create test dataframe
    df = pd.DataFrame({
        'a': [1, 2, 3],
        'b': [4, 5, 6]
    })

    # Save checkpoint
    output_path = data_prep.save_checkpoint(
        df, phase=1, name='test', output_dir=tmp_path
    )

    assert output_path.exists()

    # Load checkpoint
    df_loaded = data_prep.load_checkpoint(
        phase=1, name='test', output_dir=tmp_path
    )

    pd.testing.assert_frame_equal(df, df_loaded)


def test_pivot_to_wide():
    """Test pivoting from long to wide format."""
    # Create mock long-format data
    df_long = pd.DataFrame({
        'cluster_id': [1, 1, 2, 2, 3, 3],
        'service_name': ['NASA', 'SOIL', 'NASA', 'SOIL', 'NASA', 'SOIL'],
        'variable': ['temp', 'pH', 'temp', 'pH', 'temp', 'pH'],
        'value': [25.0, 6.5, 20.0, 7.0, 30.0, 5.5]
    })

    # Pivot
    df_wide = data_prep.pivot_to_wide(
        df_long, agg_func='mean', add_service_prefix=True
    )

    # Checks
    assert df_wide.shape == (3, 2)  # 3 clusters, 2 variables
    assert df_wide.index.name == 'cluster_id'
    assert 'NASA__temp' in df_wide.columns
    assert 'SOIL__pH' in df_wide.columns
    assert df_wide.loc[1, 'NASA__temp'] == 25.0


def test_create_presence_absence_matrix():
    """Test creation of presence/absence matrix."""
    # Mock taxonomy
    df_tax = pd.DataFrame({
        'cluster_id': [1, 2, 3, 4, 5],
        'phylum': ['A', 'A', 'B', 'B', 'C']
    }).set_index('cluster_id')

    # Create PA matrix with 40% min prevalence (2/5 clusters)
    df_pa = data_prep.create_presence_absence_matrix(
        df_tax, taxonomic_level='phylum', min_prevalence=0.4
    )

    # Phylum A and B have 2/5 = 40%, Phylum C has 1/5 = 20%
    # Should keep A and B only
    assert df_pa.shape == (5, 2)  # 5 clusters, 2 phyla
    assert 'phylum_A' in df_pa.columns
    assert 'phylum_B' in df_pa.columns
    assert 'phylum_C' not in df_pa.columns


def test_merge_env_taxonomy():
    """Test merging environmental and taxonomic data."""
    # Mock data
    df_env = pd.DataFrame({
        'var1': [1.0, 2.0, 3.0]
    }, index=pd.Index([1, 2, 3], name='cluster_id'))

    df_tax = pd.DataFrame({
        'phylum': ['A', 'B', 'C']
    }, index=pd.Index([1, 2, 4], name='cluster_id'))  # Note: cluster 4 not in env

    # Inner join
    df_merged = data_prep.merge_env_taxonomy(df_env, df_tax, how='inner')

    assert len(df_merged) == 2  # Only clusters 1 and 2 in both
    assert 'var1' in df_merged.columns
    assert 'phylum' in df_merged.columns


def test_analyze_missing_data():
    """Test missing data analysis."""
    # Mock data with missing values
    df = pd.DataFrame({
        'var1': [1.0, 2.0, 3.0, 4.0, 5.0],  # 100% complete
        'var2': [1.0, None, 3.0, None, 5.0],  # 60% complete
        'var3': [None, None, None, None, None]  # 0% complete
    })

    report = data_prep.analyze_missing_data(df)

    assert 'completeness_by_variable' in report
    assert 'completeness_by_cluster' in report
    assert report['completeness_by_variable']['var1'] == 1.0
    assert report['completeness_by_variable']['var2'] == 0.6
    assert report['completeness_by_variable']['var3'] == 0.0


def test_config_loading():
    """Test configuration loading."""
    # This will fail if config.yaml doesn't exist
    # Skip in CI environments
    import os
    if 'CI' in os.environ:
        pytest.skip("Skipping config test in CI")

    config = utils.load_config('../config.yaml')
    assert 'paths' in config
    assert 'modeling' in config


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
