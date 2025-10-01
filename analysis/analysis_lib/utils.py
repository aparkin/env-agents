"""
Utility functions for analysis pipeline.
"""
import yaml
from pathlib import Path
import pandas as pd
from typing import Dict, Any, Union


def load_config(config_path: Union[str, Path] = 'config.yaml') -> Dict[str, Any]:
    """
    Load analysis configuration from YAML file.

    Parameters
    ----------
    config_path : str or Path
        Path to config.yaml file

    Returns
    -------
    dict
        Configuration dictionary

    Examples
    --------
    >>> config = load_config()
    >>> db_path = config['paths']['database']
    """
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path) as f:
        config = yaml.safe_load(f)

    return config


def save_checkpoint(df: pd.DataFrame, phase: int, name: str,
                   output_dir: Union[str, Path] = 'data') -> Path:
    """
    Save intermediate result as Parquet checkpoint.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame to save
    phase : int
        Phase number (1-8)
    name : str
        Checkpoint name (e.g., 'df_wide', 'correlation_matrix')
    output_dir : str or Path
        Base output directory

    Returns
    -------
    Path
        Path to saved file

    Examples
    --------
    >>> df_wide = pd.DataFrame(...)
    >>> path = save_checkpoint(df_wide, phase=1, name='df_wide')
    >>> print(f"Saved to {path}")
    """
    output_dir = Path(output_dir)
    phase_dir = output_dir / f'phase{phase}_outputs'
    phase_dir.mkdir(parents=True, exist_ok=True)

    output_path = phase_dir / f'{name}.parquet'
    df.to_parquet(output_path, compression='snappy', index=True)

    print(f"✅ Saved checkpoint: {output_path}")
    print(f"   Shape: {df.shape}")

    return output_path


def load_checkpoint(phase: int, name: str,
                   output_dir: Union[str, Path] = 'data') -> pd.DataFrame:
    """
    Load intermediate result from Parquet checkpoint.

    Parameters
    ----------
    phase : int
        Phase number (1-8)
    name : str
        Checkpoint name (e.g., 'df_wide', 'correlation_matrix')
    output_dir : str or Path
        Base output directory

    Returns
    -------
    pd.DataFrame
        Loaded DataFrame

    Raises
    ------
    FileNotFoundError
        If checkpoint doesn't exist

    Examples
    --------
    >>> df_wide = load_checkpoint(phase=1, name='df_wide')
    >>> print(f"Loaded: {df_wide.shape}")
    """
    output_dir = Path(output_dir)
    input_path = output_dir / f'phase{phase}_outputs' / f'{name}.parquet'

    if not input_path.exists():
        raise FileNotFoundError(
            f"Checkpoint not found: {input_path}\n"
            f"Run Phase {phase} first to generate this checkpoint."
        )

    df = pd.read_parquet(input_path)

    print(f"✅ Loaded checkpoint: {input_path}")
    print(f"   Shape: {df.shape}")

    return df


def checkpoint_exists(phase: int, name: str,
                     output_dir: Union[str, Path] = 'data') -> bool:
    """
    Check if a checkpoint file exists.

    Parameters
    ----------
    phase : int
        Phase number (1-8)
    name : str
        Checkpoint name
    output_dir : str or Path
        Base output directory

    Returns
    -------
    bool
        True if checkpoint exists

    Examples
    --------
    >>> if checkpoint_exists(1, 'df_wide'):
    ...     df = load_checkpoint(1, 'df_wide')
    ... else:
    ...     df = compute_df_wide()
    """
    output_dir = Path(output_dir)
    checkpoint_path = output_dir / f'phase{phase}_outputs' / f'{name}.parquet'
    return checkpoint_path.exists()


