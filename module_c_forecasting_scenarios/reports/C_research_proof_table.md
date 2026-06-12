# Module C — Research proof table

Evidence trail for Bayesian tracking, exit bias, and scenario inference. This
document is the canonical **evidence** artifact (`DOC-MODC-002`) cited by the
Module C architecture surface test and portfolio registry.

## Estimand and calibration

| Claim | Proof artifact | Gate |
|-------|----------------|------|
| Series A/B anchors never mixed | `config/calibration.yaml` + `data/contract_validate.py` | F-034 estimand gates |
| Outcome anchor m★ wired post-likelihood | `models/tracking/hierarchical.py` | F-036 outcome anchor test |
| Posterior predictive scoring (not latent-only) | `validation/walk_forward.py` | `test_walk_forward_runs_and_reports_metrics` |

## Walk-forward validation (tracking)

Hold out final waves; score against posterior predictive margin with house
effect and survey noise. Synthetic fixture (`MC_FAST=1`) must report Brier ≥
0, log loss ≥ 0, and 95% interval coverage ≥ 2/3 on three holdouts.

Reproduce: `MC_FAST=1 poetry run pytest module_c_forecasting_scenarios/tests/test_walk_forward.py -q`

## MCMC diagnostics (aspirational)

Full NUTS runs export R̂ and ESS in pipeline artifacts. **Aspirational** —
not a merge gate while `MC_FAST=1` is the default CI path. See Module C README
and `reports/VALIDATION.md` for disclosure.

## Monte Carlo scenarios

Stratified draws ingest Module B allocation when present; silent-zero contacts
are rejected. Proof: `scenarios/monte_carlo.py` + `tests/test_monte_carlo_stratified.py`.

## Portfolio outputs

- `portfolio/quarto/post_mortem.qmd` — narrative post-mortem
- `METHODOLOGY.md` — generative model specification
- `reports/ppc_plot.png` — posterior predictive check figure (when generated)
