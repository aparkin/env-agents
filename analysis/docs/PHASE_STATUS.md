# Analysis Phase Status

**Last updated**: 2025-10-01

This document tracks detailed progress through the 8-phase analysis pipeline.

---

## Phase 1: Data Preparation & Quality Assessment ⏳ NOT STARTED

**Goal**: Extract environmental and taxonomic data, create analysis-ready matrices

**Status**: Ready to begin

### Tasks

- [ ] **1.1 Extract and Pivot Data** (`01a_extract_pivot.ipynb`)
  - Extract environmental observations from database
  - Pivot to wide format (clusters × variables)
  - Load taxonomy and create presence/absence matrices
  - Merge environmental and taxonomic data

- [ ] **1.2 Missing Data Assessment** (`01b_missing_data.ipynb`)
  - Characterize missingness patterns (MCAR vs MAR vs MNAR)
  - Identify variable and cluster completeness
  - Analyze correlation of missingness
  - Determine imputation strategy

- [ ] **1.3 Variable Characterization** (`01c_variable_characterization.ipynb`)
  - Classify variable types (continuous, categorical, compositional)
  - Analyze distributions (normality, skewness, outliers)
  - Determine transformations needed
  - Identify redundant measurements

### Expected Outputs

- `data/phase1_outputs/df_wide.parquet` - Wide-format matrix (~4,789 × 180)
- `data/phase1_outputs/df_taxonomy.parquet` - Taxonomy per cluster
- `data/phase1_outputs/df_phylum_pa.parquet` - Phylum presence/absence
- `data/phase1_outputs/missing_report.json` - Missing data characterization
- `data/phase1_outputs/variable_stats.csv` - Variable statistics and transformations

### Key Decisions Needed

- [ ] Services to include/exclude
- [ ] Temporal aggregation strategy (mean, std, seasonality)
- [ ] Missing data thresholds (variable >70%, cluster >50%?)
- [ ] Exclude GPM_PRECIP? (too slow)

---

## Phase 2: Exploratory Data Analysis ⏳ PENDING

**Goal**: Understand environmental space structure and taxonomic-environmental associations

**Status**: Waiting for Phase 1

### Tasks

- [ ] **2.1 Environmental Space Structure** (`02a_environmental_structure.ipynb`)
  - PCA of environmental variables
  - Identify environmental gradients
  - Visualize clusters in environmental space (NOT geographic)

- [ ] **2.2 Temporal Patterns** (`02b_temporal_features.ipynb`)
  - Create temporal variability features (seasonality, interannual variation)
  - Phenology from MODIS time series
  - Climate stability metrics

- [ ] **2.3 Correlation Analysis** (`02c_correlation_analysis.ipynb`)
  - Full correlation matrix
  - Identify confounds (pH/C/N, temp/elevation, precip/NDVI)
  - Variable clustering (hierarchical)
  - Calculate VIF for multicollinearity

- [ ] **2.4 Univariate Screening** (`02d_univariate_screening.ipynb`)
  - Test associations: environmental var × taxon
  - Spearman correlations with Bonferroni correction
  - Identify variables with signal

### Expected Outputs

- `data/phase2_outputs/correlation_matrix.parquet`
- `data/phase2_outputs/pca_results.parquet`
- `data/phase2_outputs/univariate_tests.csv`
- `results/figures/fig2_environmental_gradients.pdf`

---

## Phase 3: Dimensionality Reduction ⏳ PENDING

**Goal**: Reduce 180 variables to ~50 composite features

**Status**: Waiting for Phase 2

### Tasks

- [ ] **3.1 Domain-Driven Selection** (`03a_core_variables.ipynb`)
  - Select ~30-40 core variables based on domain knowledge
  - Climate, soil, vegetation, topography representatives

- [ ] **3.2 PCA by Domain** (`03b_pca_by_domain.ipynb`)
  - Climate PCA (NASA_POWER, WorldClim, TerraClimate)
  - Soil PCA (SoilGrids)
  - Vegetation PCA (MODIS)
  - Google embeddings PCA

- [ ] **3.3 Feature Selection** (`03c_feature_selection.ipynb`)
  - Variance threshold
  - Mutual information
  - Random Forest initial pass

### Expected Outputs

- `data/phase3_outputs/pca_by_domain.parquet`
- `data/phase3_outputs/selected_features.parquet` (~50 features)
- `data/phase3_outputs/feature_selection_report.json`

---

## Phase 4: Imputation Strategy ⏳ PENDING

**Goal**: Handle missing data

**Status**: Waiting for Phase 3

### Tasks

- [ ] **4.1 Imputation** (`04a_imputation.ipynb`)
  - Complete-case analysis (primary)
  - MICE imputation (sensitivity)
  - Spatial interpolation for spatially autocorrelated vars
  - Create missing indicators

### Expected Outputs

- `data/phase4_outputs/df_imputed.parquet`
- `data/phase4_outputs/df_complete_case.parquet`
- `data/phase4_outputs/imputation_report.json`

---

