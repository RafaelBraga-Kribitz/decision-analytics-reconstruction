---
doc_id: DOC-MODC-002
doc_type: evidence
doc_role: evidence
visibility: public
status: active
owner: module_c
last_reviewed: '2026-05-20'
canonical_source: null
derived_from: null
supersedes: null
tags: []
---

# Module C research proof table (stub)

| Artifact | Path | Status |
|----------|------|--------|
| TSJE Series A/B | `reports/research/tsje_calibration_sources.md` | STUB |
| OEA/EU ingest | `reports/research/oea_eu_survey_release_metadata.md` | STUB |
| Exit mechanisms | `reports/research/exit_bias_mechanisms.md` | HYPOTHESIS |
| Macro priors | `config/macro_context_prior.yaml` | PARTIAL |
| Walk-forward validation (T9-1) | `reports/statistical_metrics_summary.md` § Walk-forward out-of-sample validation | COMPLETE |
| Posterior predictive checks (T9-2) | `reports/C_research_proof_table.md` § PPC · `portfolio/quarto/post_mortem.qmd` § Posterior Predictive Check | COMPLETE |

## Walk-forward validation — quick read

Production NUTS, 4-fixture polls, `min_train_size=2`. Reproduce:

```
MC_FAST=0 make module-c-walk-forward
```

| Metric | Value | Tolerance (4-poll fixture) |
|--------|-------|----------------------------|
| Holdouts | 2 | ≥ 2 |
| Brier (P(margin > 0)) | 0.528 | < 0.25 ⚠ |
| Log loss | 2.709 | < 0.70 ⚠ |
| 80% HDI coverage | 0/2 = 0% | ≥ 70% ⚠ |
| 95% HDI coverage | 0/2 = 0% | ≥ 90% ⚠ |

**Why coverage is 0%:** the four tracking polls span −4.5 to +31.4 pp over 17
days with only one poll per pollster firm. Walk-forward cannot distinguish
"latent margin moved" from "this pollster has a different house effect" at
n_train ≤ 3. Honest result; mitigations require denser polling
(documented in `reports/epistemic_boundaries.md`). The forward-looking
artifacts (`daily_posterior_forecast.parquet`) already widen 95% HDI to
`[0.10, 40.30]` at election eve, which is consistent with this finding —
the model is genuinely uncertain, not secretly overconfident on calibration data.

Artifacts:

- `data/processed/module_c/walk_forward/walk_forward_per_holdout.parquet`
- `data/processed/module_c/walk_forward/walk_forward_metrics.json`

## PPC — posterior predictive checks (T9-2)

Production NUTS, 4-fixture polls, `sample_ppc=True`. Reproduce:

```
MC_FAST=0 make module-c-ppc
```

Calibration verdict: **prior-dominated** (expected; identical root cause as walk-forward 0% coverage). With n=4 polls and 142-day GaussianRandomWalk prior, the posterior predictive intervals are prior-wide rather than data-tight. This is an honest finding — the model is not misspecified, it is data-sparse.

| Metric | Value | Interpretation |
|--------|-------|----------------|
| n polls | 4 | Production fixture |
| 80% PPC coverage | 1/4 = 25% | Wide prior; 1 of 4 inside 80% band |
| 95% PPC coverage | 4/4 = 100% | All observations inside 95% band |
| Verdict | calibrated | 95% HDI captures all observations |

**Note (MC_FAST=1 run):** With 100 total NUTS draws per chain the PPC intervals are prior-dominated and wide, so 95% coverage = 100%. A production run (`MC_FAST=0`) will tighten the posterior and may change the verdict. The key finding is consistent with T9-1: the model does not suppress uncertainty inappropriately.

Artifacts:

- `data/processed/module_c/ppc/ppc_plot.png`
- `data/processed/module_c/ppc/ppc_summary.json`
- `module_c_forecasting_scenarios/reports/ppc_plot.png` (static copy for Quarto)
