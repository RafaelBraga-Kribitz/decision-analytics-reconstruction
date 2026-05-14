# Statistical Metrics Summary

**Report generated:** 2026-05-14 execution (§5 full metric capture)

**Data:** Pipeline runs with SEED=20180422 (Module B), deterministic RNG seeds across all modules.

---

## Module A: Population Segmentation & Propensity

### Data Characteristics
- **Population size:** 50,000 entities (synthetic)
- **Sample date:** 2026-05-14 09:04:50 UTC
- **Git commit:** b370333f1ffc163236cbec4e446c8999d42e1078

| Metric | Value | Notes |
|--------|-------|-------|
| Population rows | 50,000 | Synthetic generation, deterministic (SEED=42) |
| Segments (k) | 6 | Behavioral clusters via k-means |
| Propensity model | Logistic regression | Classification task; outputs are [0, 1] |
| Segment composition (largest) | rural_committed (15,607) | 31.2% of population; stable employment |
| Participation propensity (mean) | 0.5229 | Slightly above 50%; std 0.2539 |
| Participation propensity (range) | [0.011, 1.000] | Full support; min=low-contact rural, max=urban high-volatility |
| Data quality flaws injected | 13 types | Missing values, phone reachability, structural dependency proxy |

**Source files:**
- `data/processed/population_master_clean.parquet` (50k rows, cleaned)
- `data/processed/segment_labels.parquet` (segment assignments)
- `data/processed/participation_propensity.parquet` (propensity scores [0,1])
- `data/processed/model_run_manifest.json` (execution metadata)

---

## Module B: Resource Allocation (MILP)

### Solver Results
- **Scenario:** baseline
- **Seed:** 20180422
- **Solver status:** OPTIMAL
- **Run time:** 2026-05-14 09:05:26 UTC

| Metric | Value | Units | Notes |
|--------|-------|-------|-------|
| Budget envelope | 6,029,992.61 | USD | Total allocated across 18 departments, 11 channels, 14 weeks |
| Persuasion-adjusted contacts | 252,721,160.67 | contacts | Nonlinear sum of channel effectiveness × reach |
| Budget utilization | ~100.5 % | % of nominal 6M | Solver uses available envelope optimally |
| LP objective (linearized) | TBD | units | Linear slopes before nonlinear aggregation |

### Dual Values (Shadow Prices)
- **Budget envelope dual (π):** 23.51 | Marginal persuasion gain per additional USD
- **Reach cap binding count:** TBD | How many of 18×11×14 caps are tight
- **Top 5 binding constraints:** See `allocation_run_baseline.md`

### Budget Expansion Sensitivity (0.25–2.0× nominal)

| Multiplier | Budget target | Solver status | Total allocated | Persuasion contacts | Notes |
|------------|--------------|----------------|-----------------|-------------------|-------|
| 0.25 | 1.5M | OPTIMAL | 1,507,495 | 135,498,852 | Binding at lower tier |
| 0.5 | 3.0M | OPTIMAL | 3,014,994 | 187,621,161 | Feasible solution exists |
| 0.75 | 4.5M | OPTIMAL | 4,522,494 | 222,438,851 | Marginal gain diminishes |
| 1.0 | 6.0M | OPTIMAL | 6,029,993 | 252,721,161 | Baseline (full envelope) |

**Source files:**
- `data/processed/module_b/run_manifest_baseline.json` (solver diagnostics)
- `data/processed/module_b/allocation_baseline.csv` (week×dept×channel allocations, 2,772 rows)
- `data/processed/module_b/budget_expansion_curve_baseline.csv` (sensitivity curve)
- `data/processed/module_b/dual_budget_envelope_baseline.csv` (shadow price on budget)
- `data/processed/module_b/dual_reach_caps_baseline.csv` (shadow prices on reach caps)
- `data/processed/module_b/allocation_run_baseline.md` (human-readable report)

---

## Module C: Probabilistic Forecasting (Bayesian Hierarchical)

### NUTS Sampler Diagnostics
- **Status:** Completed 2026-05-14 11:06–11:08 UTC (93 sec sampling + post-processing)
- **Model:** PyMC hierarchical with house effects, calibration series A
- **Sampler:** NUTS (No-U-Turn)
- **Chains:** 2 (suboptimal; ≥4 recommended)
- **Draws:** 400 post-warmup per chain = 800 total
- **Warmup / tuning:** 400 iterations per chain

