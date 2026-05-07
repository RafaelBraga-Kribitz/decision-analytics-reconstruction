---
name: project-module-c
description: Probabilistic forecasting, Bayesian aggregation, MCMC, scenarios, Quarto — Module C. Embeds PyMC 8-step canonical workflow, ds-qa 6 layers, series gate block, and convergence gates.
disable-model-invocation: true
---

# Project Module C

## Non-negotiable order of operations

```
1. Preflight:    Series gate declaration → input contract check → prior predictive sanity
2. TDD:          Failing test for posterior shape first → minimal impl → verify green
3. PyMC workflow: 8-step canonical (data → model → prior PPC → sample → diagnostics →
                   posterior PPC → results → compare); NO step may be skipped
4. Debug rule:   4-phase systematic debugging before ANY parameterization change
5. Validate:     C1–C12 gates; BLOCK if any convergence gate fails
6. DS-QA:        All 6 layers; BLOCK if any fails at HIGH stakes
7. Evidence:     ArviZ summary + series gate + tests + gate map + render log + QA report
```

## Required reading
- `project_scope/scope_module_C_forecasting_and_scenario_engine.md`
- `forecasting_scenarios/config/calibration.yaml` (when present)

## Global skills — invoke in this order

1. `pymc` — PyMC 8-step canonical workflow is the authoritative MCMC reference.
2. `test-driven-development` — TDD iron law applies to every `src/` change.
3. `data-science/agents/ds-qa` — run all 6 QA layers before Quarto delivery.
4. `systematic-debugging` — 4 phases before ANY reparameterization or prior change.
5. `verification-before-completion` — gate function before every completion claim.
6. `statistical-analysis` — for non-Bayesian summarization (calibration curves, reliability diagrams).

## Block conditions

- Series gate declaration absent → task does not proceed.
- R-hat ≥ 1.01 on ANY variable → do not deliver.
- ESS < 400 → do not deliver.
- Divergences > 0 post-tuning → do not deliver.
- National scenario deviates > 0.5 pp from 61.25% anchor → recalibrate first.
- Quarto render fails → do not mark deliverable complete.
- DS-QA Layer 6 (peer review for national-level) not completed → BLOCK delivery.

## Quantitative acceptance summary

| Metric | Target | Source |
|--------|--------|--------|
| R-hat (all vars) | < 1.01 | PyMC / ArviZ standard |
| ESS_bulk (all vars) | > 400 | PyMC / ArviZ standard |
| ESS_tail (all vars) | > 400 | PyMC / ArviZ standard |
| Divergences (post-tune) | 0 | PyMC standard |
| House-effect SD | < 5 pp | Scope §6.3 |
| National scenario vs anchor | ±0.5 pp of 61.25% | Scope §6.4 |
| Exit measurement HDI coverage | ≥ 90% holdout | Scope §6.5 |
| Posterior PPC max deviation | < 3 pp from calibration data | Scope §6.2 |
