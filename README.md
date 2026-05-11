# Decision Analytics Reconstruction

**Retrospective Reconstruction of a National-Scale Marketing and Resource Allocation Decision System**

[![CI](https://github.com/rafaelbk/decision-analytics-reconstruction/actions/workflows/ci.yml/badge.svg)](https://github.com/rafaelbk/decision-analytics-reconstruction/actions/workflows/ci.yml)
[![Module A Dashboard](https://img.shields.io/badge/dashboard-live-blue)](https://decision-analytics-module-a.onrender.com)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue)](.python-version)

---

## What this is

A practitioner rebuilt, from scratch and with full methodological rigor, the decision analytics
infrastructure originally constructed under severe operational constraints to support a
national-scale program affecting **4.26 million entities** and a verifiable high-stakes binary outcome.

The reconstruction demonstrates three interdependent analytical capabilities:

1. **Population modeling and segmentation** — synthetic population generation with verified demographic
  calibration, realistic data quality problems, and behavioral clustering into operationally distinct segments.
2. **Resource allocation** — constrained LP optimization allocating a limited budget across 18 geographic units
  and 11 channel types to maximize expected participation rate per monetary unit.
3. **Probabilistic forecasting** — Bayesian hierarchical aggregation of noisy, structurally biased measurement
  signals into a calibrated daily forecast of a binary outcome with full uncertainty quantification.

The outcome was verifiable: the program achieved its objective by a confirmed margin of **+3.70 percentage points**
against a field of 4.26 million participating entities (TSJE, April 22, 2018).

---

## Why this matters beyond the electoral context

The three analytical systems in this project are domain-agnostic. The same combination of behavioral
segmentation, constrained resource allocation, and probabilistic forecasting applies directly to any
organization managing heterogeneous customer populations under budget constraints with a binary
performance target — including B2B manufacturers, financial services, and logistics operators in
DACH markets. Participation propensity becomes churn probability; geographic departments become sales
territories; media channels become product lines; verified margin becomes measurable KPI lift.

---

## Module A is the flagship

Module A is the production-quality, fully-tested, deployed artifact. It contains 139 tests (92% coverage), CI
enforcement, a live Streamlit dashboard, model cards, pandera runtime schema contracts, and a complete 14-step
cleaning pipeline. Modules B and C demonstrate LP optimization and Bayesian forecasting
respectively; they are analytically complete but not yet packaged to the same engineering standard.
See `ROADMAP.md` for honest status on all three modules.

---

## How to evaluate this project in 10 minutes

1. **Open the Module A dashboard:** [https://decision-analytics-module-a.onrender.com](https://decision-analytics-module-a.onrender.com)
   Select k=6 clusters and examine the segment profile table.
   Observe the calibration curve for the propensity model.
   This shows the segmentation and behavioral modeling layer.
2. **Read the model cards:** [`module_a_population_segmentation/reports/model_card_propensity.md`](module_a_population_segmentation/reports/model_card_propensity.md) and [`module_a_population_segmentation/reports/model_card_segmentation.md`](module_a_population_segmentation/reports/model_card_segmentation.md)
   The problem, the data constraints, the methodology, the output, and what a practitioner does with it.
3. **Open this notebook:** `module_a_population_segmentation/notebooks/03_segmentation_analysis.ipynb`
   Analysis notebook for interpretability. Production code is in `src/`; the notebook is for exploration.

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

    A["Module A: Population Modeling & Segmentation\n[FLAGSHIP]\n139 tests · 80%+ coverage · live dashboard"]

    A --> AO["population_master_clean.parquet\nsegment_labels.parquet — 6 behavioral clusters\nparticipation_propensity.parquet\nmedia_reachability_by_segment.csv"]

    AO --> B["Module B: Resource Allocation Engine\nPuLP/CVXPY · FX-aware · FastAPI"]

    B --> BO["budget_allocation_weekly.csv\nrouting_schedules.parquet\nreallocation_counterfactuals.parquet"]

    BO --> C["Module C: Probabilistic Forecasting\nPyMC Bayesian hierarchical · Monte Carlo scenarios"]

    C --> CO["daily_posterior_forecast.parquet\nmonte_carlo_scenario_catalog.yaml\nbattleground_probability_heatmap.geojson"]
```

See `ARCHITECTURE.md` for the full component breakdown, and `schema_contracts/` for cross-module data contracts.

---

## Modules

| Module | Status | Artifact | Description |
|---|---|---|---|
| **A: Population Modeling** | Complete — 138 tests, 92% coverage | [Streamlit dashboard](https://decision-analytics-module-a.onrender.com) | Synthetic population + segmentation + propensity |
| **B: Resource Allocation** | Analytically complete — LP/MILP + routing + counterfactuals | `make module-b-allocate` / FastAPI (`make module-b-api`) | Constrained weekly allocation + FX + broadcast_to_direct |
| **C: Probabilistic Forecasting** | Analytically complete — PyMC tracking + exit + MC | `make test-module-c` / `make module-c-all` (fixture CSV) | Calibration series gate, shock catalog, scenario HTML |

---

## Setup

```bash
git clone <repo-url>
cd decision-analytics-reconstruction
poetry install
cp .env.example .env
make test          # run Module A tests
make dashboard     # launch Streamlit dashboard
```

**Requirements:** Python 3.11, Poetry. Docker optional (see `docker-compose.yml`). On legacy Mac workstations (Mac Pro with unreliable Metal stacks), prefer **Colima + `docker compose`** instead of Docker Desktop.

---

## Repository structure

```
├── README.md                    <- this file
├── ARCHITECTURE.md              <- component breakdown and cross-module contracts
├── ROADMAP.md                   <- honest status and next milestones per module
├── pyproject.toml               <- Poetry dependencies + tool config (Ruff, Black, Pyright, Pytest)
├── schema_contracts/            <- cross-module data contracts (authoritative)
├── reports/                     <- decision log, data dictionary, case studies
├── appendix/                    <- calibration anchor registry (TSJE/DGEEC verified anchors)
├── module_a_population_segmentation/  <- production implementation (fully tested)
│   ├── config/                  <- generation.yaml, calibration_anchors.yaml, model_params.yaml
│   ├── src/population_segmentation/   <- production code
│   ├── tests/                   <- 139 tests, 92% coverage
│   ├── app/                     <- Streamlit dashboard
│   └── reports/                 <- model cards, QA reports
├── module_b_resource_allocation/  <- LP/MILP allocation + routing + API
└── module_c_forecasting_scenarios/ <- forecasting, scenarios, contracts
```

---

## Honest narrative

This system was originally built under severe time and resource constraints. The reconstruction
applies the rigor, reproducibility, and statistical discipline that were absent in the original.
Every modeling choice is documented. Every synthetic data anchor is tied to a verified source.
Every uncertainty estimate is propagated rather than suppressed.

This is not a claim of original seniority. It demonstrates what the practitioner would build today.
