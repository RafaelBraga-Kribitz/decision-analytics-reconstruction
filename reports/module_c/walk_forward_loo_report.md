# Module C — Leave-One-Wave-Out Walk-Forward Report

First **out-of-sample** predictive score on the real Paraguay 2018 poll fixture.
Each row holds out one tracking wave, refits the hierarchical model **without** the
verified outcome anchor (``m_star_pp=None``; see F-069), and scores the held-out poll
against its posterior-predictive distribution.

## Caveats (read before quoting these numbers)

- **Small n:** only **8** tracking waves → **6** holdouts at ``min_train_size=2``.
- **Wide intervals expected:** sparse polls + house effects → interval coverage is a structural diagnostic, not evidence of calibration.
- **No power:** coverage is quoted as k/n with its exact binomial 95% CI; with n=6 that CI spans most of [0, 1], so this check cannot distinguish a calibrated model from a badly miscalibrated one.
- **Regeneration mode:** this committed artifact was produced with full NUTS, ``MC_FAST`` unset (4 chains x 1000 draws, 1000 tune, target_accept=0.99, seed=42, max_treedepth=15).

## Aggregate metrics

| Metric | Value | Interpretation |
|---|---:|---|
| Brier score (sign task) | 0.3225 | P(margin>0) vs observed sign |
| Log loss | 1.1184 | Same task, log score |
| 80% interval coverage | 3/6 = 50% [0.12, 0.88] | Holdouts inside 80% HDI [exact binomial 95% CI] |
| 95% interval coverage | 4/6 = 67% [0.22, 0.96] | Holdouts inside 95% HDI [exact binomial 95% CI] |

## Per-holdout detail

| Holdout wave | Date | Observed margin (pp) | Predictive mean (pp) | 95% HDI (pp) | In 95% HDI |
|---|---|---:|---:|---|---|
| `wave_ati_20180315` | 2018-03-15 | -4.50 | 20.27 | [-3.2, 44.7] | no |
| `wave_ica_20180318` | 2018-03-18 | 31.40 | 3.97 | [-14.9, 22.7] | no |
| `wave_ecodat_20180326` | 2018-03-26 | 26.43 | 14.68 | [-7.6, 34.6] | yes |
| `wave_capli_20180406` | 2018-04-06 | 31.50 | 21.53 | [-4.1, 46.3] | yes |
| `wave_grau_20180410` | 2018-04-10 | 25.11 | 22.75 | [0.5, 44.2] | yes |
| `wave_ati_20180418` | 2018-04-18 | -5.12 | 17.18 | [-5.9, 38.3] | yes |

## MCMC diagnostics per fold

Gates: R-hat <= 1.01, ESS bulk >= 400, ESS tail >= 400, divergences <= 0 (``DIAGNOSTIC_GATES`` in the tracking model).

| Fold (train size) | Holdout wave | R-hat max | ESS bulk min | ESS tail min | Divergences | Treedepth hits | Gates |
|---:|---|---:|---:|---:|---:|---:|---|
| 2 | `wave_ati_20180315` | 1.005 | 1809 | 613 | 0 | 0 | pass |
| 3 | `wave_ica_20180318` | 1.007 | 2259 | 2007 | 0 | 0 | pass |
| 4 | `wave_ecodat_20180326` | 1.008 | 1983 | 1530 | 0 | 0 | pass |
| 5 | `wave_capli_20180406` | 1.005 | 1391 | 1531 | 0 | 0 | pass |
| 6 | `wave_grau_20180410` | 1.004 | 1442 | 1187 | 0 | 0 | pass |
| 7 | `wave_ati_20180418` | 1.004 | 1099 | 1046 | 0 | 0 | pass |

## How to regenerate

```bash
# Publication-grade full NUTS (do not set MC_FAST, not even to 0):
poetry run python scripts/generate_walk_forward_loo_report.py --full
# CI-friendly fast path:
poetry run python scripts/generate_walk_forward_loo_report.py
```

*Generated on 2026-11-04 from ``module_c_forecasting_scenarios/tests/fixtures/polls_raw_fixture.csv``.*
