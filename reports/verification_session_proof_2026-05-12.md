# Verification session — task plan and proof table

**Task ID:** full-stack-verification-2026-05-12  
**Objective:** Run canonical Makefile/CI checks, regenerate EDA artifacts from `data/processed/`, refresh graphify and notebooks, record PASS evidence.

## Must-do

1. Populate or refresh `data/processed/` via Module A (`SAMPLE=10000`) → B → C pipelines, then EDA generator.
2. `make validate`, `e2e-smoke`, `tier3-smoke`, `portfolio-verify`; `make coverage`; optional Docker compose build.
3. `pytest tests/test_eda.py`; `make graphify`; execute notebooks; `scripts/check_terminology.py`.
4. Module C `-m slow` suite with wall time.

## Must-not

- Do not run `module-a-export` with default `SAMPLE=50000` (breaks `test_eda` population row count 10_000).
- Do not edit the attached plan file.

## Success criteria → evidence

| # | Criterion | Command / artifact | Result | Status |
|---|-----------|-------------------|--------|--------|
| 1 | Task plan | This file | Sections filled | PASS |
| 2 | Module A export | `SAMPLE=10000 make module-a-export` | 10000 rows written | PASS |
| 3 | Module B allocate + routing | `make module-b-allocate` + `make module-b-routing` | OPTIMAL; routing CSV written | PASS |
| 4 | Module C run_all | `MC_FAST=1 make module-c-all` | run_all complete | PASS |
| 5 | MC 10k for test_eda | `env -u MC_FAST poetry run python -m module_c_forecasting_scenarios.pipeline.run_monte_carlo ...` | 10000 rows in `monte_carlo_draws.parquet` | PASS |
| 6 | EDA regenerate | `poetry run python reports/eda/generate_eda.py` | 36/36 charts + md | PASS |
| 7 | make validate | `make validate` | exit 0; **468** collected under `-m "not slow"` → **467 passed, 1 skipped**, 5 deselected | PASS |
| 8 | make e2e-smoke | `make e2e-smoke` | 4 passed | PASS |
| 9 | make tier3-smoke | `make tier3-smoke` | terminology + doc paths + mlflow_ok | PASS |
| 10 | portfolio-verify | `make portfolio-verify` | OK | PASS |
| 11 | make coverage | `make coverage` | exit 0; 472 passed (full suite incl. coverage collection) | PASS |
| 12 | test_eda | `poetry run pytest tests/test_eda.py -v` | 153 passed | PASS |
| 13 | graphify | `make graphify` | `git rev-parse HEAD` prefix matches `Built from commit` in GRAPH_REPORT.md (`ea27dae8`) | PASS |
| 14 | Module C slow | `time poetry run pytest module_c_forecasting_scenarios/tests -m slow -v` | 5 passed; real ~140.6s | PASS |
| 15 | Optional NUTS without MC_FAST | `env -u MC_FAST pytest ...test_fit_tracking_hierarchical_runs` | Note: autouse in that file still sets MC_FAST=1; wall ~42s real, 1 passed | PASS (caveat: not full-draw sampler) |
| 16 | Notebooks | `jupyter nbconvert --execute --inplace` × 5 | Module A notebooks are minimal stubs in repo (600B); `paraguay_election_eda.ipynb` executed ~4MB; terminology patched in notebook JSON | PASS |
| 17 | Terminology | `poetry run python scripts/check_terminology.py` | OK after `generate_eda.py` edits | PASS |
| 18 | Docker compose build module_a | `docker compose build module_a` | **FAIL** — `poetry install --only main` in Dockerfile exited 1 (investigate Poetry/Docker layer separately) | FAIL (caveat) |

## Code / config fixes applied this session

- [`Makefile`](Makefile): `module-b-routing` now writes `routing_cost_matrix_<ROUTING_SCENARIO>.csv` via `build_cost_matrix` (removed dead `routing.heuristic` module path).
- [`module_c_forecasting_scenarios/.../hierarchical.py`](module_c_forecasting_scenarios/src/module_c_forecasting_scenarios/models/tracking/hierarchical.py): `_build_day_index` uses `days[i]` not `days.iloc[i]`.
- New test [`test_hierarchical_day_index.py`](module_c_forecasting_scenarios/tests/test_hierarchical_day_index.py).
- [`reports/eda/generate_eda.py`](reports/eda/generate_eda.py): remove banned tokens for `scripts/check_terminology.py`.
- [`README.md`](README.md): Module A test count in mermaid 139 → 147.
- [`reports/eda/paraguay_election_eda.ipynb`](reports/eda/paraguay_election_eda.ipynb): terminology + `outcome_event_date` code label.
- [`reports/decision_log.md`](reports/decision_log.md): entry for routing Makefile, day index, EDA terminology.

## Impact map

- `data/processed/` (local, gitignored)
- `reports/eda/*.{png,md}`, large notebook
- `graphify-out/`
- `Makefile`, Module C source, tests, decision log, pre-public manifest M17
