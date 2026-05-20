---
doc_id: DOC-TST-001
doc_type: narrative
doc_role: canonical
visibility: public
status: active
owner: project
last_reviewed: '2026-05-20'
canonical_source: null
derived_from: null
supersedes: null
tags: []
---

# Tests

This directory holds **root-level** pytest modules (cross-cutting contracts, CI, portfolio smoke). Per-module tests live under:

- `module_a_population_segmentation/tests/`
- `module_b_resource_allocation/tests/`
- `module_c_forecasting_scenarios/tests/`

## Running tests

| Command | Scope |
|--------|--------|
| `make test` | All module + root tests, **excludes** `-m slow`, with coverage on the three `src/` trees |
| `make coverage` | Same test paths as `make test` for file list; **does not** pass `-m "not slow"` (includes slow tests if not filtered) — prefer `make test` for a fast signal |
| `poetry run pytest <path> -q` | Targeted run |

Coverage flags (see root `Makefile`): `--cov=module_a_population_segmentation/src --cov=module_b_resource_allocation/src --cov=module_c_forecasting_scenarios/src`.

## Coverage baseline (combined `src/`)

**Policy:** Combined statement coverage across Module A, B, and C `src/` trees shall be **≥ 80%** when running the default suite (`make test`: `-m "not slow"`).

**Measured (2026-05-13):** `TOTAL` **83%** (3611 statements, 627 missed) with:

```bash
poetry run pytest module_a_population_segmentation/tests \
  module_b_resource_allocation/tests module_c_forecasting_scenarios/tests tests \
  -m "not slow" \
  --cov=module_a_population_segmentation/src \
  --cov=module_b_resource_allocation/src \
  --cov=module_c_forecasting_scenarios/src \
  --cov-report=term
```

Artifacts: `coverage.xml` (root), optionally `htmlcov/` if you add `--cov-report=html`.

## Documented gaps (not failures)

Low or zero coverage is **expected** for paths that only execute when a human runs a CLI, optional integrations, or heavy scenarios:

| Area | Typical reason |
|------|----------------|
| `module_b_resource_allocation/.../pipeline/run_allocation.py` | **`main()`** and file I/O paths not hit by unit tests |
| `module_b_resource_allocation/.../reporting/run_markdown.py` | CLI / report generation entrypoints |
| `module_c_forecasting_scenarios/mlflow_tracking.py` | Optional MLflow; environment-dependent |
| `module_c_forecasting_scenarios/pipeline/run_*.py` | **`if __name__ == "__main__"`** orchestration CLIs |
| `module_c_forecasting_scenarios/viz/*` | Plotly explorer; manual / notebook use |
| `module_c_forecasting_scenarios/models/tracking/hierarchical.py` | Part of **`fit_tracking_hierarchical`** / PyMC paths; partially covered by smoke tests |
| `module_c_forecasting_scenarios/models/exit/exit_model.py` | Exit pipeline branches |

Closing gaps is incremental: add focused tests or smoke that **imports and executes** thin wrappers where safe; defer GUI/MLflow until fixtures exist.

## Slow tests

Tests marked `@pytest.mark.slow` (e.g. full MCMC) are excluded from `make test`. Run with:

```bash
MC_FAST=1 poetry run pytest module_c_forecasting_scenarios/tests -m slow -q
```

(or remove `-m "not slow"` for full suite — long-running.)
