# Implementation Plan

**Project:** Paraguay 2018 Election Forecasting Reconstruction (A+ Portfolio Edition)  
**Phases:** 1–9 (corresponding to action-plan Tiers T1–T9)  
**Last Updated:** 2026-05-14  
**Gate:** Gate 11 closure (Documentation completeness)

---

## Phase Summary

| Phase | Title | Effort | Status | Quality Gate |
|---|---|---|---|---|
| **1** | Blockers (CI, MLflow, E2E walkthrough, docs baseline) | 5.25h | ✅ COMPLETE | Gate 9 (CI green) |
| **2** | Unit tests + contract validation | ~4h | ✅ COMPLETE | Gate 10 (all tests pass) |
| **3** | Linter + CI cleanup (ruff, black, pre-commit) | ~3.5h | ✅ COMPLETE | Gate 2 (lint green) |
| **4** | T4 architecture verification (schema contracts, test suite) | ~1h | ✅ COMPLETE | Gate 11 (contract tests pass) |
| **5** | DVC pipeline + reproducibility (dvc.yaml, dvc.lock, .dvc/) | ~3h | ✅ COMPLETE | Gate 13 (dvc pipeline runs, outputs hash to manifest) |
| **6** | Tier 3 components (T6-1 through T6-4: TSP/VRP routing, MC engine, battleground heatmap, MILP bundles) | ~11h | ✅ COMPLETE | Acceptance: all Tier 3 artifacts present, tests pass |
| **7** | Documentation completeness (IMPLEMENTATION_PLAN.md, data dict, decision log, epistemic boundaries, baseline comparison) | 6h | 🔄 IN PROGRESS | Gate 11 (5 docs complete, `verify_doc_code_paths.py` passes) |
| **8** | Pyright strict mode + Docker smoke test CI | ~8.5h | ⏳ PLANNED | Gate 7 (Docker builds; Gate 4/§3 Architecture strict type checks) |
| **9** | Statistical rigor completion (walk-forward validation, PPC, interval coverage) | ~6-7h | ⏳ PLANNED | Gate 5 (statistician verification; evidence for all claims) |

---

## Phase 1: Blockers — CI, MLflow, Documentation Baseline

**Duration:** 5.25h | **Status:** ✅ COMPLETE  
**Quality Gate:** CI pipeline runs; MLflow local file store initialized; executive summary added  
**Dependencies:** None (foundational)

### Deliverables

- **T1-1:** Pyright strict on Module C `src/` (0.5h) — Added CI job `typecheck_module_c`
- **T1-2:** Slow-pipeline acceptance test (0.25h) — Confirmed `test_architecture_pipeline_dev_contract` passes
- **T1-3:** MLflow local file store (2h) — Configured at `./mlruns/`; runs, metrics, params, artifacts tracked
- **T1-4:** End-to-end walkthrough notebook (1.5h) — `notebooks/01_end_to_end_walkthrough.ipynb` traces entity → segment → propensity
- **T1-5:** Business case CFO summary (1h) — `reports/business_case.md` preamble added; "preference proxy" defined upfront

### Verification

Run: `make ci` — 771 tests pass; MLflow directory initialized.

---

## Phase 2: Unit Tests + Contract Validation

**Duration:** ~4h | **Status:** ✅ COMPLETE  
**Quality Gate:** All unit tests pass; Pydantic contracts valid; schema contracts non-null  
**Dependencies:** Phase 1

### Deliverables

- **T2-1:** Module A unit test expansion (1h)
- **T2-2:** Module B unit test coverage (1.5h)
- **T2-3:** Module C unit test suite (1h)
- **T2-4:** Pydantic handshake schema validation (0.5h)

### Verification

Run: `make test` — 771 tests pass (zero failures).

---

## Phase 3: Linter + CI Cleanup

**Duration:** ~3.5h | **Status:** ✅ COMPLETE  
**Quality Gate:** All linter checks pass; pre-commit hooks active; ruff/black agree  
**Dependencies:** Phase 2

### Deliverables

