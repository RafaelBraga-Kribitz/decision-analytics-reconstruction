# Architecture

Three-module decision analytics system. Each module is an independent deployable unit;
cross-module communication is through versioned Parquet/CSV artifacts and schema contracts.

### Canonical repository roots (three modules)

The installable Poetry packages ([`pyproject.toml`](pyproject.toml) `[tool.poetry]` `packages`) map one-to-one to these directories:

- **Module A (population segmentation):** [`module_a_population_segmentation/`](module_a_population_segmentation/) — packaged from `module_a_population_segmentation/src` as `population_segmentation`.
- **Module B (resource allocation):** [`module_b_resource_allocation/`](module_b_resource_allocation/) — packaged from `module_b_resource_allocation/src` as `module_b_resource_allocation`.
- **Module C (forecasting scenarios):** [`module_c_forecasting_scenarios/`](module_c_forecasting_scenarios/) — packaged from `module_c_forecasting_scenarios/src` as `module_c_forecasting_scenarios`.

Layout invariants are covered by [`tests/test_architecture_three_module_layout.py`](tests/test_architecture_three_module_layout.py).

Module A file-level surface and pipe import hooks are guarded by [`tests/test_architecture_module_a_surface.py`](tests/test_architecture_module_a_surface.py).

---

## Component map

```
decision-analytics-reconstruction/
│
├── module_a_population_segmentation/    [FLAGSHIP]
│   ├── config/
│   │   ├── generation.yaml              department weights, field distributions
│   │   ├── calibration_anchors.yaml     TSJE/DGEEC verified anchors + tolerances
│   │   └── model_params.yaml            feature list, model hyperparameters
│   ├── src/population_segmentation/
│   │   ├── data/
│   │   │   ├── generator.py             synthetic population (→ population_raw.parquet)
│   │   │   ├── raw_injector.py          13-flaw injection (→ population_raw_flawed.parquet)
│   │   │   ├── cleaner.py              14-step cleaning (→ population_master_clean.parquet)
│   │   │   └── validator.py            schema + calibration anchor checks (QAGateFailure)
│   │   ├── features/
│   │   │   ├── demographic.py           age_bin, gender, youth/senior flags
│   │   │   ├── behavioral.py            preference_proxy, structural_dependency, interactions
│   │   │   └── reachability.py          digital/TV/radio scores, compound indices
│   │   ├── models/
│   │   │   ├── segmentation.py          DBSCAN pre-pass + K-Means (k=6)
│   │   │   └── propensity.py            LogReg + Platt calibration + department rake
│   │   ├── evaluation/
│   │   │   ├── schema_validator.py      Pandera clean-population contract (cleaner exit gate)
│   │   │   ├── calibration_metrics.py
│   │   │   └── clustering_metrics.py
│   │   ├── visualization/
│   │   │   ├── segment_profiles.py
│   │   │   └── calibration_curves.py
│   │   ├── pipeline/
│   │   │   └── export.py                assembles final parquet/csv artifacts
│   │   └── utils/
│   │       ├── schema.py                Final-typed column name constants (never bare strings)
│   │       └── seeds.py                 RANDOM_SEED env var, default 20180422
│   ├── tests/                           140 tests, TDD-compliant, CI-gated at 80% coverage
│   ├── app/                             Streamlit dashboard (deployed on Render)
│   └── reports/                         model cards, QA report, transformation log
│
├── module_b_resource_allocation/
│   ├── src/
│   │   ├── solver.py                    PuLP CBC mixed-integer LP
│   │   ├── fx_layer.py                  BCP PYG/USD time series, scenario bands
│   │   ├── constraints.py               budget envelopes, reach caps, municipality coverage
│   │   └── api.py                       FastAPI re-optimization endpoint
│   └── tests/
│
├── module_c_forecasting_scenarios/
│   ├── src/
│   │   ├── tracker.py                   PyMC Bayesian hierarchical model
│   │   ├── house_effects.py             4-pollster shrinkage prior estimation
│   │   └── scenarios.py                 10,000-draw Monte Carlo shock engine
│   ├── portfolio/quarto/
│   │   └── post_mortem.qmd              Quarto rendered deliverable (exit 0 required)
│   └── tests/
│
├── schema_contracts/                    Versioned YAML column contracts (cross-module authority)
├── appendix/
│   └── verified_calibration_anchors_full.md   source-tagged anchor registry
└── reports/
    ├── case_study_business.md / .pdf    business-audience case study
    ├── case_study_technical.md / .pdf   technical architecture document
    └── eda/                             36-chart EDA, strategic brief, 153-test suite
```

---

## Data flow

```
generation.yaml + calibration_anchors.yaml
        │
        ▼
generator.py → population_raw.parquet
        │
        ▼ (raw_injector.py — 13 flaw types)
population_raw_flawed.parquet
        │
        ▼ (cleaner.py — 14-step pipeline + validate_clean_population in schema_validator.py)
population_master_clean.parquet
        │
        ├── features/ (demographic, behavioral, reachability)
        │
        ├── models/segmentation → segment_labels.parquet
        │
        └── models/propensity → participation_propensity.parquet
                │
                ▼
        [Module B receives]: participation_propensity, segment_labels, media_reachability
                │
                ▼ (PuLP solver)
        budget_allocation_weekly.csv + routing_schedules.parquet
                │
                ▼
        [Module C receives]: allocation outputs + polling data
                │
                ▼ (PyMC + Monte Carlo)
        daily_posterior_forecast + scenario_catalog
```

---

## Cross-module contracts

All inter-module artifact schemas are versioned in `schema_contracts/`. A downstream module
that reads an artifact must reference the contract version, not infer column names from the file.

Key contracts:

| Contract file | Produced by | Consumed by |
|---|---|---|
| `population_master_clean_v1.yaml` | Module A cleaner | Module B solver |
| `segment_labels_v1.yaml` | Module A segmentation | Module B solver |
| `participation_propensity_v1.yaml` | Module A propensity | Module B solver, Module C |
| `budget_allocation_weekly_v1.yaml` | Module B solver | Module C scenario engine |

---

## Key engineering invariants

- **Column name constants.** All column names are `Final`-typed constants in `utils/schema.py`.
  Bare string column names in `src/` are a test failure.
- **Seeded RNG.** All random operations use `numpy.random.Generator` from `utils/seeds.py`.
  `RANDOM_SEED` env var defaults to `20180422`.
- **QA / contracts.** `evaluation/schema_validator.py` runs `validate_clean_population` at the
  cleaner exit (Pandera contract). `data/validator.py` adds `validate_schema` and
  `validate_calibration_anchors`; both can raise `QAGateFailure` where wired into a run.
- **TDD.** Every `src/` change requires a failing test first. CI enforces 80% coverage floor.
- **OPTIMAL-only solver.** Module B halts on INFEASIBLE; constraint relaxation requires documented justification.
- **MCMC diagnostics.** Module C requires R-hat < 1.01, ESS > 400, zero divergences. Any violation blocks delivery.
