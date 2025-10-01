# Environmental-Taxonomic Analysis

**Comprehensive analysis of environmental determinants of microbial distribution across 83,227 genomes**

## Overview

This directory contains the complete analysis pipeline implementing the plan described in [docs/operations/COMPREHENSIVE_ANALYSIS_PLAN.md](../docs/operations/COMPREHENSIVE_ANALYSIS_PLAN.md).

**Goal**: Identify environmental features and their interactions that predict taxonomic distribution, accounting for correlations among environmental variables (pH/C/N confounds), and determine where in the taxonomic tree environmental niche differentiation occurs.

**Data**:
- **Genomes**: 83,227 GTDB-classified genomes (presence/absence only)
- **Spatial clusters**: 4,789 locations (DBSCAN-clustered)
- **Environmental observations**: 1.7M+ → 16-20M (16 services)
- **Environmental variables**: ~180 parameters across climate, soil, vegetation, topography

## Quick Start

### 1. Setup

```bash
cd analysis/
pip install -r requirements.txt
```

### 2. Configure paths

Edit `config.yaml` to point to your data:
```yaml
database_path: "../notebooks/pangenome_env_data/pangenome_env.db"
taxonomy_file: "../notebooks/df_gtdb_tagged_cleaneed.tsv"
```

### 3. Run Phase 1 (Data Preparation)

**Option A: Run all steps via script**
```bash
python scripts/phase1_data_prep.py
```

**Option B: Explore interactively**
```bash
jupyter notebook notebooks/01_data_prep/
```

Start with `01a_extract_pivot.ipynb`

### 4. Check outputs

```bash
ls data/phase1_outputs/
# Expected: df_wide.parquet, df_taxonomy.parquet, missing_report.json
```

## Project Status

**Last updated**: 2025-10-01

| Phase | Status | Key Outputs |
|-------|--------|-------------|
| 1. Data Prep | ⏳ Not started | Wide-format matrix, missing data report |
| 2. EDA | ⏳ Pending | Correlation structure, univariate associations |
| 3. Dimensionality | ⏳ Pending | 50 composite features from 180 vars |
| 4. Imputation | ⏳ Pending | Complete dataset strategy |
| 5. Modeling | ⏳ Pending | CatBoost models, hierarchical divergence |
| 6. Validation | ⏳ Pending | Cross-validation, sensitivity analyses |
| 7. Interpretation | ⏳ Pending | SHAP values, hypothesis tests |
| 8. Reporting | ⏳ Pending | Publication-ready figures/tables |

See [docs/PHASE_STATUS.md](docs/PHASE_STATUS.md) for detailed progress.

## Directory Structure

```
analysis/
├── README.md                    # This file
├── config.yaml                  # Central configuration
├── requirements.txt             # Python dependencies
│
├── notebooks/                   # Interactive exploration
│   ├── 00_dashboard.ipynb      # Quick overview of results
│   ├── 01_data_prep/           # Phase 1 notebooks
│   ├── 02_eda/                 # Phase 2 notebooks
│   └── ...                     # Phases 3-8
│
├── scripts/                     # Production pipelines
│   ├── phase1_data_prep.py     # Run all Phase 1 steps
│   ├── phase2_eda.py
│   └── ...
│
├── analysis_lib/                # Reusable functions
│   ├── __init__.py
│   ├── data_prep.py            # Extract, pivot, characterize
│   ├── missing_data.py         # Missingness analysis
│   ├── modeling.py             # CatBoost wrappers
│   ├── divergence.py           # Hierarchical divergence
│   └── visualization.py        # Standard plots
│
├── data/                        # Intermediate outputs (gitignored)
│   ├── phase1_outputs/
│   │   ├── df_wide.parquet     # 4,789 clusters × 180 env vars
│   │   ├── df_taxonomy.parquet # Taxonomy per cluster
│   │   └── missing_report.json # Missingness characterization
│   └── phase2_outputs/
│       └── ...
│
├── results/                     # Publication outputs
│   ├── figures/                # PDF figures
│   ├── tables/                 # CSV tables
│   └── models/                 # Trained CatBoost models (.cbm)
│
├── tests/                       # Validation
│   ├── test_data_prep.py       # Unit tests
│   └── validate_pipeline.py    # End-to-end checks
│
└── docs/                        # Analysis documentation
    ├── ANALYSIS_LOG.md         # Decision log
    ├── PHASE_STATUS.md         # Detailed progress
    └── DEPENDENCIES.md         # Software versions
```