- **T3-1:** Ruff configuration + rule fixes (1.5h) — Fixed E501, I001, F401, SIM300, etc.
- **T3-2:** Black code formatter (1h) — Normalized spacing, line wrapping
- **T3-3:** Pre-commit hook CI (1h) — Hook runs on every commit; CI jobs verify

### Verification

Run: `make lint` — Zero errors.

---

## Phase 4: Architecture Verification

**Duration:** ~1h | **Status:** ✅ COMPLETE  
**Quality Gate:** Schema contracts present; test suite validates contracts; Gate 11 pre-check passes  
**Dependencies:** Phase 3

### Deliverables

- **T4-1:** Schema contract YAML files (0.3h) — 19 YAML files in `schema_contracts/`
- **T4-2:** Contract validation tests (0.7h) — `test_architecture_module_*_surface.py` validates structure and metadata

### Verification

Run: `make test` with `-m "not slow"` — All contract tests pass.

---

## Phase 5: DVC Pipeline + Reproducibility

**Duration:** ~3h | **Status:** ✅ COMPLETE  
**Quality Gate:** `dvc.yaml` defines all module pipelines; `dvc repro --dry` runs with no errors; `.dvc/` locked  
**Dependencies:** Phase 4

### Deliverables

- **T5-1:** DVC.yaml pipeline definition (1.5h) — Three stages (module_a, module_b, module_c) with cmd, deps, outs, metrics
- **T5-2:** DVC reproducibility test (0.75h) — `test_dvc_pipeline_config.py` validates stage structure
- **T5-3:** Reproducibility documentation (0.75h) — `tests/REPRODUCIBILITY.md` records 9 MD5 hashes

### Verification

Run: `dvc repro --dry` — All stages verified; `dvc.lock` consistent.

---

## Phase 6: Tier 3 Components

**Duration:** ~11h | **Status:** ✅ COMPLETE  
**Quality Gate:** All Tier 3 artifacts present; 60+ new tests pass; acceptance criteria met per task  
**Dependencies:** Phase 5

### Deliverables

- **T6-1:** TSP/VRP routing (4h) — `tsp_router.py` nearest-neighbor + 2-opt; `routing_schedules.parquet` 18 depts × 14 weeks × 3 scenarios; 8 tests
- **T6-2:** Monte Carlo engine full spec (3h) — `monte_carlo.py` stratified draws across 3 canonical buckets with LogNormal prior synthesis; 7 tests
- **T6-3:** Battleground heatmap (2h) — `battleground_probability_heatmap.geojson` with polygon geometries; `px.choropleth` in post_mortem.qmd; 6 tests
- **T6-4:** MILP bundle constraints (2h) — Binary `z[bundle_id]` linking; `bundle_min_spend` floor enforcement; 5 tests

### Verification

Run: `make module-c-all` — All outputs present; 61 Module C tests pass; Module B 221 tests pass.

---

## Phase 7: Documentation Completeness

**Duration:** 6h | **Status:** 🔄 IN PROGRESS (T7-1, T7-2 active)  
**Quality Gate:** Gate 11 — All 5 docs complete; `verify_doc_code_paths.py` no missing fields  
**Dependencies:** Phase 6

### Deliverables

- **T7-1:** IMPLEMENTATION_PLAN.md (1h) — THIS FILE; 9 phases, status, effort, gates per phase
- **T7-2:** Data dictionary completion (2h) — Module B/C columns added; 100% schema coverage
- **T7-3:** Decision log completion (1.5h) — 8+ named decisions with all 5 fields per entry
- **T7-4:** Epistemic boundaries (1h) — 400+ words; all 8 output artifacts; evidence column per row
- **T7-5:** Baseline comparison (0.5h) — Module A/B/C vs naive; improvement deltas shown

### Verification

Run: `poetry run python scripts/verify_doc_code_paths.py` — Zero missing fields.

---

## Phase 8: Pyright Strict Mode + Docker Smoke Test

