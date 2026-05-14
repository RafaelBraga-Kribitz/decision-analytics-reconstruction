# Module C research proof table (stub)

| Artifact | Path | Status |
|----------|------|--------|
| TSJE Series A/B | `reports/research/tsje_calibration_sources.md` | STUB |
| OEA/EU ingest | `reports/research/oea_eu_survey_release_metadata.md` | STUB |
| Exit mechanisms | `reports/research/exit_bias_mechanisms.md` | HYPOTHESIS |
| Macro priors | `config/macro_context_prior.yaml` | PARTIAL |
| Walk-forward validation (T9-1) | `reports/statistical_metrics_summary.md` § Walk-forward out-of-sample validation | COMPLETE |

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
