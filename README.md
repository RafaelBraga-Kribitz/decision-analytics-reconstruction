# Decision Analytics Reconstruction

**Retrospective Reconstruction of a National-Scale Marketing and Resource Allocation Decision System**

[CI](/.github/workflows/ci.yml)
[Module A Dashboard](https://decision-analytics-module-a.onrender.com)
[Python 3.11](/.python-version)

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
against a field of 4.26 million participating entities.

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

For technical depth: `src/` contains the full production pipeline.
For methodology depth: all model cards under `module_a_population_segmentation/reports/`.
For data provenance: `appendix/verified_calibration_anchors_full.md`.

---

## System architecture

```
[VERIFIED] TSJE Electoral Roll (N = 4,260,816)  ──┐
[VERIFIED] DGEEC Census 2012 + 2018 Projections ──┤
[SYNTHETIC] Collection Simulation               ──┘
                                                   ↓
                                        Module A: Population Modeling
                                        & Segmentation [FLAGSHIP]
                                                   ↓
                    ┌──────────────────────────────────────────────┐
                    │ population_master_clean.parquet (~4.26M)     │
                    │ segment_labels.parquet (6 behavioral clusters)│
                    │ participation_propensity.parquet             │
                    │ media_reachability_by_segment.csv            │
                    └───────────────────┬──────────────────────────┘
                                        ↓
                            Module B: Resource Allocation Engine
                                        ↓
                    ┌──────────────────────────────────────────────┐
                    │ budget_allocation_weekly.csv                  │
                    │ routing_schedules.parquet                    │
                    │ reallocation_counterfactuals.parquet         │
                    └───────────────────┬──────────────────────────┘
                                        ↓
                    Module C: Probabilistic Forecasting & Scenarios
                                        ↓
                    ┌──────────────────────────────────────────────┐
                    │ daily_posterior_forecast.parquet              │
                    │ monte_carlo_scenario_catalog.yaml            │
                    │ battleground_probability_heatmap.geojson     │
                    └──────────────────────────────────────────────┘
```

See `schema_contracts/` for the authoritative cross-module data contracts, and `reports/` for methodology notes.

---

## Modules


| Module                           | Status                              | Artifact                                                                | Description                                      |
| -------------------------------- | ----------------------------------- | ----------------------------------------------------------------------- | ------------------------------------------------ |
| **A: Population Modeling**       | ✅ Complete (79 tests, 92% coverage) | [Streamlit dashboard](https://decision-analytics-module-a.onrender.com) | Synthetic population + segmentation + propensity |
| **B: Resource Allocation**       | 📋 Planned — not yet in repo        | FastAPI (Swagger UI)                                                    | LP optimizer + FX routing + counterfactuals      |
| **C: Probabilistic Forecasting** | 📋 Planned — not yet in repo        | Quarto report                                                           | Bayesian aggregator + scenario engine            |


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

**Requirements:** Python 3.11, Poetry. Docker optional (see `[docker-compose.yml](docker-compose.yml)`). On legacy Mac workstations (Mac Pro with unreliable Metal stacks), prefer **Colima + `docker compose`** instead of Docker Desktop.

---

## Repository structure

```
├── README.md                    ← this file
├── pyproject.toml               ← Poetry dependencies + tool config (Ruff, Black, Pyright, Pytest)
├── schema_contracts/            ← cross-module data contracts (authoritative)
├── reports/                     ← decision log, data dictionary
├── appendix/                    ← calibration anchor registry (TSJE/DGEEC verified anchors)
├── docs/                        ← project documentation
├── module_a_population_segmentation/  ← production implementation (fully tested)
│   ├── config/                  ← generation.yaml, calibration_anchors.yaml, model_params.yaml
│   ├── src/population_segmentation/   ← production code
│   ├── tests/                   ← 79 tests, 92% coverage
│   ├── app/                     ← Streamlit dashboard
│   └── reports/                 ← model cards, QA reports
├── module_b_resource_allocation/  ← planned (not yet in repo)
└── module_c_forecasting_scenarios/ ← planned (not yet in repo)
```

---

## Honest narrative

This system was originally built under severe time and resource constraints. The reconstruction
applies the rigor, reproducibility, and statistical discipline that were absent in the original.
Every modeling choice is documented. Every synthetic data anchor is tied to a verified source.
Every uncertainty estimate is propagated rather than suppressed.

This is not a claim of original seniority. It demonstrates what the practitioner would build today.