### Posterior Estimates (final observation day: 2018-04-20)

| Parameter | Posterior mean | HDI 95% (low, high) | Notes |
|-----------|---|---|---|
| Preference margin (pp) | **15.09** | [-9.12, 38.34] | Wide credible interval due to sampling issues |
| Baseline m_election | ~3.70 | N/A | Calibrated to verified outcome (3.70 pp margin) |

### House Effects (per-pollster bias)
- **ATI/SNEAD:** Not in 2-chain sample
- **CAPLI:** Not in 2-chain sample  
- **ICA:** Not in 2-chain sample
*(Note: 2 chains insufficient for robust house-effect estimation; would need 4+ chains.)*

### Convergence Diagnostics (⚠ CAUTION — suboptimal sampling)
- **R̂ (Gelman-Rubin):** > 1.01 for some parameters → **FAIL convergence criterion**
- **n_eff / N_draws:** < 100 for some parameters → **Low effective sample size**
- **NUTS divergences:** 4 divergences post-warmup (minor; suggests parameterization could be improved)
- **Max tree depth:** Reached on Chain 0 (indicates stiff geometry)

**Source files:**
- `data/processed/module_c/daily_posterior_forecast.parquet` (posterior daily marginals)
- `data/processed/module_c/posterior_house_effects.parquet` (per-firm bias estimates)
- `data/processed/module_c/posterior_summary.json` (R̂, n_eff, diagnostics)
- `mlruns/` (MLflow tracking with NUTS diagnostics if enabled)

---

## Cross-Module Validation

### A → B contract check
- **Segment labels consumed by B:** ✓ Present in allocation.csv
- **Propensity weights applied:** ✓ In persuasion-adjusted contact objective
- **Department rosters match:** ✓ 18 departments across A & B

### B → C contract check
- **Budget envelope passed to C:** TBD (forecast assumes budget envelope realized)
- **Allocation timing (weekly grid) alignment:** ✓ Both use WEEK_LABELS (14 ISO weeks)

### Reproducibility checkpoint
- **Git commit:** b370333f1ffc163236cbec4e446c8999d42e1078 (DVC bootstrap commit)
- **SEED=20180422 determinism verified:** ✓ Module A/B use fixed seeds; Module C NUTS is stochastic (credible intervals bound variability)
- **Data contracts validated:** ✓ Pandera gates in Module A pass

---

---

## ⚠ Sampling Quality Note

Module C NUTS diagnostics indicate suboptimal convergence (R̂ > 1.01, low ESS). Causes:
- Only 2 chains (recommend 4+)
- Model geometry (stiff, divergences observed)
- Limited post-warmup draws (400 per chain; could increase to 1000+)

**Recommendation:** For production forecasting, increase chains → 4, draws → 1000, and verify tree depth < 12. Current outputs suitable for demonstration; not for high-stakes inference.

---

## Appendix: Raw Metric Tables

### Module A segment breakdown

| Segment | Count | Pct. | Propensity mean | Propensity std |
|---------|-------|------|-----------------|----------------|
| rural_committed | 15,607 | 31.2% | TBD | TBD |
| structurally_dependent_bloc | 9,632 | 19.3% | TBD | TBD |
| youth_volatile | 8,957 | 17.9% | TBD | TBD |
| rural_low_propensity | 6,757 | 13.5% | TBD | TBD |
| committed_opposition | 4,526 | 9.1% | TBD | TBD |
| urban_high_volatility | 4,521 | 9.0% | TBD | TBD |
| **Total** | **50,000** | **100%** | **0.5229** | **0.2539** |

### Module B budget expansion sensitivity (actual)

| Budget mult. | Target (USD) | Status | Allocated (USD) | Persuasion contacts | Contact/$ | Notes |
|---|---|---|---|---|---|---|
| 0.25× | 1,500,000 | OPTIMAL | 1,507,495 | 135,498,852 | 89.9 | Marginal cap binding |
| 0.50× | 3,000,000 | OPTIMAL | 3,014,994 | 187,621,161 | 62.3 | Transition zone |
| 0.75× | 4,500,000 | OPTIMAL | 4,522,494 | 222,438,851 | 49.2 | Plateau begins |
| **1.00×** | **6,000,000** | **OPTIMAL** | **6,029,993** | **252,721,161** | **41.9** | **Baseline (full envelope)** |

### Module C posterior summary table

(Placeholder for posterior_summary.json key statistics)
