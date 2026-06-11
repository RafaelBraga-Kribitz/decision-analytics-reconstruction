# Module B — Resource Allocation Engine

Constrained linear/integer program (PuLP + CBC) allocating a multi-week budget across **18 geographic departments × 11 media channels**, maximizing persuasion-adjusted contact volume subject to reach caps, FX corridors, and municipality coverage constraints.

**Scale:** 2,772 decision variables (18 × 11 × 14 weeks).
**Budget envelope:** $6M USD reconstruction (from verified $44M BCP 2018Q1 operational record).
**FX model:** BCP Jan–Apr 2018 corridor (bid/ask spread parameterized).

## Quick start

```bash
# Run baseline allocation (resolves in < 2s on CBC)
poetry run python -m module_b_resource_allocation.cli \
    --scenario baseline --seed 20180422 \
    --out-dir data/processed/module_b

# Or via Make
make module-b-allocate

# Run all scenarios + sensitivity CSVs
make module-b-allocate-sensitivity

# Start FastAPI service locally
make module-b-api
# → http://localhost:8000/docs
```

## Live API

Module B ships as a FastAPI service. Run it locally:

```bash
make module-b-api   # docs at http://127.0.0.1:8088/docs, health at /healthz
```

A hosted deployment is tracked as open finding `F-021` and will be linked
here once it is verifiably live.

## Source surface

| Path | Purpose |
|------|---------|
| `src/module_b_resource_allocation/models/` | MILP build + solve (`build_problem`, `solve`) |
| `src/module_b_resource_allocation/api/` | FastAPI service (scenarios, counterfactuals, FX, routing) |
| `src/module_b_resource_allocation/fx/` | Jan–Apr 2018 BCP FX corridor model |
| `src/module_b_resource_allocation/routing/` | TSP nearest-neighbor + 2-opt across 18 depts × 3 weather scenarios |
| `src/module_b_resource_allocation/reporting/` | Scenario comparison CSVs + benchmark reports |
| `src/module_b_resource_allocation/counterfactual/` | Broadcast-to-direct shift analysis |
| `src/module_b_resource_allocation/bundle_definitions.py` | 11-channel bundle specs |
| `src/module_b_resource_allocation/constants.py` | Reach caps, budget envelope, FX params |

## Scenarios

| Scenario ID | Description |
|-------------|-------------|
| `baseline` | Uniform 14-week calendar, unconstrained routing |
| `early_lock` | Spend committed in weeks 1–6 before preference-proxy update |
| `late_flex` | Budget held back until week 8; rapid deployment |
| `broadcast_to_direct` | Counterfactual: shift x% from broadcast to direct channels |

## Optimization formulation

Maximize:
```
Σ_{d,c,w} persuasion_weight[c] × reach_efficiency[d,c] × allocation[d,c,w]
```
subject to:
- Weekly budget constraint per department
- Channel reach caps (% of department population)
- FX corridor feasibility (import-channel costs in PYG)
- Bundle binary linking (all channels in a bundle activate together or not)
- Municipality coverage floor (≥ N municipalities per dept per week)

See [`SPECIFICATION.md`](SPECIFICATION.md) and [`../reports/module_b_optimization_formulation.md`](../reports/module_b_optimization_formulation.md) for full LP formulation and shadow-price extraction.

## Tests and CI

```bash
poetry run pytest module_b_resource_allocation/tests/ -v
```

Coverage measured per-module; CI gate at 70% (ratchet to 80% in progress — see `ROADMAP.md`).

## Status

Analytically complete. API serving on Railway. Cloud Run infrastructure wired but not yet provisioned (see `ROADMAP.md` § Deployment milestones).

## Docs

- [`SPECIFICATION.md`](SPECIFICATION.md) — math + solver configuration
- [`../reports/module_b_optimization_formulation.md`](../reports/module_b_optimization_formulation.md) — LP formulation detail
- [`../reports/module_b_module_c_handshake.md`](../reports/module_b_module_c_handshake.md) — cross-module contract (parquet handshake)
- [`../reports/business_case.md`](../reports/business_case.md) — CFO-facing ROI narrative
