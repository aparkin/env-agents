# Comprehensive Analysis Plan: Environmental Predictors of Microbial Distribution

**Goal:** Understand which environmental features determine where specific taxa are found, accounting for confounding relationships among environmental variables (e.g., C/N/pH correlations).

**Critical Clarifications:**
- **NOT abundance data:** Presence/absence only (genomes were isolated/assembled from these locations)
- **NOT a representative sample:** Idiosyncratic collection selected for pangenomics (species representation + genome quality)
- **NOT about spatial per se:** Space is just a proxy for environment; we want environmental determinants
- **Focus:** Interpretable associations between taxa and environments, understanding environmental confounds

**Data Structure:**
- **Genome samples:** 83,227 (GTDB-classified genomes, deduplicated for pangenomics)
- **Spatial clusters:** 4,789 (locations where genomes were isolated/assembled)
- **Environmental observations:** 1.7M+ → 16-20M (climate, soil, vegetation, topography)
- **Taxonomic levels:** Phylum through Species (but biased toward genome-quality representatives)

---

## Key Analytical Decisions (Based on Data Constraints)

### What We Changed from Standard Approaches

1. **Space is environment, not a confounder**
   - ❌ NO spatial autocorrelation "correction"
   - ❌ NO spatial random effects
   - ✅ Geographic diversity = environmental diversity (that's the feature space)

2. **Presence/absence, not abundance**
   - ❌ NO compositional data analysis (CLR, Aitchison distance)
   - ❌ NO community dissimilarity (Bray-Curtis, UniFrac)
   - ✅ Binary classification per taxon: P(taxon present | environment)

3. **Temporal patterns as environmental features**
   - ❌ NO time-series modeling of taxonomic change (only one snapshot)
   - ✅ Climate variability as environmental descriptor (seasonality, interannual variation)

4. **Focus on confounds, not just correlations**
   - ❌ NO simple feature importance ranking
   - ✅ Conditional variable importance: What matters given other correlates?
   - ✅ Partial correlations: Independent effects after controlling for confounds
   - ✅ Variance partitioning: Climate vs soil vs vegetation vs shared

5. **Interpretability over predictive accuracy**
   - Goal: 10-20 key environmental drivers, clearly explained
   - Secondary: Interactions between 2-3 variables (e.g., pH × carbon)
   - De-prioritize: Complex interactions, black-box predictions

---

## Current Data Collection Status (as of analysis start)

### Complete Services (ready for analysis)
- ✅ **NASA_POWER** (4,789/4,789 clusters): Climate/weather (6 vars)
- ✅ **GBIF** (4,789/4,789): Biodiversity observations (3 vars)

### Near-Complete Services
- **SRTM** (4,051/4,789): Elevation (84% complete)
- **WorldClim** (3,596/4,789): Bioclimate variables (19 vars, 75% complete)
- **SoilGrids** (3,557/4,789 each): Texture, pH, organic carbon (74% complete)
- **MODIS_NDVI** (3,674/4,789): Vegetation index (77% complete)
- **MODIS_EVI** (3,120/4,789): Enhanced vegetation (65% complete)
- **MODIS_LANDCOVER** (919/4,789): Land cover types (19% complete)

### Sparse Services (expect limited coverage)
- **TERRA_CLIMATE** (930/4,789): Climate water balance (19% complete, 14 vars)
- **OpenAQ** (847/4,789): Air quality (18% urban coverage expected)
- **Google Embeddings** (429/4,789): Satellite features (64 dims, 9% complete)
- **USGS_NWIS** (20/4,789): Stream gauges (11 vars, US-only, sparse)

**Expected final:** ~16-20M observations across 180+ environmental variables

---

## Phase 1: Data Preparation & Quality Assessment (Week 1-2)

### 1.1 Data Extraction & Pivoting

**Create wide-format matrix:**
```python
# Target structure
rows = clusters (4,789)
columns = {
    taxonomic_composition (phylum-level proportions),
    environmental_features (180+ variables),
    spatial_features (lat, lon, elevation),
    metadata (cluster_size, sample_count)
}
```

**Key Decisions:**
- **Taxonomic response variable:** Multiple strategies
  1. **Phylum-level proportions** (15-20 major phyla) - compositional data
  2. **Binary presence/absence** per phylum - simpler, robust to sampling depth
  3. **Dominant phylum** - categorical outcome
  4. **Diversity indices** - Shannon, Simpson, phylogenetic diversity

- **Temporal aggregation:** For time-series env data (NASA_POWER, MODIS, etc.)
  1. **Annual mean** (2019-2021 window)
  2. **Seasonal summaries** (growing season means, winter minimums)
  3. **Variability** (coefficient of variation, range)

**Script:** `01_extract_and_pivot.py`

### 1.2 Missing Data Assessment

**Characterize missingness:**

```python
import missingno as msno

# Visualize missing data patterns
msno.matrix(df_env)
msno.heatmap(df_env)  # Correlation of missingness
msno.dendrogram(df_env)  # Hierarchical clustering of missingness

# Quantify by service
missing_by_service = df_env.isnull().sum() / len(df_env)

# Identify clusters of missingness
# (e.g., ocean locations missing soil data)
```

**Critical Questions:**
1. **MCAR, MAR, or MNAR?** (Missing Completely At Random, At Random, Not At Random)
   - MNAR example: Soil data missing for aquatic locations (informative!)
   - MAR example: Sensor data missing in remote areas

2. **Service completion patterns:**
   - Which services co-occur? (e.g., WorldClim + SoilGrids both missing in oceans)
   - Are taxonomic groups associated with missingness?

**Missingness strategies:**
- **Mechanical missing** (ocean clusters + soil data) → Reasonable to exclude or impute as "aquatic"
- **Geographic missing** (remote areas) → Consider spatial imputation
- **Sensor missing** (urban air quality) → Multiple imputation or indicator variables

**Script:** `02_missing_data_analysis.py`

### 1.3 Variable Characterization

**Classify each variable:**

| Type | Examples | Analysis Approach |
|------|----------|-------------------|
| **Continuous** | Temperature, precipitation, elevation | Scale, log-transform if skewed |
| **Bounded continuous** | NDVI (0-1), Soil pH (0-14) | Logit transform for proportions |
| **Categorical (ordinal)** | Land cover class (forest→urban) | Ordinal encoding or one-hot |
| **Categorical (nominal)** | Soil texture class | One-hot encoding |
| **Count** | GBIF species observations | Log(n+1) or zero-inflated models |
| **Compositional** | Phylum proportions (sum to 1) | CLR transform (centered log-ratio) |
| **High-dimensional embeddings** | Google 64-dim satellite features | PCA/UMAP before modeling |

**Distributional analysis:**
```python
for var in env_vars:
    # Shapiro-Wilk test for normality
    # QQ-plots
    # Histograms + KDE
    # Outlier detection (IQR, z-score)
```

**Transformation decisions:**
- **Right-skewed** (precip, population) → log(x+1)
- **Bimodal** (e.g., urban vs rural) → Consider clustering or indicator
- **Heavy-tailed** → Winsorize extremes or use robust scaling

**Script:** `03_variable_characterization.py`

---

## Phase 2: Exploratory Data Analysis (Week 2-3)

### 2.1 Environmental Space Structure (Not Geographic Space)

**Goal:** Understand the intrinsic structure of environmental variation - **space is just where we measured environment, not the predictor itself**

**Key Insight:** We're not trying to "control for" or "remove" spatial effects. Geography gave us diverse environments to sample - that's the point. We want to understand environmental gradients regardless of their spatial configuration.

**Analyses:**

1. **Environmental space visualization** (NOT geographic maps)
   ```python
   # PCA of environmental variables
   from sklearn.decomposition import PCA
   pca = PCA(n_components=2)
   env_pca = pca.fit_transform(X_env_scaled)

   # What do PC1 and PC2 represent?
   # PC1: Temperature/aridity gradient?
   # PC2: Soil fertility gradient?

   # Plot clusters in environmental space, colored by dominant phylum
   plt.scatter(env_pca[:, 0], env_pca[:, 1], c=phylum_color)
   # Do phyla occupy distinct regions of environmental space?
   ```

2. **Environmental correlation structure** (the "confounds" you mentioned)
   ```python
   # Which environmental variables co-vary?
   corr_matrix = df_env[soil_vars + climate_vars].corr()

   # Key relationships to understand:
   # - pH vs soil organic carbon (acidic soils often C-rich)
   # - Temperature vs elevation (lapse rate)
   # - Precipitation vs NDVI (water drives productivity)
   # - C:N ratio vs pH (nutrient cycling patterns)

   # These confounds are REAL ecological relationships, not statistical nuisances
   # We want to understand which of these correlated variables matters for taxa
   ```

3. **Environmental variable clustering** (identify redundant measurements)
   ```python
   from scipy.cluster.hierarchy import linkage, dendrogram

   # Hierarchical clustering of variables by correlation
   # Groups: [temp-related], [precip-related], [soil fertility], [vegetation]
   # Within each group, can we pick 1-2 representative variables?
   ```

**No spatial autocorrelation analysis needed** - we're not trying to partition variance into "spatial" vs "environmental". All variance IS environmental (or sampling bias, which we acknowledge).

**Script:** `04_environmental_structure.py`

### 2.2 Temporal Patterns as Environmental Features

**Important:** We don't have time-series of taxonomy (single snapshot per location), so temporal analysis is about **characterizing environments themselves**, not tracking taxonomic change.

**Goal:** Temporal variability as an environmental feature (e.g., "high interannual precip variability" is a different environment than "stable rainfall")

**Analyses:**

1. **Climate variability features** (from NASA_POWER, TerraClimate time series)
   ```python
   # Create derived variables that capture temporal patterns
   df['precip_seasonality'] = df['precip_monthly_std'] / df['precip_annual_mean']
   df['temp_range'] = df['temp_max'] - df['temp_min']
   df['drought_frequency'] = (df['monthly_precip'] < threshold).sum() / n_months

   # These describe environmental STABILITY or VARIABILITY
   # Hypothesis: Stable environments → specialists; variable → generalists?
   ```

2. **Phenology as environment** (from MODIS NDVI time series)
   ```python
   # Growing season characteristics
   df['growing_season_length'] = days_above_ndvi_threshold(ndvi_ts)
   df['green_up_rate'] = slope_of_spring_ndvi_increase(ndvi_ts)
   df['ndvi_amplitude'] = max(ndvi_ts) - min(ndvi_ts)  # Seasonality measure
   ```

3. **Long-term vs short-term aggregates**
   ```python
   # Does 10-year mean temperature predict better than 1-year?
   # Test sensitivity to temporal window
   ```

**Key Insight:** Temporal patterns describe **what kind of environment it is**, not dynamics of the microbial community (which we can't measure).

**Script:** `05_temporal_environmental_features.py`

### 2.3 Correlation Structure

**Goal:** Identify multicollinearity and variable redundancy

**Hierarchical approach:**

1. **Within-service correlation**
   ```python
   # Example: NASA_POWER variables
   climate_vars = ['temperature', 'precipitation', 'humidity', 'solar_rad']
   corr_climate = df_env[climate_vars].corr()

   # High corr (>0.9) → Consider PCA or select one
   ```

2. **Cross-service correlation**
   ```python
   # Full correlation matrix (180+ vars)
   corr_full = df_env.corr()

   # Identify variable clusters
   from scipy.cluster.hierarchy import linkage, dendrogram
   linkage_matrix = linkage(corr_full, method='ward')
   ```

3. **Variance Inflation Factor (VIF)**
   ```python
   from statsmodels.stats.outliers_influence import variance_inflation_factor

   # VIF > 10 indicates severe multicollinearity
   vif = [variance_inflation_factor(X.values, i) for i in range(X.shape[1])]
   ```

**Strategies:**
- **High correlation (>0.9):** Drop one variable or create composite
- **Conceptual redundancy:** Elevation highly correlated with temperature → Keep both but note
- **PCA for variable families:** Google embeddings (64 dims) → 5-10 PCs

**Script:** `06_correlation_analysis.py`

### 2.4 Taxonomic-Environmental Associations (Univariate)

**Screening for signal:**

For each environmental variable, test association with:
1. **Phylum proportions** (Spearman correlation)
2. **Diversity indices** (Shannon, phylogenetic diversity)
3. **Specific phyla presence** (Mann-Whitney U test)

**Example:**
```python
import scipy.stats as stats

for env_var in env_vars:
    for phylum in major_phyla:
        rho, p = stats.spearmanr(df_env[env_var], df_tax[phylum], nan_policy='omit')
        # Bonferroni correction for multiple testing
```

**Goal:** Identify variables with ANY signal before multivariate modeling

**Visualization:**
- Heatmap: Variables × Phyla, color = Spearman ρ
- Scatter: Top associations with LOESS smoothing

**Script:** `07_univariate_screening.py`

---

## Phase 3: Dimensionality Reduction (Week 3-4)

**Challenge:** 180+ environmental variables, many correlated, some sparse

### 3.1 Variable Selection Strategies

**A. Domain-Driven Pre-Selection**
- **Core climate** (5-10 vars): Temperature (mean, range), Precipitation (total, seasonality), Aridity
- **Soil** (5-10 vars): pH, texture, organic carbon, bulk density
- **Vegetation** (3-5 vars): NDVI (mean, variability), Land cover type
- **Topography** (2-3 vars): Elevation, slope, aspect
- **Geographic** (2 vars): Latitude, longitude
- **Diversity** (2-3 vars): Species richness (GBIF), land use heterogeneity

**Total:** ~30-40 "core" variables selected a priori based on microbial ecology theory

**B. Data-Driven Selection**

1. **Variance threshold:** Drop low-variance variables (near-constant)
   ```python
   from sklearn.feature_selection import VarianceThreshold
   selector = VarianceThreshold(threshold=0.01)  # Remove <1% variance
   ```

2. **Mutual information:** Non-linear dependency measure
   ```python
   from sklearn.feature_selection import mutual_info_regression
   mi_scores = mutual_info_regression(X, y)
   # Keep top N by MI score
   ```

3. **Random Forest initial pass:** Get feature importances
   ```python
   from sklearn.ensemble import RandomForestRegressor
   rf = RandomForestRegressor(n_estimators=100, max_depth=10)
   rf.fit(X, y)
   # Keep features with importance > threshold
   ```

### 3.2 Principal Component Analysis (By Domain)

**Apply PCA to variable families:**

1. **Climate PCA** (NASA_POWER + TerraClimate)
   - Likely PC1 = temperature gradient, PC2 = precipitation gradient
   - Keep ~3-5 PCs explaining 90% variance

2. **Satellite PCA** (MODIS NDVI, EVI, LST time series)
   - PC1 = mean productivity, PC2 = seasonality
   - Keep ~3-4 PCs

3. **Google Embeddings PCA** (64 dimensions)
   - Often PC1-10 capture most information
   - Keep ~10 PCs

4. **Soil PCA** (SoilGrids multi-depth profiles)
   - PC1 = overall fertility, PC2 = texture
   - Keep ~3-4 PCs

**Result:** 180 vars → ~30 core + ~20 PCs = 50 composite features

**Script:** `08_dimensionality_reduction.py`

### 3.3 UMAP for Visualization

**Non-linear dimensionality reduction:**
```python
import umap

# Environmental space
umap_env = umap.UMAP(n_neighbors=15, min_dist=0.1, n_components=2)
env_2d = umap_env.fit_transform(X_scaled)

# Color by taxonomic groups
plt.scatter(env_2d[:, 0], env_2d[:, 1], c=phylum_dominance, cmap='tab20')
```

**Goal:** Visualize if taxonomic groups occupy distinct environmental niches

**Script:** `09_umap_visualization.py`

---

## Phase 4: Imputation Strategy (Week 4)

### 4.1 Imputation Methods (By Missingness Type)

**A. Mechanical Missing (Aquatic vs Terrestrial)**
- **Soil variables missing for aquatic sites:** Create "aquatic" indicator, impute soil vars with placeholder or separate model

**B. Geographic Missing (Random sampling gaps)**
- **Spatial interpolation:** Kriging, IDW for spatially autocorrelated variables
- **Nearest-neighbor:** For sparse data (USGS gauges, OpenAQ sensors)

**C. Sparse Coverage (Optional services)**
- **Multiple imputation (MICE):**
  ```python
  from sklearn.experimental import enable_iterative_imputer
  from sklearn.impute import IterativeImputer

  imputer = IterativeImputer(max_iter=10, random_state=42)
  X_imputed = imputer.fit_transform(X)
  ```

- **Indicator variables:** Add "X_missing" binary flag to preserve missingness information

**D. High-Dimensional (Google embeddings)**
- **Model-based imputation:** Train autoencoder on observed embeddings, predict missing

**Strategy Recommendation:**
1. **Primary analysis:** Complete-case analysis on variables with >70% coverage (~30-40 core vars)
2. **Sensitivity analysis:** Compare results with imputed data

**Script:** `10_imputation.py`

---

## Phase 5: Modeling Framework (Week 5-7)

### 5.1 Response Variable Formulations

**Critical:** We have **presence/absence only** (not abundance). Genomes were sampled opportunistically for quality, NOT proportional to abundance. This rules out compositional/abundance-based analyses.

**Viable formulations:**

1. **Taxon-Specific Presence/Absence** (RECOMMENDED)
   - Response: Binary (present/absent) for each taxon of interest
   - Build separate model per taxon: P(taxon present | environment)
   - Advantage:
     - Interpretable as environmental niche/tolerance
     - Phylum, class, order, or genus-level
     - Directly addresses: "Where do we find Acidobacteria?"
   - Models: 15-20 binary classifiers (one per major phylum)

2. **Taxonomic Richness** (Secondary)
   - Response: Number of distinct phyla/families present per cluster
   - Advantage: Single metric of "environmental generalism"
   - Challenge: Confounded by sampling effort (more genomes → more taxa)
   - Use IF genome counts are similar across clusters

3. **Taxonomic Evenness** (Exploratory)
   - Response: Shannon evenness of phyla (accounting for unequal genome counts)
   - Question: Are "even" communities in different environments than "uneven"?

**Do NOT use:**
- ❌ Compositional data analysis (no abundance)
- ❌ Dominant taxon (artificial - depends on sampling)
- ❌ Community dissimilarity metrics (not meaningful without abundance)

**Primary Strategy:** Binary models per major taxon
- "What environments predict Acidobacteria presence?"
- "What environments predict Actinomycetota presence?"
- Compare niches across taxa to find environmental axes of differentiation

### 5.2 CatBoost Gradient-Boosted Decision Tree (GBDT)

**Why CatBoost:**
- ✅ Handles mixed data types (continuous, categorical, ordinal) natively
- ✅ Built-in categorical encoding (no need for one-hot)
- ✅ Robust to missing values (treats as separate category)
- ✅ Feature importance metrics (split-based, gain-based, SHAP)
- ✅ Handles non-linear interactions automatically
- ✅ Less prone to overfitting than XGBoost (ordered boosting)
- ✅ Fast GPU training

**Model Configuration:**
```python
from catboost import CatBoostClassifier, CatBoostRegressor, Pool

# For binary/multiclass
model = CatBoostClassifier(
    iterations=1000,
    learning_rate=0.05,
    depth=6,  # Shallow trees reduce overfitting
    l2_leaf_reg=3,  # L2 regularization
    border_count=128,  # For continuous vars
    cat_features=[list_of_categorical_indices],
    early_stopping_rounds=50,
    verbose=100,
    task_type='GPU',
    loss_function='MultiClass' or 'Logloss'
)

# Categorical features
cat_features = ['land_cover_class', 'soil_texture', 'koppen_climate_zone']
```

### 5.3 Cross-Validation Strategy

**Revised perspective:** Since space is a proxy for environment (not a confounder), we can use simpler CV strategies.

**Option A: Stratified K-Fold** (Standard approach)
```python
from sklearn.model_selection import StratifiedKFold

# Ensure each fold has similar class balance
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
for train_idx, test_idx in skf.split(X, y):
    # Standard cross-validation
```

**Option B: Environmental Stratification** (If you want to test generalization)
```python
# Stratify by environmental type, not geography
# E.g., divide into climate zones or biome types
df_clusters['env_stratum'] = assign_environmental_stratum(df_clusters)
# Options: Köppen climate zones, biome categories, soil type categories

# Then use stratified CV by env_stratum
# Tests: Can we predict Acidobacteria in tropical forests if trained on temperate?
```

**Option C: Leave-One-Out for sparse taxa** (If taxon very rare)
```python
# For taxa present in <100 clusters, regular CV may fail
# Use LOOCV or repeated stratified CV with small test sets
```

**Recommendation:** Start with Option A (standard stratified K-fold). Only use environmental stratification if you specifically want to test niche extrapolation.

**Nested CV for hyperparameter tuning:**
- Outer loop: 5-fold stratified CV (performance estimation)
- Inner loop: 3-fold CV (hyperparameter selection)

### 5.4 Handling Environmental Confounds (Critical!)

**Your key concern:** "understand the specific 'confounding' relationships among environmental features like carbon, nitrogen, and pH"

**Approach: Conditional Variable Importance** (not just raw importance)

**Goal:** Distinguish true predictors from correlated bystanders

**Example scenario:**
- Acidobacteria correlate with low pH
- Low pH soils tend to be high in organic carbon
- **Question:** Does pH matter? Or organic carbon? Or both?

**Method 1: Partial Correlation Analysis**
```python
from pingouin import partial_corr

# Does Acidobacteria-pH association hold after controlling for carbon?
partial_corr(data=df, x='acidobacteria_presence', y='soil_pH', covar='soil_carbon')

# If still significant → pH has independent effect
# If not → pH association is confounded by carbon
```

**Method 2: Conditional Permutation Importance** (CPI)
```python
# Standard importance: Permute variable X, measure drop in performance
# Conditional importance: Permute X CONDITIONAL on correlated vars

from sklearn.inspection import permutation_importance

# Importance of pH given that carbon is already in model
model_with_carbon = CatBoost().fit(X[['carbon', 'other_vars']], y)
importance_pH_conditional = permutation_importance(
    model_with_carbon, X[['pH', 'carbon', 'other_vars']], y
)

# Low conditional importance → pH is redundant with carbon
# High conditional importance → pH adds unique information
```

**Method 3: Hierarchical Feature Addition**
```python
# Test variables in groups
models = []

# Model 1: Climate only
models.append(fit(X[climate_vars], y))

# Model 2: Climate + Soil chemistry
models.append(fit(X[climate_vars + soil_chem_vars], y))

# Model 3: Climate + Soil chemistry + Vegetation
models.append(fit(X[climate_vars + soil_chem_vars + veg_vars], y))

# Compare AUC: How much does each variable group add?
# Identifies which domains matter most
```

**Method 4: Variance Partitioning**
```python
# Inspired by community ecology (variation partitioning)
# Fraction of variance explained by:
# - Climate alone
# - Soil alone
# - Shared between climate & soil
# - Unexplained

# Use R² or deviance explained to quantify
```

**Result:** For each taxon, report:
1. **Primary predictors:** Variables with high conditional importance
2. **Confounded predictors:** Variables that matter but only in absence of primary
3. **Interaction effects:** Variables that matter only in combination

**Script:** `11b_conditional_importance.py`

### 5.5 Feature Selection via Iterative Elimination

**After understanding confounds, select parsimonious model:**

```python
from sklearn.feature_selection import RFECV

# Strategy: RFECV with permutation importance
selector = RFECV(
    estimator=CatBoostClassifier(**params),
    step=3,  # Remove 3 features per iteration
    cv=5,
    scoring='roc_auc',
    importance_getter='auto'  # Use model's feature importance
)
selector.fit(X, y)
optimal_features = X.columns[selector.support_]

# But ALSO check conditional importance of selected features
# Ensure we're not keeping redundant correlated variables
```

**Principle:** Prefer one representative from correlated clusters (e.g., pH over carbon if conditionally more important) rather than keeping both

### 5.5 Interaction Detection

**SHAP (SHapley Additive exPlanations) for interactions:**

```python
import shap

explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)

# Main effects
shap.summary_plot(shap_values, X_test, plot_type="bar")

# Interaction detection
shap.dependence_plot("temperature", shap_values, X_test, interaction_index="precipitation")

# Top 2-way interactions
shap_interaction_values = explainer.shap_interaction_values(X_test)
# Identify strongest interactions by H-statistic
```

**H-statistic (Friedman's interaction strength):**
```python
from sklearn.inspection import partial_dependence

# Test specific interactions
for feat1, feat2 in candidate_pairs:
    h_stat = friedman_h_statistic(model, X, [feat1, feat2])
    # High H-stat → strong interaction
```

**Engineering interaction features (if warranted):**
```python
# Example: Aridity index (function of temp and precip)
X['aridity_index'] = X['precipitation'] / X['evapotranspiration']

# Climate-soil interaction
X['temp_x_soil_pH'] = X['temperature'] * X['soil_pH']
```

### 5.6 Model Interpretation

**Global interpretation:**

1. **Feature importance ranking** (bar plot)
2. **SHAP summary plot** (beeswarm plot showing distribution of effects)
3. **Partial dependence plots** (marginal effect of each feature)

**Local interpretation (specific predictions):**

```python
# SHAP waterfall plot for individual cluster
shap.waterfall_plot(shap.Explanation(shap_values[i], base_values[i], X_test.iloc[i], feature_names))
```

**Biological interpretation:**

- **Temperature gradient:** Thermophiles vs mesophiles
- **pH gradient:** Acidophiles vs alkaliphiles
- **Moisture:** Aquatic vs terrestrial vs arid
- **Nutrient availability:** Oligotrophs vs copiotrophs

**Script:** `11_catboost_modeling.py`

---

## Phase 6: Model Validation & Sensitivity (Week 7-8)

### 6.1 Performance Metrics

**For each phylum (binary classification):**
- **ROC-AUC:** Overall discriminatory power
- **Precision-Recall AUC:** Better for imbalanced classes
- **F1-score:** Balance of precision and recall
- **Calibration:** Brier score, calibration plots

**For diversity (regression):**
- **R²:** Variance explained
- **RMSE:** Prediction error
- **MAE:** Mean absolute error (more robust to outliers)

**For dominant phylum (multiclass):**
- **Macro F1:** Average across classes
- **Cohen's kappa:** Agreement adjusted for chance
- **Confusion matrix:** Where are misclassifications?

### 6.2 Spatial Validation

**Test generalization across geography:**

```python
# Hold out entire biogeographic regions
regions = ['North_America', 'Europe', 'Asia', 'South_America', 'Africa', 'Oceania']

for region in regions:
    train = df[df['region'] != region]
    test = df[df['region'] == region]
    model.fit(train[X_cols], train[y_col])
    score = model.score(test[X_cols], test[y_col])
    print(f"{region}: {score:.3f}")
```

**Question:** Does model transfer across continents? Or is it overfit to specific regions?

### 6.3 Sensitivity Analyses

**Test robustness to:**

1. **Imputation method:** Compare complete-case vs MICE vs spatial interpolation
2. **Taxonomic resolution:** Phylum vs Class vs Order
3. **Environmental variable selection:** Core 30 vars vs full 180 vars vs PCA features
4. **Modeling algorithm:** CatBoost vs Random Forest vs XGBoost vs GLM (baseline)
5. **Train/test split:** Random vs spatial block vs temporal (if dates available)

### 6.4 Null Model Comparisons

**Baselines to beat:**

1. **Geography-only:** Lat/lon/elevation only (tests if environment adds info beyond biogeography)
2. **Climate-only:** Temperature + precipitation only (classic biogeographic predictors)
3. **Random:** Permuted labels (sanity check)
4. **Null diversity:** Constant prediction (mean diversity)

**Script:** `12_model_validation.py`

---

## Phase 7: Hypothesis Testing & Biological Interpretation (Week 8-9)

### 7.1 Key Ecological Hypotheses

**Test specific predictions:**

1. **Temperature-diversity:** Does Shannon diversity peak at mid-latitudes? (Latitudinal diversity gradient)
2. **Soil pH:** Are Acidobacteria enriched in low-pH soils?
3. **Aridity:** Do Actinobacteria dominate arid environments?
4. **Nutrient gradients:** Oligotrophic vs copiotrophic strategies
5. **Land use:** Does urbanization reduce diversity?

**Statistical tests:**
```python
# Example: pH and Acidobacteria
low_pH = df[df['soil_pH'] < 5.5]
high_pH = df[df['soil_pH'] > 6.5]

from scipy.stats import mannwhitneyu
stat, p = mannwhitneyu(low_pH['acidobacteria_prop'], high_pH['acidobacteria_prop'])
```

### 7.2 Identifying Key Environmental Thresholds

**Segmented regression / breakpoint detection:**

```python
import pwlf  # piecewise linear fit

# Does diversity-temperature relationship have a breakpoint?
model = pwlf.PiecewiseLinFit(df['temperature'], df['diversity'])
breaks = model.fit(n_segments=2)  # Find optimal breakpoint
```

**Classification trees (interpretable rules):**
```python
from sklearn.tree import DecisionTreeClassifier, export_text

# Simple tree for interpretation (not prediction)
tree = DecisionTreeClassifier(max_depth=3)
tree.fit(X, y)
rules = export_text(tree, feature_names=X.columns)
# Example: "If soil_pH < 5.2 AND temp > 15°C → Acidobacteria"
```

### 7.3 Comparison to Literature

**Benchmark against known relationships:**

- **Temperature-metabolism:** Q10 rule (metabolic rate doubles per 10°C)
- **Rapoport's rule:** Diversity peaks at equator
- **pH optima:** Known phylum preferences

**Novelty identification:** Which associations are unexpected? Worthy of follow-up?

**Script:** `13_hypothesis_testing.py`

---

## Phase 8: Reporting & Visualization (Week 9-10)

### 8.1 Key Figures

1. **Figure 1: Data overview**
   - Map: Sampling locations colored by dominant phylum
   - Bar: Taxonomic composition (phylum-level)
   - Heatmap: Environmental data completeness by service

2. **Figure 2: Environmental gradients**
   - UMAP: Clusters in environmental space, colored by taxonomy
   - PCA biplots: Top environmental PCs with taxonomic loadings

3. **Figure 3: Univariate associations**
   - Heatmap: Spearman correlation (phyla × env vars), hierarchically clustered
   - Scatter grid: Top 6 associations with LOESS smoothing

4. **Figure 4: Model performance**
   - ROC curves: Per-phylum binary classification
   - Confusion matrix: Dominant phylum multiclass
   - R² plot: Observed vs predicted diversity

5. **Figure 5: Feature importance**
   - Bar: Top 20 features by permutation importance
   - SHAP summary: Beeswarm plot showing effect distributions

6. **Figure 6: Key interactions**
   - 2D heatmaps: Top 3 pairwise interactions (e.g., temp × precipitation)
   - Partial dependence: How diversity changes across gradients

7. **Figure 7: Biological interpretation**
   - Niche plots: Environmental optima for each phylum (violin plots)
   - Decision tree: Interpretable rules for phylum prediction

8. **Figure 8: Spatial predictions**
   - Map: Predicted vs observed diversity
   - Residual map: Where does model fail? (spatial structure in errors?)

### 8.2 Tables

1. **Table 1:** Summary statistics (samples, clusters, env observations by service)
2. **Table 2:** Model comparison (CatBoost vs alternatives, with CV scores)
3. **Table 3:** Top 20 features ranked by importance with interpretation
4. **Table 4:** Phylum-specific environmental preferences (mean ± SD for top 5 predictors)

### 8.3 Supplementary Materials

- **Supp Data 1:** Full feature importance table (all variables)
- **Supp Data 2:** SHAP values per cluster (for reproducibility)
- **Supp Fig 1:** All univariate associations (full heatmap)
- **Supp Fig 2:** Model calibration plots
- **Supp Fig 3:** Sensitivity analyses results

**Script:** `14_generate_figures.py`

---

## Alternative/Complementary Approaches

### Beyond CatBoost GBDT

**If CatBoost underperforms or for comparison:**

1. **Random Forest** (simpler, more interpretable)
   - Pros: Less tuning, feature importance built-in
   - Cons: Less accurate than boosting usually

2. **Elastic Net GLM** (interpretable linear model)
   - Pros: Coefficient interpretability, handles multicollinearity
   - Cons: Assumes linearity, needs interaction terms explicitly

3. **Neural Network** (deep learning)
   - Pros: Can learn complex interactions
   - Cons: Black box, requires more data, overfits easily

4. **Bayesian Hierarchical Model** (for uncertainty quantification)
   - Pros: Principled uncertainty, handles spatial structure elegantly
   - Cons: Slow, requires careful priors

5. **Distance-Based (CCA, db-RDA)**
   - Pros: Designed for community ecology, multivariate response
   - Cons: Linear assumptions, harder to get feature importance

### For Interactions Specifically

**If SHAP interactions are insufficient:**

1. **Model-X Knockoffs** (for controlled variable selection with FDR)
2. **Friedman's H-statistic** (quantifies interaction strength)
3. **RuleFit** (combines trees and linear models to extract rules)

---

## Software & Tools

### Core Libraries

```python
# Data manipulation
import pandas as pd
import numpy as np

# Spatial analysis
import geopandas as gpd
from esda.moran import Moran
from libpysal.weights import KNN
import pysal

# Machine learning
from catboost import CatBoostClassifier, CatBoostRegressor, Pool
from sklearn.model_selection import cross_val_score, GroupKFold
from sklearn.inspection import permutation_importance, partial_dependence
from sklearn.feature_selection import RFECV

# Interpretation
import shap
import matplotlib.pyplot as plt
import seaborn as sns

# Imputation
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer

# Dimensionality reduction
from sklearn.decomposition import PCA
import umap

# Missing data
import missingno as msno

# Statistical tests
from scipy import stats
from statsmodels.stats.multitest import multipletests  # Bonferroni correction
```

### Recommended Computing Environment

- **RAM:** 32GB+ (for full dataset in memory)
- **GPU:** NVIDIA GPU for CatBoost GPU training (optional but 10x faster)
- **Storage:** 50GB for intermediate files

---

## Timeline Summary

| Phase | Duration | Key Deliverable |
|-------|----------|-----------------|
| 1. Data Prep & QA | 2 weeks | Clean wide-format matrix |
| 2. EDA | 1-2 weeks | Summary statistics, correlation structure |
| 3. Dimensionality Reduction | 1 week | 50 composite features |
| 4. Imputation | 1 week | Complete dataset with sensitivity checks |
| 5. Modeling | 2-3 weeks | Trained CatBoost models with feature selection |
| 6. Validation | 1-2 weeks | Cross-validated performance metrics |
| 7. Interpretation | 1-2 weeks | Biological insights from SHAP/PDP |
| 8. Reporting | 1-2 weeks | Manuscript-ready figures and tables |

**Total:** 10-15 weeks (2.5-4 months)

---

## Critical Success Factors

1. **Handle spatial autocorrelation:** Use spatial block CV, not random splits
2. **Account for missingness:** Understand MCAR vs MAR vs MNAR patterns
3. **Control multicollinearity:** VIF < 10, consider PCA for correlated groups
4. **Validate across space:** Test generalization to held-out geographic regions
5. **Interpret cautiously:** Correlation ≠ causation, unmeasured confounders possible
6. **Biological plausibility:** Do results align with microbial ecology theory?

---

## Next Steps

1. **Review and refine plan** based on complete data collection
2. **Begin Phase 1:** Extract and pivot database to wide-format matrix
3. **Set up analysis repository** with reproducible scripts
4. **Document decisions** (e.g., imputation choices, variable transformations) in analysis log

---

**Questions to resolve before starting:**

1. **Taxonomic resolution:** Focus on phylum-level or drill down to genus?
2. **Imputation philosophy:** Conservative (complete-case) or aggressive (MICE)?
3. **Response variable:** Prioritize diversity indices or compositional data?
4. **Computational resources:** GPU access for CatBoost training?
5. **Timeline constraints:** Need preliminary results by specific date?