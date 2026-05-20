---
doc_id: DOC-RPT-013
doc_type: methodology
doc_role: derived
visibility: public
status: active
owner: project
last_reviewed: '2026-05-20'
canonical_source:
- DOC-MODC-001
derived_from:
- DOC-MODC-001
supersedes: null
tags: []
allowed_content:
- interpretation
- summarization
forbidden_content:
- novel_metrics
---

# Module C — forecast validation and diagnostics

## What CI proves (fast path)

GitHub Actions runs `pytest module_c_forecasting_scenarios/tests -m "not slow"` with `MC_FAST=1`. This exercises:

- Pipeline imports and data contracts on the fixture CSV.
- Tracking hierarchical fit with **reduced** NUTS draws/tune (see `module_c_forecasting_scenarios/config/pymc_sampler.yaml` and env `MC_FAST`).

## What slow tests prove (local or scheduled)

Tests marked `@pytest.mark.slow` call `fit_tracking_hierarchical` with full sampling settings when `MC_FAST` is unset. Evidence checklist:

1. **Sampling completes** — `idata` contains `posterior` groups for `mu_margin`, `house_offset`, etc.
2. **Posterior export** — `export_daily_posterior_table` row count matches the campaign day index built from the fixture and declared `outcome_event_date`.
3. **Convergence** — after full runs, inspect `arviz.summary(idata)` for R-hat and ESS (documented numeric thresholds in `ROADMAP.md`).

## Posterior predictive and prior predictive checks

- **Prior predictive:** run `pm.sample_prior_predictive` in a dedicated slow test or notebook cell; store summary statistics in `data/processed/module_c/` when executing full pipelines (not required for `MC_FAST` CI).
- **Posterior predictive:** extend the hierarchical model with a PPC draw against `obs` where appropriate; for the current Gaussian observation layer on `m_poll_pp`, PPC is emitted in slow diagnostics tests as a mean absolute deviation check on synthetic fixtures.

## Walk-forward note

A strict walk-forward requires dated measurement splits beyond the 10-row synthetic fixture. The reconstruction documents the **intended** walk-forward protocol here: train on `publication_date ≤ t`, score day `t+1`, advance `t`. Operational validation awaits a longer fixture or production-grade poll panel.

## Calibration series gate

Models must declare **one** calibration series per run (`A` or `B`) — never mix numerators across series in a single likelihood (see `reports/decision_log.md` and scope gate).
