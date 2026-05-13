---
title: "Technical Case Study: Decision Analytics Reconstruction"
subtitle: "Architecture, methodology, and implementation decisions for a three-module national-scale decision analytics system"
author: "Rafael Bragá-Kribitz · Data Science Portfolio"
date: "2026"
geometry: margin=2.5cm
fontsize: 10pt
linestretch: 1.35
colorlinks: true
linkcolor: "NavyBlue"
---

\newpage

# System Overview

This document describes the technical architecture and implementation decisions of a three-module decision analytics system built as a practitioner reconstruction. The system processed 4,260,816 entities across 18 geographic units, allocated a constrained budget across 11 channel types over 18 weeks, and produced a calibrated probabilistic forecast of a verifiable binary outcome.

**Outcome:** Program achieved objective by +3.70 pp (Series A) and +3.88 pp (Series B). Verified by TSJE 2018.

---

# Module A: Population Modeling and Segmentation

## Architecture

```
generation.yaml          → generator.py         → population_raw.parquet
calibration_anchors.yaml → raw_injector.py       → population_raw_flawed.parquet
model_params.yaml        → cleaner.py            → population_master_clean.parquet
                         → features/demographic  → (engineered features)
                         → features/behavioral   → (interaction terms)
                         → features/reachability → (channel access scores)
                         → models/segmentation   → segment_labels.parquet
                         → models/propensity     → participation_propensity.parquet
                         → evaluation/validator  → qa_report.md
                         → app/streamlit_dashboard
```

## Synthetic data generation

The raw population is generated from verified demographic anchors. Key design decisions:

**IPF/raking.** Simple `rng.choice()` with probability weights produces marginal distributions that can drift from anchors due to interaction effects (e.g., rural × language). Two raking passes are applied: (1) binary raking of `rural_flag` to the verified 38.3% rural share via random bit-flipping, (2) categorical raking of `language_census_bucket` to DGEEC bilingualism marginals. This is a simplified IPF; full iterative proportional fitting is deferred to the cleaner.

**Department weights.** Electoral-roll population shares (TSJE 2018) normalized to sum exactly to 1.0. Eighteen departments including Asunción (treated as a separate administrative unit). Weight for Central ≈ 32.6%, consistent with Central being the most populous department.

**Flaw injection.** Thirteen realistic data quality problems are injected into the raw layer by `raw_injector.py`, calibrated to observed rates in real administrative data collection:

| Flaw type | Rate | Mechanism |
|---|---|---|
| Cédula format error | 3.5% | Missing zero-pad on 7-digit numbers |
| Duplicate registration | 1.2% | Cross-office re-entry simulation |
| Department typo | 2.5% | "Cordilera", "Caaguazu" variants |
| Municipality null | 8.0% | Blank field from field collection |
| Date format swap | 1.8% | MM/DD/YYYY from 2 offices |
| Encoding error | 4.0% | Windows-1252 → UTF-8 garble |
| Phone format variant | 4.5% | Three observed formats |
| Gender variant | 3.0% | "Masculino", "1", "2" |
| Age range error | 0.8% | Transposed DOB producing age <18 or >120 |
| Schema drift | 1.5% | Column naming inconsistency |
| Sentiment scale | 20.0% | Inconsistent 1–5 scale across offices |
| District null | 25.0% | Neighborhood name not collected |
| Rural flag absent | 100% | Always derived; never in raw |

The 14-step cleaning pipeline in `cleaner.py` addresses each flaw type in documented sequence (see `reports/transformation_log.md`).

## Segmentation model

**Pre-pass: DBSCAN** identifies structural noise entities (those with unusual feature combinations that do not belong to any behaviorally coherent cluster). Noise rate target: < 1%. Epsilon and min_samples tuned on a 10K sample; validated on full population.

**K-Means (k=6)** applied to the non-noise population on a 14-feature matrix:

```
age_bin_encoded, gender_encoded, youth_flag, senior_flag,
language_jopara_encoded, nbi_stress_prior_scaled,
structural_dependency_encoded, preference_proxy_encoded,
reachability_digital, reachability_broadcast_tv,
reachability_broadcast_radio, metro_flag, chaco_flag,
rural_offline_compound
```

Acceptance criteria: mean silhouette > 0.35, bootstrap ARI > 0.80 across 100 seeds.

