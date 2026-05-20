---
doc_id: DOC-ROOT-001
doc_type: narrative
doc_role: canonical
visibility: public
status: active
owner: portfolio
last_reviewed: '2026-05-20'
canonical_source: null
derived_from: null
supersedes: null
tags: []
---

# Decision Analytics Reconstruction

**Retrospective Reconstruction of a National-Scale Marketing and Resource Allocation Decision System**

[![CI](https://github.com/RafaelBraga-Kribitz/decision-analytics-reconstruction/actions/workflows/ci.yml/badge.svg)](https://github.com/RafaelBraga-Kribitz/decision-analytics-reconstruction/actions/workflows/ci.yml)
[![Module A Dashboard](https://img.shields.io/badge/Module_A-Streamlit_Dashboard-blue)](https://decision-analytics-module-a.onrender.com)
[![Module B API](https://img.shields.io/badge/Module_B-FastAPI_Docs-blue)](https://decision-analytics-module-b.up.railway.app/docs)
[![Module C Report](https://img.shields.io/badge/Module_C-Quarto_Report-blue)](https://RafaelBraga-Kribitz.github.io/decision-analytics-reconstruction/)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue)](.python-version)

---

## Executive overview (around one minute)

A national-scale **program** had to move a multi-million-dollar budget across heterogeneous geographies while honoring feasibility caps, currency corridors, and a tight weekly calendar influencing a measurable **preference proxy**. The reconstruction packages three interoperable streams: behavioural segmentation plus participation scoring on an entity-scale **population dataset**, constrained MILP allocation with reproducible manifests, and probabilistic condensation of biased **survey measurement** into coherent uncertainty. The payoff for a VP without code access is spelled out economically in `[reports/business_case.md](reports/business_case.md)`: transparent **department-uniform naive** spend vs optimized allocation (with seeded reruns via `make module-b-allocate`), plus documented downside shocks for budget truncation and modeled FX posture. Calibration boundaries—what mirrors verified registries versus synthetic layers—sit in `[reports/epistemic_boundaries.md](reports/epistemic_boundaries.md)`. For stakeholder-to-artifact routing, skim `[reports/stakeholder_scenario_table.md](reports/stakeholder_scenario_table.md)`.

---

## What this is

A practitioner rebuilt the decision analytics stack that originally supported a
national-scale program affecting **4.26 million entities** and a verifiable binary outcome event.

The reconstruction demonstrates three interdependent capabilities:

1. **Population modeling and segmentation** — synthetic population dataset generation with verified demographic
  calibration, realistic data quality problems, and behavioral clustering into operationally distinct segments.
2. **Resource allocation** — constrained LP/MILP (PuLP + CBC) allocating a limited budget across 18 geographic units
  and 11 channel types to maximize a persuasion-adjusted contact proxy per monetary unit.
3. **Probabilistic forecasting** — Bayesian hierarchical aggregation of noisy, structurally biased survey measurements
  into a daily preference-proxy track with uncertainty (Module C; fixture-backed fast CI plus slow NUTS diagnostics).

The outcome event margin was verifiable: **+3.70 percentage points** against a field of 4.26 million participating entities (TSJE, April 22, 2018).

**Epistemic calibration:** see `[reports/epistemic_boundaries.md](reports/epistemic_boundaries.md)` for what is verified vs simulated vs illustrative.

---

## What makes this portfolio different

Most analytics portfolios are either **predictive** (build a classifier or regression model) or **descriptive** (produce dashboards and reports). This one is **prescriptive**: it combines three interoperable systems to answer "**where should we spend, how confident are we, and what happens if constraints shift?**" rather than "what will happen?" This requires decision-layer engineering — not just modeling. That means exposing dual values (marginal costs of constraints), validating contracts between modules, and shipping manifests so that 6 months later a CFO can trace a budget decision back to the RNG seeds that powered it. Most portfolios use "reproducibility" to mean "code runs again." Here it means the numbers provably match down to floating-point precision given the same seeds and dependency versions. The shift from "model accuracy" to "decision traceability" is structural; it reshapes how you validate (test shadow prices, not just AUC), how you hand off code (schema contracts, not just function signatures), and how you position hiring value (operations research + statistical rigor, not machine learning).

---

## Why this matters beyond the electoral context

The three analytical systems in this project are domain-agnostic. The same combination of behavioral
segmentation, constrained resource allocation, and probabilistic forecasting applies directly to any
organization managing heterogeneous customer populations under budget constraints with a binary
performance target — including B2B manufacturers, financial services, and logistics operators in
DACH markets. Participation propensity becomes churn probability; geographic departments become sales
territories; media channels become product lines; verified margin becomes measurable KPI lift.

---

## Positioning (hiring signal)

This repository is best read as **decision analytics / marketing science / analytical engineering**: translating operational programs into reproducible systems (segmentation, constrained allocation, probabilistic measurement aggregation) — not as a generic “deep AI” or Kaggle-style single-notebook portfolio.

---

## Module A is the flagship

Module A is the most heavily engineered surface: CI with lint + Pyright + coverage floor, a live Streamlit dashboard, model cards, Pandera runtime schema contracts, and the full cleaning pipeline. Modules B and C ship **production-oriented** solver and forecasting code with growing test and reporting coverage; Module B now emits dual and budget-expansion CSVs when run with `--sensitivity` (see `make module-b-allocate-sensitivity`). Status detail: `ROADMAP.md`.

---

## How to evaluate this project in 10 minutes

1. **Open the Module A dashboard:** [https://decision-analytics-module-a.onrender.com](https://decision-analytics-module-a.onrender.com)
  Select k=6 clusters and examine the segment profile table.
   Observe the calibration curve for the propensity model.
   This shows the segmentation and behavioral modeling layer.
2. **Read the model cards:** `[module_a_population_segmentation/reports/model_card_propensity.md](module_a_population_segmentation/reports/model_card_propensity.md)` and `[module_a_population_segmentation/reports/model_card_segmentation.md](module_a_population_segmentation/reports/model_card_segmentation.md)`
  The problem, the data constraints, the methodology, the output, and what a practitioner does with it.
3. **Open this notebook:** `module_a_population_segmentation/notebooks/03_segmentation_analysis.ipynb`
  Analysis notebook for interpretability. Production code is in `src/`; the notebook is for exploration.
4. **Technical walkthrough (one entity row):** `[reports/system_walkthrough.md](reports/system_walkthrough.md)`

For technical depth: `src/` contains the full production pipeline.
For methodology depth: all model cards under `module_a_population_segmentation/reports/`.
For data provenance: `appendix/verified_calibration_anchors_full.md`.

---

## System architecture

```mermaid
flowchart TD
    TSJE["[VERIFIED] TSJE Electoral Roll\nN = 4,260,816"]
    DGEEC["[VERIFIED] DGEEC Census 2012 + 2018"]
    SIM["[SYNTHETIC] Collection Simulation\n13 injected flaw types"]

    TSJE --> A
    DGEEC --> A
    SIM --> A

    A["Module A: Population Modeling & Segmentation\n[FLAGSHIP]\n806 tests · 87% coverage · live dashboard"]

    A --> AO["population_master_clean.parquet\nsegment_labels.parquet — 6 behavioral clusters\nparticipation_propensity.parquet\nmedia_reachability_by_segment.csv"]

    AO --> B["Module B: Resource Allocation Engine\nPuLP + CBC · FX-aware · FastAPI"]

    B --> BO["budget_allocation_weekly.csv\nrouting_schedules.parquet\nreallocation_counterfactuals.parquet"]

    BO --> C["Module C: Probabilistic Forecasting\nPyMC Bayesian hierarchical · Monte Carlo scenarios"]

    C --> CO["daily_posterior_forecast.parquet\nmonte_carlo_scenario_catalog.yaml\nbattleground_probability_heatmap.geojson"]
```



See `ARCHITECTURE.md` for the full component breakdown, and `schema_contracts/` for cross-module data contracts.

---

## Modules


| Module                           | Status                                                       | Artifact                                                                                                                | Description                                                                       |
| -------------------------------- | ------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| **A: Population Modeling**       | CI-complete — see Module A job in `.github/workflows/ci.yml` | [Streamlit dashboard](https://decision-analytics-module-a.onrender.com)                                                 | Synthetic population dataset + segmentation + propensity                          |
| **B: Resource Allocation**       | CI job + dual/budget expansion reports (`--sensitivity`)     | [FastAPI docs](https://decision-analytics-module-b.up.railway.app/docs) · `make module-b-api` (local)                   | Constrained weekly allocation + FX + broadcast_to_direct counterfactual           |
| **C: Probabilistic Forecasting** | Fast pytest in CI; slow NUTS diagnostics optional            | [Quarto report](https://RafaelBraga-Kribitz.github.io/decision-analytics-reconstruction/) · `make module-c-all` (local) | Bayesian posterior track, house effects, MC scenarios, battleground probabilities |


---

## Setup

```bash
git clone <repo-url>
cd decision-analytics-reconstruction
poetry install
cp .env.example .env
make test              # all modules + portfolio smoke (excludes slow NUTS)
make validate          # lint + typecheck + tests + documentation governance (doc paths + registry)
make e2e-smoke         # fixture-only cross-module smoke (A schema + B solve + C CSV + handshake)
make tier3-smoke       # terminology sample + mlflow import (local mirror of part of CI tier3 job)
make portfolio-verify  # git-index hygiene for portfolio exports
make dashboard         # launch Streamlit dashboard (Module A)
make module-a-pipeline # Module A end-to-end (alias for `poetry run python -m population_segmentation.pipeline`)
make pipeline-dev      # Module A dev pipeline (n=10k, ~3–5 min; override: SAMPLE=50000 for ~15–20 min)
```

**Module A batch pipeline:** From the repo root, `poetry run python -m population_segmentation.pipeline` runs generation → injection → cleaning → features → segmentation → propensity with defaults pointing at `module_a_population_segmentation/config/` and `data/processed/`. Override with `--config`, `--anchors`, `--out-dir`, `--sample-size`. Writes parquet/CSV outputs plus `model_run_manifest.json` (package version, UTC timestamp, git commit, RNG seeds). Data-science framing docs: `[reports/model_hierarchy.md](reports/model_hierarchy.md)`, `[reports/module_a_model_io_spec.md](reports/module_a_model_io_spec.md)`, `[reports/feature_engineering_justification.md](reports/feature_engineering_justification.md)`. Notebook walkthrough: `[module_a_population_segmentation/notebooks/01_end_to_end_walkthrough.ipynb](module_a_population_segmentation/notebooks/01_end_to_end_walkthrough.ipynb)`.

**Requirements:** Python 3.11, Poetry. Docker optional (see `docker-compose.yml`). On legacy Mac workstations (Mac Pro with unreliable Metal stacks), prefer **Colima + `docker compose`** instead of Docker Desktop.

**Module A / Module C observability (optional):** MLflow logging is **opt-in**. Set `MLFLOW_TRACKING_URI` (and optionally `MLFLOW_EXPERIMENT_NAME`) when you want runs recorded; Module C entry points such as `python -m module_c_forecasting_scenarios.pipeline.run_tracking` and Module A export (`run_export` / `population_segmentation.pipeline`) log only when that environment is present. To view runs locally: `poetry run mlflow ui` (opens [http://localhost:5000](http://localhost:5000)).

**Data versioning (DVC):** A `dvc.yaml` pipeline defines three reproducible stages (`module_a` → `module_b` → `module_c`), each with explicit `deps`, `outs`, and `metrics`. Running `dvc repro` regenerates all `data/processed/` artifacts from source; `dvc status` returns clean immediately after. Reference artifact MD5 hashes are documented in `[tests/REPRODUCIBILITY.md](tests/REPRODUCIBILITY.md)`. To reproduce from scratch: `poetry install --extras tracking && dvc repro`. To restore artifacts without re-running: `dvc pull` (requires a configured remote). The default remote (`local-cache`) points at `../../decision-analytics-dvc-cache`; to override: `poetry run dvc remote modify local-cache url s3://bucket/path` (or GCS/Azure/SSH). Raw inputs (`data/raw/`) stay empty because the population dataset is synthesized on demand from `module_a_population_segmentation/config/`.

---

## Production Deployment (Cloud Run)

**Current endpoints (legacy):**
- Module A: https://decision-analytics-module-a.onrender.com (Render)
- Module B: https://decision-analytics-module-b.up.railway.app (Railway)
- Module C: https://RafaelBraga-Kribitz.github.io/decision-analytics-reconstruction/ (GitHub Pages)

**New: Deploy to Google Cloud Run** (parallel infrastructure):

```bash
# 1. Set up Artifact Registry + Cloud Storage
make setup-artifact-registry GCP_PROJECT=<your-project-id>

# 2. Deploy Module A (Streamlit) to Cloud Run
make deploy-module-a GCP_PROJECT=<your-project-id>

# 3. Deploy Module B (FastAPI) to Cloud Run
make deploy-module-b GCP_PROJECT=<your-project-id>

# 4. Smoke test live endpoints
make smoke-test MODULE_A_URL=<url> MODULE_B_URL=<url>

# Rollback if needed
make rollback-module-a GCP_PROJECT=<your-project-id>
make rollback-module-b GCP_PROJECT=<your-project-id>
```

**Architecture:** Docker → Artifact Registry (europe-west3) → Cloud Run (2 Gi for A, 1 Gi for B, auto-scaling, health checks `/` and `/healthz`).

**Automatic deployment:** Push to `main` triggers GitHub Actions workflow. Requires Workload Identity setup ([see GITHUB_ACTIONS_SETUP.md](docs/GITHUB_ACTIONS_SETUP.md)).

**Cost:** ~$15–$50/month for both modules (estimated; depends on traffic). See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for full cost breakdown and observability guide.

---

## Repository structure

```
├── README.md                          <- this file
├── ARCHITECTURE.md                    <- component breakdown and cross-module contracts
├── ROADMAP.md                         <- honest status and next milestones per module
├── docs/INDEX.md                      <- generated navigation from docs/registry/docs_registry.yaml
├── docs/registry/docs_registry.yaml    <- machine-readable doc inventory (SSOT for documentation graph)
├── IMPLEMENTATION_PLAN.md             <- authoritative phase and gate status (`DOC-PLAN-001`)
├── pyproject.toml                     <- Poetry dependencies + tool config (Ruff, Black, Pyright, Pytest)
├── schema_contracts/                  <- cross-module data contracts (authoritative)
├── reports/                           <- decision log, data dictionary, case studies
├── appendix/                          <- calibration anchor registry (TSJE/DGEEC verified anchors)
├── module_a_population_segmentation/  <- production implementation (fully tested)
│   ├── config/                        <- generation.yaml, calibration_anchors.yaml, model_params.yaml
│   ├── src/population_segmentation/   <- production code
│   ├── tests/                         <- pytest suite (see CI for counts)
│   ├── app/                           <- Streamlit dashboard
│   └── reports/                       <- model cards, QA reports
├── module_b_resource_allocation/      <- LP/MILP allocation + routing + API
└── module_c_forecasting_scenarios/    <- forecasting, scenarios, contracts
```

---

## Benchmark comparison (illustrative on synthetic reconstruction)


| Baseline                            | Module | Metric (higher is better unless noted)                                                      | Source                                                                                          |
| ----------------------------------- | ------ | ------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Naive participation-rate classifier | A      | Brier ≈ 0.245 vs model 0.088                                                                | `[model_card_propensity.md](module_a_population_segmentation/reports/model_card_propensity.md)` |
| Scenario timing variants            | B      | Compare `total_persuasion_adjusted_contacts` across `baseline` / `early_lock` / `late_flex` | `scenario_benchmark_*.csv` from `make module-b-allocate-sensitivity`                            |
| Fixture-only tracking               | C      | Posterior export row count equals campaign day index                                        | `module_c_forecasting_scenarios/tests/test_tracking_smoke.py`                                   |


These deltas quantify **internal reconstruction targets**, not external campaign lift.

---

## Disclaimer

The original system was built under severe operational constraints. This repository documents modeling choices, enforces tests in CI, and separates verified anchors from synthetic layers (`[reports/epistemic_boundaries.md](reports/epistemic_boundaries.md)`). It is a reconstruction exercise demonstrating what the practitioner would build today—not a claim of original operational seniority.