## Key Analyses

### 1. Hierarchical Divergence Analysis (NEW!)

**Where in the taxonomic tree do environmental niches split?**

Example question: Do Proteobacteria classes (Alpha, Beta, Gamma) have different environmental preferences?

- **Method**: Compare environmental models for sibling taxa
- **Output**: "Environmental differentiation tree" showing where niches diverge
- **Applications**:
  - Identify optimal taxonomic resolution for modeling
  - Understand when ecological specialization evolved

See: `notebooks/05_modeling/05c_hierarchical_divergence.ipynb`

### 2. Conditional Variable Importance

**Does pH matter independent of carbon? Or is it confounded?**

- **Method**: Partial correlations, conditional permutation importance
- **Goal**: Distinguish true predictors from correlated bystanders
- **Example**: If pH-Acidobacteria association vanishes after controlling for soil C, then pH effect is confounded

See: `notebooks/05_modeling/05b_conditional_importance.ipynb`

### 3. Taxon-Specific Models

**Binary classification per taxon**: P(taxon present | environment)

- 15-20 models (one per major phylum)
- CatBoost GBDT (handles mixed types, missing data, interactions)
- Interpretable via SHAP values and partial dependence plots

See: `notebooks/05_modeling/05a_baseline_models.ipynb`

## Development Workflow

**Typical iteration:**

1. **Explore** in Jupyter notebook (`notebooks/`)
2. **Extract** working functions to library (`analysis_lib/`)
3. **Create** production script (`scripts/`)
4. **Test** functionality (`tests/`)
5. **Save** checkpoint (`data/phaseN_outputs/`)
6. **Document** decisions (`docs/ANALYSIS_LOG.md`)

**Example (Phase 1):**
```bash
# Explore data extraction
jupyter notebook notebooks/01_data_prep/01a_extract_pivot.ipynb

# Move proven code to library
# Edit: analysis_lib/data_prep.py

# Create production script
python scripts/phase1_data_prep.py

# Validate
python tests/test_data_prep.py
```

## Checkpoints and Caching

Each phase saves intermediate results as Parquet files to avoid re-computation:

```python
from analysis_lib import data_prep

# Save checkpoint
df_wide = ...  # computed result
data_prep.save_checkpoint(df_wide, phase=1, name='df_wide')

# Load checkpoint (skip re-computation)
df_wide = data_prep.load_checkpoint(phase=1, name='df_wide')
```

This allows:
- ✅ Resume analysis after interruption
- ✅ Skip expensive computations
- ✅ Experiment with different parameters in later phases

## Testing Strategy

**Quick validation after each phase:**

```bash
# Run all tests
python -m pytest tests/ -v

# Or just pipeline validation
python tests/validate_pipeline.py
```

Tests check:
- Data shapes (e.g., ~4,789 clusters, ~180 variables)
- Column names and types
- No NaN in key columns
- Expected file outputs exist

## Key Results (To Be Filled)

*This section will be updated as analysis progresses*

### Phase 1: Data Preparation
- [ ] Clusters: 4,789
- [ ] Environmental variables: 180
- [ ] Missing data pattern: ...
- [ ] Excluded services: GPM_PRECIP (too slow)

### Phase 5: Modeling
- [ ] Top environmental predictors: ...
- [ ] Hierarchical divergence: ...
- [ ] Key confounds identified: ...

## Troubleshooting

**Error: "ModuleNotFoundError: No module named 'analysis_lib'"**
```bash
# Add analysis/ to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or install in development mode
pip install -e .
```

**Error: "FileNotFoundError: config.yaml"**
```bash
# Run from analysis/ directory
cd analysis/
python scripts/phase1_data_prep.py
```

**Database locked or slow queries**
```bash
# Check if data acquisition is still running
ps aux | grep acquire_environmental_data

# If needed, work with snapshot
cp notebooks/pangenome_env_data/pangenome_env.db analysis/data/pangenome_env_snapshot.db
```

## References

- **Analysis plan**: [docs/operations/COMPREHENSIVE_ANALYSIS_PLAN.md](../docs/operations/COMPREHENSIVE_ANALYSIS_PLAN.md)
- **Service documentation**: [docs/SERVICES.md](../docs/SERVICES.md)
- **Database management**: [docs/operations/DATABASE_MANAGEMENT.md](../docs/operations/DATABASE_MANAGEMENT.md)

## Contact

See repository [CONTRIBUTING.md](../CONTRIBUTING.md) for collaboration guidelines.
