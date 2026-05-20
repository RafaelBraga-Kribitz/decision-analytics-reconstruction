---
doc_id: DOC-REP-008
doc_type: narrative
doc_role: canonical
visibility: public
status: active
owner: project
last_reviewed: '2026-05-20'
canonical_source: null
derived_from: null
supersedes: null
tags: []
---

# Module B → Module C handshake (allocation and shocks)

Module C consumes **allocation_output** rows from Module B
(`schema_contracts/allocation_output.yaml`) together with Module A
**participation_propensity** and **segment_labels** for strata weights.

## Primary columns for participation elasticity bridges

| Column | Role for Module C |
|--------|-------------------|
| `department` | Geographic stratum for posterior win-probability maps |
| `channel` | Instrument family (broadcast vs bilateral vs in_person) |
| `week_index` / `iso_week` | Aligns with poll field windows and shock timestamps |
| `budget_allocation_usd` | Spend path feeding counterfactual reallocation stress |
| `expected_contacts` / `persuasion_adjusted_contacts` | Scale for demobilisation shock absorption tests |
| `scenario_id` | Baseline vs timing / counterfactual tags |
| `reach_cap_population_proxy` | Denominator for utilisation when mapping shocks to participation |

## Counterfactual artifact

`reallocation_counterfactuals.parquet` (see `schema_contracts/reallocation_counterfactuals.yaml`)
carries **delta_budget_usd** and **delta_contacts** per grid cell for the
`broadcast_to_direct` scenario. Module C Monte Carlo may ingest these deltas as
bounded perturbations on participation priors (hypothesis-level only).

## Calibration series

Module C must read `module_c_forecasting_scenarios/config/calibration.yaml`
(`series: A` or `B`) and **never** mix Series A numerators with Series B
denominators. Enforced in `module_c_forecasting_scenarios/tests/test_calibration_series_gate.py`.