def get_checkpoint_info(phase: int, name: str,
                       output_dir: Union[str, Path] = 'data') -> Dict[str, Any]:
    """
    Get metadata about a checkpoint file.

    Parameters
    ----------
    phase : int
        Phase number (1-8)
    name : str
        Checkpoint name
    output_dir : str or Path
        Base output directory

    Returns
    -------
    dict
        Metadata including file size, modification time, shape

    Examples
    --------
    >>> info = get_checkpoint_info(1, 'df_wide')
    >>> print(f"Size: {info['size_mb']:.1f} MB")
    >>> print(f"Modified: {info['modified']}")
    """
    output_dir = Path(output_dir)
    checkpoint_path = output_dir / f'phase{phase}_outputs' / f'{name}.parquet'

    if not checkpoint_path.exists():
        return {'exists': False}

    # Get file stats
    stat = checkpoint_path.stat()
    size_mb = stat.st_size / (1024 * 1024)

    # Try to load for shape info (may be slow for large files)
    try:
        df = pd.read_parquet(checkpoint_path)
        shape = df.shape
        columns = list(df.columns[:10])  # First 10 columns
        if len(df.columns) > 10:
            columns.append(f"... and {len(df.columns) - 10} more")
    except Exception as e:
        shape = None
        columns = None

    return {
        'exists': True,
        'path': str(checkpoint_path),
        'size_mb': size_mb,
        'modified': pd.Timestamp.fromtimestamp(stat.st_mtime),
        'shape': shape,
        'columns_preview': columns
    }


def print_phase_status(output_dir: Union[str, Path] = 'data'):
    """
    Print summary of all phase checkpoints.

    Parameters
    ----------
    output_dir : str or Path
        Base output directory

    Examples
    --------
    >>> print_phase_status()
    Phase 1: ✅ Complete (2 checkpoints)
      - df_wide (4789 × 180) - 12.3 MB
      - df_taxonomy (4789 × 15) - 0.8 MB
    Phase 2: 🔄 In progress (1 checkpoint)
      - correlation_matrix (180 × 180) - 2.1 MB
    Phase 3: ⏳ Not started
    """
    output_dir = Path(output_dir)

    common_checkpoints = {
        1: ['df_wide', 'df_taxonomy', 'missing_report'],
        2: ['correlation_matrix', 'pca_results', 'univariate_tests'],
        3: ['pca_by_domain', 'selected_features'],
        4: ['df_imputed'],
        5: ['trained_models', 'feature_importances', 'divergence_results'],
        6: ['validation_scores', 'sensitivity_results'],
        7: ['shap_values', 'hypothesis_tests'],
        8: ['final_figures', 'final_tables']
    }

    print("\n" + "="*60)
    print("PHASE STATUS")
    print("="*60)

    for phase in range(1, 9):
        phase_dir = output_dir / f'phase{phase}_outputs'

        if not phase_dir.exists():
            print(f"\nPhase {phase}: ⏳ Not started")
            continue

        # Count checkpoints
        checkpoints = list(phase_dir.glob('*.parquet'))
        n_checkpoints = len(checkpoints)

        if n_checkpoints == 0:
            print(f"\nPhase {phase}: ⏳ Not started")
        elif n_checkpoints < len(common_checkpoints.get(phase, [])):
            print(f"\nPhase {phase}: 🔄 In progress ({n_checkpoints} checkpoints)")
        else:
            print(f"\nPhase {phase}: ✅ Complete ({n_checkpoints} checkpoints)")

        # List checkpoints
        for cp_path in sorted(checkpoints)[:5]:  # Show first 5
            name = cp_path.stem
            info = get_checkpoint_info(phase, name, output_dir)
            if info['shape']:
                shape_str = f"{info['shape'][0]} × {info['shape'][1]}"
                print(f"  - {name} ({shape_str}) - {info['size_mb']:.1f} MB")
            else:
                print(f"  - {name} - {info['size_mb']:.1f} MB")

        if len(checkpoints) > 5:
            print(f"  ... and {len(checkpoints) - 5} more")

    print("\n" + "="*60 + "\n")
