---
doc_id: DOC-RPT-012
doc_type: methodology
doc_role: derived
visibility: public
status: active
owner: project
last_reviewed: '2026-05-20'
canonical_source:
- DOC-MODB-001
derived_from:
- DOC-MODB-001
supersedes: null
tags: []
allowed_content:
- interpretation
- summarization
forbidden_content:
- novel_metrics
---

# Module B — LP / MILP optimization formulation (portfolio)

Canonical implementation: `module_b_resource_allocation/src/module_b_resource_allocation/models/allocation.py` (`build_problem`, `solve`). Specification context: `module_b_resource_allocation/SPECIFICATION.md` and `module_b_resource_allocation/reports/response_curve_spec.md`.

## Sets and indices

- Departments `d ∈ D` (18), channels `c ∈ C` (11), weeks `w ∈ {1,…,14}` (ISO labels `2018-W01` … `2018-W14`).
- Binary indicators `y[d,c,w] ∈ {0,1}`: channel-week active (bundle and linkage logic).
- Continuous spend `x[d,c,w] ≥ 0` (USD).

## Objective

Maximize **persuasion-adjusted expected contacts**, approximated as a linear expression in `x` using a two-slope diminishing-returns blend per `(d,c)` (inflection share and `k` from reach-cap features). Weekly scenario weights (`baseline` / `early_lock` / `late_flex`) and tier penalties scale coefficients.

## Hard constraints (high level)

1. **Binary linkage:** `x[d,c,w] ≤ max_spend[d,c,w] · y[d,c,w]` with `max_spend = reachable_audience × unit_cost_usd`.
2. **Reach ceiling:** `x[d,c,w] ≤ max_spend[d,c,w]` (hard cap row).
3. **Pay-TV eligibility:** `x = 0` for `tv_spots` outside eligible departments.
4. **Global budget:** `sum_{d,c,w} x[d,c,w] ∈ [(1−ε)B, (1+ε)B]` with `B = CAMPAIGN_BUDGET_USD`, `ε = CAMPAIGN_BUDGET_TOLERANCE`.
5. **Department coverage proxy:** lower bound on contacted mass per department (see code constraint `coverage_{d}`).
6. **Channel bundles:** hard bundle families from `config/channel_bundles.yaml` (equality / cardinality patterns).
7. **Negligible-tier in-person cap:** spend ceiling on in-person channels for `negligible` tier departments.

## Solver and duals

CBC via PuLP. Post-solve, `lp_diagnostics` records `budget_upper` / `budget_lower` shadow prices (`pi`) and the top five `cap_*` reach-cap dual magnitudes (when CBC returns them).

## Sensitivity outputs

`compute_budget_expansion_curve` re-solves at budget multiples `(0.25, 0.5, 0.75, 1.0, 1.5, 2.0) × B`. CSV + JSON manifest entries are emitted when running the allocation CLI with `--sensitivity`.

## Infeasibility

If CBC returns `INFEASIBLE`, the solve status string is `INFEASIBLE` and the allocation frame should not be interpreted as optimal — treat as a constraint-debugging signal (see rubric: INFEASIBLE is a bug for nominal scenario budgets).
