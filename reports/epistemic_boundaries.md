# Epistemic boundaries — reconstruction portfolio

This document classifies **what is verified**, **what is simulated**, and **what is illustrative** so reviewers can align claims with evidence. Wording follows project terminology (entity, population dataset, participation rate, preference proxy, outcome event, survey measurement, program).

| Component | Status | Notes |
|-----------|--------|--------|
| TSJE / DGEEC calibration anchors (department participation rates, roll counts) | Verified external inputs | Used as hard targets or informational checks per `schema_contracts` and model cards. |
| Outcome event margin (program vs alternative) | Verified | Public electoral authority figures referenced in README and appendix. |
| Population dataset structure (departments, channels, weeks) | Structural + partially calibrated | Counts and geography align to anchors; individual-level fields are synthetic. |
| Behavioral relationships (features, flaws, segment separation) | Simulated | Generated under documented priors and QA gates; not causal estimates from micro-behavioral panels. |
| Media reachability and routing costs | Synthetic structural inputs | Derived from Module A segment exports and Module B configuration for operational plausibility. |
| Participation propensity scores | Model output on synthetic population dataset | Calibration gates in CI; not validated on withheld real microdata. |
| Resource allocation LP / MILP | Structural demonstration | Solver outputs are reproducible; objective is a persuasion-adjusted contact proxy, not audited campaign accounting. |
| Preference-proxy tracking model (Module C) | Illustrative on fixture + fast sampler | `MC_FAST` in CI; full NUTS diagnostics in slow tests and `reports/module_c_forecast_validation.md`. |
| Monte Carlo scenario fan | Illustrative | Shock catalog bounds perturbations; not a calibrated tail-risk model for trading. |

**How to use this table:** If a sentence in the README or a model card implies stronger inferential status than the row above, rewrite it to match the row or move detail here.
