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
