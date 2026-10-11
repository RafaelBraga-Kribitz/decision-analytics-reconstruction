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

## MCMC diagnostics (enforced merge gate)

Full-NUTS R̂ ≤ 1.01, bulk/tail ESS ≥ 400, zero divergences, and seed-42
posterior stability are hard assertions in
`module_c_forecasting_scenarios/tests/test_mcmc_diagnostics_summary.py`. The
`module-c-slow-nuts` job in `.github/workflows/ci.yml` runs them, with the
rest of the Module C `slow` suite, on every PR with `MC_FAST` unset, so a
convergence regression fails the build. The fast
lane (`MC_FAST=1`) skips them.

Reproduce: `poetry run pytest module_c_forecasting_scenarios/tests/test_mcmc_diagnostics_summary.py -m slow`

## Monte Carlo scenarios

Stratified draws ingest Module B allocation when present; silent-zero contacts
are rejected. Proof: `module_c_forecasting_scenarios/src/module_c_forecasting_scenarios/scenarios/monte_carlo.py` + `module_c_forecasting_scenarios/tests/test_monte_carlo_stratified.py`.

## Portfolio outputs

- `portfolio/quarto/post_mortem.qmd` — narrative post-mortem
- `METHODOLOGY.md` — generative model specification
- `reports/ppc_plot.png` — posterior predictive check figure (when generated)
