# Module C — Leave-One-Wave-Out Walk-Forward Report

First **out-of-sample** predictive score on the real Paraguay 2018 poll fixture.
Each row holds out one tracking wave, refits the hierarchical model **without** the
verified outcome anchor (``m_star_pp=None``; see F-069), and scores the held-out poll
against its posterior-predictive distribution.

## Caveats (read before quoting these numbers)

- **Small n:** only **8** tracking waves → **6** holdouts at ``min_train_size=2``.
- **Wide intervals expected:** sparse polls + house effects → interval coverage is a structural diagnostic, not proof of calibration.
- **Regeneration mode:** this committed artifact was produced with ``MC_FAST=1``; re-run without ``MC_FAST`` for publication-grade MCMC.

## Aggregate metrics

| Metric | Value | Interpretation |
|---|---:|---|
| Brier score (sign task) | 0.3100 | P(margin>0) vs observed sign |
| Log loss | 1.0237 | Same task, log score |
| 80% interval coverage | 33.3% | Share of holdouts inside 80% HDI |
| 95% interval coverage | 50.0% | Share of holdouts inside 95% HDI |

## Per-holdout detail

| Holdout wave | Date | Observed margin (pp) | Predictive mean (pp) | 95% HDI (pp) | In 95% HDI |
|---|---|---:|---:|---|---|
| `wave_ati_20180315` | 2018-03-15 | -4.50 | 19.40 | [-1.2, 42.9] | no |
| `wave_ica_20180318` | 2018-03-18 | 31.40 | 4.81 | [-13.2, 22.8] | no |
| `wave_ecodat_20180326` | 2018-03-26 | 26.43 | 13.78 | [-2.8, 29.7] | yes |
| `wave_capli_20180406` | 2018-04-06 | 31.50 | 20.70 | [-3.4, 51.9] | yes |
| `wave_grau_20180410` | 2018-04-10 | 25.11 | 23.85 | [6.6, 45.0] | yes |
| `wave_ati_20180418` | 2018-04-18 | -5.12 | 14.82 | [-3.6, 38.4] | no |

## How to regenerate

```bash
MC_FAST=1 poetry run python scripts/generate_walk_forward_loo_report.py
```

*Generated on 2026-07-14 from ``module_c_forecasting_scenarios/tests/fixtures/polls_raw_fixture.csv``.*