The six resulting segments have interpretable behavioral profiles (see model card). The segment names are operationally meaningful labels assigned post-hoc, not clustering inputs.

## Propensity model

**Model:** Logistic regression with L2 regularization, trained on synthetic population with known participation outcomes (derived from calibration anchors + noise).

**Calibration:** Platt scaling post-hoc to linearize the sigmoid. Reliability diagram checked per decile; max deviation target < 3 pp.

**Department raking:** Post-calibration rake multiplier per department, computed from the ratio of verified departmental participation rate (calibration_anchors.yaml) to model-predicted mean. Applied as a multiplicative correction to raw logit before sigmoid.

**Acceptance criteria:**

| Metric | Target | Rationale |
|---|---|---|
| AUC-ROC | > 0.70 | Better than stratified baseline |
| Brier score | < 0.22 | 10 pp improvement over naive Brier (0.238 at p=0.6125) |
| Reliability diagram | < 3 pp per decile | Per scope §7.3 |
| National mean propensity | 61.25% ± 0.1 pp | Matches verified TSJE anchor |

**SHAP analysis:** LinearExplainer on 10K-entity sample. Feature importance used to validate that the model is learning from behavioral signals, not from artifacts of the generation process.

---

# Module B: Resource Allocation Engine

## Problem formulation

Mixed-integer linear program over the decision space: `x[d, c, w]` = budget allocated to department `d`, channel `c`, week `w`.

**Objective:** Maximize total persuasion-adjusted contacts:
```
max Σ_{d,c,w}  x[d,c,w] / unit_cost[d,c]
              × persuasion_weight[segment_affinity(d,c)]
              × (1 - reach_utilisation[d,c,w] / reach_cap[d,c])
```

**Constraints:**
- `Σ_c,w x[d,c,w] ≤ budget_envelope[d]` (department budget cap)
- `Σ_w x[d,c,w] / unit_cost[d,c] ≤ reach_cap[d,c]` (population coverage ceiling)
- `x[d,c,w] ≥ 0` (non-negativity)
- `Σ_d x[d,c,w] / unit_cost[d,c] ≥ coverage_min × population[d]` for ≥80% of municipalities
- FX constraint: `TC_ref_used ∈ [5,500, 5,700] PYG/USD` (BCP Q1 2018 corridor)

**Solver:** PuLP with CBC backend. OPTIMAL status required; INFEASIBLE halts execution and triggers systematic debugging before any constraint relaxation.

## FX modeling

The Guaraní/USD rate is modeled as a weekly time series with:

- Reference rate from BCP daily TC_Ref (Q1 2018: 5,500–5,700 PYG/USD)
- Retail spread: ~+50 PYG/USD above reference
- Scenario bands: baseline (5,600), strengthening (5,500), weakening (5,700)

All budget figures reported in both USD and PYG to separate operational decisions from FX exposure.

## API layer

FastAPI endpoint for re-optimization with updated inputs (new segment scores, updated FX rate). P95 latency target: ≤ 2 seconds under 10 concurrent requests.

---

# Module C: Probabilistic Forecasting

## Model architecture

Bayesian hierarchical tracking model built in PyMC. The generative model:

```
preference_margin[t] ~ Normal(mu[t], sigma_obs)
mu[t] = alpha + Σ_j beta[j] * X[t,j] + house_effect[pollster]
alpha ~ Normal(prior_mean, prior_sd)   # calibrated to pre-campaign anchor
house_effect[k] ~ Normal(0, sigma_house)
sigma_house ~ HalfNormal(5.0)          # house effect SD < 5 pp target
sigma_obs ~ HalfNormal(10.0)
```

## Sampling diagnostics (acceptance criteria)

| Diagnostic | Target | Rationale |
|---|---|---|
| R-hat (all vars) | < 1.01 | ArviZ/PyMC standard |
| ESS_bulk | > 400 | Reliable posterior summary |
| ESS_tail | > 400 | Reliable tail estimates |
| Divergences (post-tuning) | 0 | No geometry pathologies |

Any violation blocks delivery. Reparameterization requires systematic debugging (4-phase protocol) before any prior change.

## House effect correction

Four polling sources showed structural biases:

| Pollster | Estimated house effect | Direction |
|---|---|---|
| ATI/Snead | −5.1 pp | Understates Series A |
| ICA | +3.8 pp | Overstates Series A |
| CAPLI | −0.4 pp | Near-unbiased (lowest transparency rating) |
| OEA/EU | −1.1 pp | Mild Series A understatement |