**Duration:** ~8.5h | **Status:** ⏳ PLANNED  
**Quality Gate:** Gate 7 (Docker builds, tests pass in container); Pyright strict on all src/ (zero errors)  
**Dependencies:** Phase 7

### Deliverables

- **T8-1:** Pyright strict Module A (3h) — Fix `basic` → `strict` errors (narrowing, `object` vs `Any`, return types)
- **T8-2:** Pyright strict Module B (2h) — PuLP/pandas DataFrame overload stubs
- **T8-3:** Pyright strict Module C (2h) — PyMC/ArviZ/xarray type narrowing
- **T8-4:** Docker smoke test CI (1.5h) — `.github/workflows/ci.yml` new job; builds and runs tests in container

### Verification

Run: `make typecheck` — Zero errors; `docker build . && docker run --rm <image> make test` passes.

---

## Phase 9: Statistical Rigor Completion

**Duration:** ~6-7h | **Status:** ⏳ PLANNED  
**Quality Gate:** Gate 5 (statistician can verify all claims); interval coverage, PPC, forecast metrics  
**Dependencies:** Phase 8

### Deliverables

- **T9-1:** Walk-forward validation (2h) — Hold last 2 weeks; fit weeks 1–12; forecast 13–14; Brier, log loss, interval coverage recorded
- **T9-2:** Posterior predictive checks (2.5h) — Simulate y_rep ~ posterior; compare to observed polls; p-values recorded
- **T9-3:** Interval coverage metrics (1h) — 80% and 95% HDI coverage rates; document assumptions
- **T9-4:** Forecast skill evaluation (1h) — Interval width vs naive prior; calibration curves

### Verification

Run: `MC_FAST=0 make module-c-tracking` then inspect `reports/statistical_metrics_summary.md` — All metrics present with evidence.

---

## Cross-Phase Dependencies

```
Phase 1 (Blockers)
  ↓
Phase 2 (Unit tests) ← requires Phase 1
  ↓
Phase 3 (Linter)    ← requires Phase 2
  ↓
Phase 4 (Architecture) ← requires Phase 3
  ↓
Phase 5 (DVC)       ← requires Phase 4
  ↓
Phase 6 (Tier 3)    ← requires Phase 5
  ↓
Phase 7 (Documentation) ← requires Phase 6 (IN PROGRESS)
  ↓
Phase 8 (Pyright + Docker) ← requires Phase 7
  ↓
Phase 9 (Statistics) ← requires Phase 8
```

---

## Effort Summary

| Phases | Effort | Cumulative | Status |
|---|---|---|---|
| 1–6 (Delivery tiers 1–3) | 28.25h | 28.25h | ✅ COMPLETE |
| 7 (Documentation) | 6h | 34.25h | 🔄 IN PROGRESS |
| 8 (Engineering hardening) | 8.5h | 42.75h | ⏳ PLANNED |
| 9 (Statistical rigor) | 6-7h | ~49h | ⏳ PLANNED |

---

## Gate Status

| Gate | Title | Phase | Status |
|---|---|---|---|
| **2** | Linter clean | 3 | ✅ |
| **4** | Pyright basic type checks | 1 | ✅ |
| **5** | Statistician verification | 9 | ⏳ |
| **7** | Docker smoke test | 8 | ⏳ |
| **9** | CI pipeline green | 1 | ✅ |
| **10** | All tests pass | 2 | ✅ |
| **11** | Documentation complete | 7 | 🔄 |
| **13** | DVC reproducibility | 5 | ✅ |

---

## Notes

- **Scope reference:** Original spec `scope_master_reconstruction_project.md` v3 defines 3 Tiers × 3 Modules × 13 Gates.
- **Portfolio artifacts:** Tier 3 (Phase 6) outputs feed deployment artifacts for §8 (Hiring Signal) and §10 (Portfolio Differentiation).
- **Reproducibility:** `dvc repro --dry` confirms all pipeline stages; `dvc.lock` captures immutable artifact graph.
- **Quality assurance:** 771 unit tests across all modules; 100% schema contract validation; linter green on all src/ and test files.
