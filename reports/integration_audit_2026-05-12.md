---
doc_id: DOC-REP-007
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

# Integration audit — portfolio 360° hardening (2026-05-12)

## Scope

Cross-module surfaces touched: Module B `reporting/` package, allocation CLI `--sensitivity`, `schema_contracts` consumption unchanged, CI workflow (Module B job), root `Makefile`, portfolio scripts, documentation under `reports/`.

## Upstream / downstream

| Producer | Artifact | Consumer |
|----------|----------|----------|
| Module A export | segment / propensity / clean population | Module B `build_allocation_features` |
| Module B solve | allocation CSV / manifest | Module C scenario perturbations (handshake) |
| Module C pipelines | posterior tables / HTML | Quarto / reports |

## Contract decisions

- No column renames in `schema_contracts/*.yaml` in this change set.
- Dual CSV filenames are **new** outputs under `data/processed/module_b/` only (not schema version bumps).

## Residual risks

- CBC dual availability varies by build; reach-cap dual CSV may be sparse.
- Module C walk-forward remains fixture-limited until a longer panel is added.

## Sign-off

Prepared as part of the integration-impact checklist (`reports/decision_log.md` entry 2026-05-12 — Portfolio 360° hardening).

---

## 2026-05-12 — Makefile `pipeline-dev` → Module A `run_export`

**Scope:** Root [`Makefile`](../Makefile) `pipeline-dev` now delegates to `python -m population_segmentation.pipeline` (same `run_export` path as `module-a-export`). Downstream unchanged: Module B still consumes `data/processed/` contract filenames.

**Residual:** Interim `data/interim/population_master_*.parquet` from the old three-step dev recipe are no longer refreshed by `pipeline-dev` alone; use `generate-dev` or a full export when those files are needed for debugging.