The model treats house effects as unknown parameters with a shrinkage prior, estimated jointly with the preference trajectory.

## Scenario engine (Monte Carlo)

10,000 Monte Carlo draws simulate shock scenarios:

- **Baseline tracker:** Moderate shocks (scale ~1.0×)
- **Moderate tracker:** Medium shocks (scale ~1.5×)
- **Extreme tracker:** Large shocks (scale ~1.8–2.4×)

Shock sources: late-breaking adverse events, polling infrastructure failures, turnout depression in Youth Volatile segment.

**Known pipeline issue (flagged):** `alloc_mean_persuasion_contacts` is currently unlinked from Module B solver outputs, meaning the MC model cannot yet quantify how budget reallocation affects win probability. This is the priority cross-module integration fix.

## Quarto deliverable

Module C outputs a rendered Quarto document (`module_c_forecasting_scenarios/portfolio/quarto/post_mortem.qmd`) containing the full post-mortem analysis. `quarto render` exit 0 is a required delivery gate.

---

# Engineering Standards

## Test-driven development

Every `src/` change follows the TDD iron law: failing test first → minimal implementation → green. The test suite is CI-gated with an 80% coverage floor.

```
138 tests — Module A (pytest, includes pandera schema contracts)
153 tests — EDA validation (pytest)
  0 failures across both suites
```

## Schema contract enforcement

Column names are never bare strings in `src/`. All column names are `Final` typed constants in `schema.py`, imported explicitly. The raw layer uses `_raw` suffixed constants where the clean layer uses clean names (e.g., `ENC_SOURCE_RAW` in generator output, `ENC_SOURCE` in cleaner output). Schema contracts are versioned YAML files in `schema_contracts/`.

## Reproducibility

- All random operations use an explicitly seeded `numpy.random.Generator` from `seeds.py`
- `RANDOM_SEED` environment variable sets the global seed; defaults to `20180422` (outcome event date)
- All outputs are version-pinned via run manifests (JSON sidecar files)
- MLflow experiment tracking for model runs

## Data quality gates (QA)

Thirteen quantitative acceptance gates are checked by `evaluation/validator.py` before any downstream module receives Module A outputs. A `QAGateFailure` exception halts the pipeline and requires documented resolution before the gate is reopened.

---

# Repository Structure

```
decision-analytics-reconstruction/
├── module_a_population_segmentation/    # [FLAGSHIP] Core pipeline
│   ├── src/population_segmentation/
│   │   ├── data/          # generator, cleaner, raw_injector
│   │   ├── features/      # demographic, behavioral, reachability
│   │   ├── models/        # segmentation, propensity
│   │   ├── evaluation/    # validator, calibration_metrics, clustering_metrics
│   │   ├── visualization/ # segment_profiles, calibration_curves
│   │   └── pipeline/      # export
│   ├── config/            # generation.yaml, calibration_anchors.yaml, model_params.yaml
│   ├── tests/             # 116 tests, TDD-compliant
│   ├── reports/           # model cards, QA reports, transformation log
│   └── app/               # Streamlit dashboard
├── module_b_resource_allocation/        # LP solver, FX layer, FastAPI
├── module_c_forecasting_scenarios/      # PyMC models, scenario engine, Quarto
├── schema_contracts/                    # Versioned YAML column contracts
├── appendix/                            # Verified calibration anchors
└── reports/                             # Case studies, EDA, decision log
```

---

# Skills Demonstrated

| Skill | Where demonstrated |
|---|---|
| Statistical modeling (Bayesian) | Module C: PyMC hierarchical model, MCMC diagnostics |
| Machine learning (classical) | Module A: Logistic + Platt, DBSCAN + KMeans, SHAP |
| Optimization (LP) | Module B: PuLP/CVXPY constrained solver |
| Data engineering | Module A: 14-step cleaning pipeline, IPF raking, schema contracts |
| Software engineering | TDD, CI/CD, schema constants, reproducible seeds, Docker |
| Technical writing | Model cards, transformation log, QA reports, Quarto |
| Uncertainty quantification | Bayesian HDI, Monte Carlo scenario engine, reliability diagrams |
| Domain expertise | Demographic calibration, FX modeling, media channel optimization |
