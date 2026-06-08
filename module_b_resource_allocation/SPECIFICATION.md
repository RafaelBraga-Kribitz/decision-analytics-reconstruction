# Module B — Allocation LP and sensitivity analysis (specification)

This document is the **implementation-facing** specification for the resource allocation layer. It complements the narrative in [`reports/response_curve_spec.md`](reports/response_curve_spec.md), which contrasts this LP with a full media mix model.

## Implementation map

- **Canonical MILP:** [`src/module_b_resource_allocation/models/allocation.py`](src/module_b_resource_allocation/models/allocation.py) (`build_problem`, `solve`).
- **Legacy CLI / dict API:** [`src/module_b_resource_allocation/models/allocation_lp.py`](src/module_b_resource_allocation/models/allocation_lp.py) (`run_allocation`).
- **Diminishing returns / reach caps:** [`src/module_b_resource_allocation/features/diminishing_returns.py`](src/module_b_resource_allocation/features/diminishing_returns.py) and [`features/reach_caps.py`](src/module_b_resource_allocation/features/reach_caps.py).

## Decision variables (conceptual)

- `x[d,c,w]`: nonnegative spend (USD) in geographic unit `d`, channel `c`, ISO week `w`.
- `y[b] ∈ {0,1}`: bundle / conglomerate activation indicators where the formulation uses binary linking for minimum bundle floors.

Concrete variable names and index sets match the PuLP problem built in `build_problem` (departments, channels, weeks, FX scenario).

## Objective (high level)

Maximize **persuasion-weighted, cost-normalized contacts** subject to reach ceilings:

- Per-cell objective terms combine **unit cost**, **segment / channel persuasion weights** from Module A outputs, and **remaining reach headroom** so that marginal contacts decline as utilization approaches the cap (LP-linearized saturation; see `response_curve_spec.md`).

## Constraints (high level)

- **Budget:** total spend across all cells and weeks ≤ campaign envelope.
- **Reach caps:** spend translated to contacts cannot exceed population × channel reachability × policy caps.
- **FX / scenario layer:** PYG/USD path and corridor tags select cost coefficients and feasibility (see `fx/` package).
- **Bundle floors:** minimum spend on selected channel bundles when the corresponding activation binary is on.
- **Nonnegativity:** all spend variables ≥ 0.

## Mandatory sensitivity analysis outputs (OR practice)

Once a baseline optimal solution exists, every **scenario report** should include:

1. **Budget constraint shadow price** — interpret as approximate marginal value of an extra dollar of spend at the optimum (dual on the global budget row), stated in the same units as the objective (contacts or scaled objective).
2. **Binding reach-cap duals** — for the top five binding caps, report which `(department, channel)` pairs are bottlenecked and the shadow price sign/magnitude bucket (low / medium / high) to avoid false precision when CBC duals are noisy.
3. **Budget expansion curve** — tabulate optimal objective value (or total contacts) at budget multiples {0.25, 0.50, 0.75, 1.00, 1.50, 2.00} × baseline envelope to show diminishing returns from saturation and caps.
4. **Scenario comparison table** — at minimum three FX narrative tags (e.g. early lock, late flex, balanced): columns for total spend, optimal objective, top three geographic units by spend, and list of binding constraint classes.

## Diminishing returns choice

The reconstruction uses **concave, piecewise-linear** upper bounds derived from reach caps rather than a non-concave S-curve, so the problem stays a **mixed-integer linear program** without piecewise-linearization binaries for an inflection point. A Hill or logistic response remains **out of scope** unless reformulated to MILP or solved as a nonlinear program.

## Status

The Python implementation, tests, and API surface **exist** in this repository; this file captures the **OR interpretation layer** and the **sensitivity deliverables** expected in portfolio and stakeholder reviews.
