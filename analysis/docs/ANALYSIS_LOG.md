# Analysis Decision Log

**Purpose**: Document key decisions, rationale, and alternatives considered throughout the analysis.

**Format**: Reverse chronological (newest first)

---

## 2025-10-01: Analysis Infrastructure Created

**Decision**: Create dedicated `analysis/` directory with modular structure

**Rationale**:
- Separate analysis code from data acquisition framework
- Enable incremental development with checkpoints
- Facilitate collaboration through clear structure
- Support reproducibility with configuration management

**Structure**:
- `notebooks/` - Phase-by-phase interactive exploration
- `scripts/` - Production pipelines
- `analysis_lib/` - Reusable functions
- `data/` - Intermediate checkpoints (gitignored)
- `results/` - Publication-ready outputs

**Alternatives considered**:
- Single monolithic notebook (rejected - hard to maintain, share)
- Scripts only (rejected - less exploratory, harder for collaborators)

**Implementation**:
- Configuration via `config.yaml` (single source of truth)
- Checkpoint system (Parquet files) for expensive computations
- Test suite for validation

---

## 2025-10-01: GPM_PRECIP Service Exclusion

**Decision**: Exclude GPM_PRECIP from analysis

**Rationale**:
- Extremely slow (>10 minutes per cluster vs ~5 seconds for others)
- Blocks progress on data acquisition
- NASA_POWER provides adequate precipitation data
- Cost-benefit: high-resolution precip not critical for initial analysis

**Impact**:
- Lose high temporal resolution precipitation
- NASA_POWER daily precipitation sufficient for analysis

**Alternative considered**:
- Wait for GPM acquisition to complete (rejected - indefinite delay)
- Parallel acquisition with timeout (rejected - still blocks pipeline)

**Configuration**:
```yaml
services:
  exclude:
    - GPM_PRECIP
```

---

## Future Decisions to Document

### Phase 1: Data Preparation

- [ ] **Temporal aggregation strategy**
  - Mean, std, min, max, or all?
  - Window: annual, seasonal, growing season?

- [ ] **Missing data thresholds**
  - Variable completeness: 70%? 50%?
  - Cluster completeness: 50%?

- [ ] **Variable transformations**
  - Log-transform skewed variables?
  - Logit-transform bounded proportions?

### Phase 2: EDA

- [ ] **Correlation threshold for redundancy**
  - Drop if |r| > 0.9?
  - Or keep and address in modeling?

- [ ] **Univariate screening alpha**
  - Bonferroni correction level?
  - Or FDR correction?

### Phase 3: Dimensionality Reduction

- [ ] **PCA variance explained threshold**
  - 90%? 95%?
  - Trade-off: interpretability vs information

- [ ] **Core variable selection**
  - Domain-driven only?
  - Or hybrid with data-driven?

### Phase 4: Imputation

- [ ] **Primary imputation strategy**
  - Complete-case (conservative)?
  - MICE (aggressive)?
  - Spatial interpolation?

- [ ] **Handling mechanically missing data**
  - Soil variables for aquatic sites?
  - Create "aquatic" indicator?

### Phase 5: Modeling

- [ ] **Taxonomic resolution**
  - Focus on phylum level?
  - Drill down to class/order where divergence found?

- [ ] **Feature selection method**
  - RFECV (slow but optimal)?
  - Or importance threshold (fast)?

- [ ] **Handling class imbalance**
  - Class weights?
  - Oversampling/undersampling?
  - Leave as-is (CatBoost handles well)?

### Phase 6: Validation

- [ ] **Cross-validation strategy**
  - Stratified K-fold (standard)?
  - Or environmental stratification?

- [ ] **Spatial validation regions**
  - By continent?
  - By climate zone?
  - By biome?

### Phase 7: Interpretation

- [ ] **SHAP computation**
  - Full dataset?
  - Or subsample (faster)?

- [ ] **Hypothesis testing approach**
  - Pre-registered hypotheses only?
  - Or exploratory with correction?

---

## Template for New Entries

```
## YYYY-MM-DD: Decision Title

**Decision**: [What was decided]

**Rationale**:
- [Why this was chosen]
- [Key considerations]

**Alternatives considered**:
- [Option 1] (rejected - reason)
- [Option 2] (rejected - reason)

**Impact**:
- [Effect on results]
- [Effect on interpretation]

**Configuration/Code**:
[Relevant config or code snippet]
```

---

## References

- **Analysis plan**: [../docs/operations/COMPREHENSIVE_ANALYSIS_PLAN.md](../../docs/operations/COMPREHENSIVE_ANALYSIS_PLAN.md)
- **Phase status**: [PHASE_STATUS.md](PHASE_STATUS.md)