## Phase 5: Modeling Framework ⏳ PENDING

**Goal**: Build predictive models and analyze hierarchical divergence

**Status**: Waiting for Phase 4

### Tasks

- [ ] **5.1 Baseline Models** (`05a_baseline_models.ipynb`)
  - Train CatBoost models per taxon (15-20 phyla)
  - Feature importance ranking
  - Cross-validation

- [ ] **5.2 Conditional Importance** (`05b_conditional_importance.ipynb`)
  - Partial correlations (pH vs C, temp vs elevation)
  - Conditional permutation importance
  - Hierarchical feature addition
  - Variance partitioning (climate vs soil vs vegetation)

- [ ] **5.3 Hierarchical Divergence** (`05c_hierarchical_divergence.ipynb`) ⭐ KEY
  - Compare environmental models of sibling taxa
  - Identify where in tree niches diverge (phylum/class/order)
  - Statistical testing (permutation tests)
  - Create environmental differentiation tree

### Expected Outputs

- `results/models/*.cbm` - Trained CatBoost models
- `data/phase5_outputs/feature_importances.csv`
- `data/phase5_outputs/conditional_importance.csv`
- `data/phase5_outputs/divergence_results.json`
- `results/tables/table5_taxonomic_divergence.csv`

---

## Phase 6: Validation & Sensitivity ⏳ PENDING

**Goal**: Validate models and test robustness

**Status**: Waiting for Phase 5

### Tasks

- [ ] **6.1 Cross-Validation** (`06a_cross_validation.ipynb`)
  - Stratified K-fold CV
  - Performance metrics (ROC-AUC, PR-AUC, F1)

- [ ] **6.2 Spatial Validation** (`06b_spatial_validation.ipynb`)
  - Hold-out by biogeographic region
  - Test generalization across continents

- [ ] **6.3 Sensitivity Analyses** (`06c_sensitivity.ipynb`)
  - Imputation method
  - Taxonomic resolution
  - Variable selection strategy
  - Model algorithm

### Expected Outputs

- `data/phase6_outputs/validation_scores.csv`
- `data/phase6_outputs/sensitivity_results.json`

---

## Phase 7: Interpretation ⏳ PENDING

**Goal**: Biological interpretation and hypothesis testing

**Status**: Waiting for Phase 6

### Tasks

- [ ] **7.1 SHAP Analysis** (`07a_shap_interpretation.ipynb`)
  - SHAP values for all models
  - Interaction detection
  - Partial dependence plots

- [ ] **7.2 Hypothesis Testing** (`07b_hypothesis_tests.ipynb`)
  - pH vs Acidobacteria
  - Aridity vs Actinomycetota
  - Temperature-diversity relationships

### Expected Outputs

- `data/phase7_outputs/shap_values.parquet`
- `data/phase7_outputs/hypothesis_tests.csv`

---

## Phase 8: Reporting & Visualization ⏳ PENDING

**Goal**: Create publication-ready figures and tables

**Status**: Waiting for Phase 7

### Tasks

- [ ] **8.1 Main Figures** (`08a_main_figures.ipynb`)
  - Fig 1: Data overview
  - Fig 2: Environmental gradients
  - Fig 3: Univariate associations
  - Fig 4: Model performance
  - Fig 5: Feature importance
  - Fig 6: Interactions
  - Fig 7: Hierarchical divergence ⭐
  - Fig 8: Biological interpretation
  - Fig 9: Spatial predictions

- [ ] **8.2 Tables** (`08b_tables.ipynb`)
  - Table 1: Summary statistics
  - Table 2: Model comparison
  - Table 3: Feature importance
  - Table 4: Environmental preferences
  - Table 5: Taxonomic divergence ⭐

### Expected Outputs

- `results/figures/*.pdf` - All main figures
- `results/tables/*.csv` - All tables
- `results/supplementary/` - Supplementary materials

---

## Current Status Summary

| Phase | Status | Progress |
|-------|--------|----------|
| 1. Data Prep | ⏳ Not Started | 0% |
| 2. EDA | ⏳ Pending | 0% |
| 3. Dimensionality | ⏳ Pending | 0% |
| 4. Imputation | ⏳ Pending | 0% |
| 5. Modeling | ⏳ Pending | 0% |
| 6. Validation | ⏳ Pending | 0% |
| 7. Interpretation | ⏳ Pending | 0% |
| 8. Reporting | ⏳ Pending | 0% |

**Overall Progress**: 0%

---

## Next Actions

1. ✅ Set up analysis infrastructure (COMPLETE)
2. ⏭️ Run Phase 1a: Extract and pivot data
3. ⏭️ Run Phase 1b: Missing data analysis
4. ⏭️ Decide on GPM_PRECIP inclusion (recommend exclude)

---

## Notes

- GPM_PRECIP is very slow (>10min per cluster). Recommend excluding and using NASA_POWER precipitation instead.
- Data collection still running (~812/4,789 clusters complete as of 2025-10-01)
- May want to begin analysis on complete clusters while acquisition continues
