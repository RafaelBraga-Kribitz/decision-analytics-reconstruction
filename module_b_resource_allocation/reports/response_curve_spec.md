# Response Curve Specification — Module B

**Status:** Design specification. Distinguishes the LP allocation model from a full MMM.

---

## What Module B is (and is not)

Module B is a **constrained linear program** — not a Media Mix Model (MMM).

| Dimension | This model (LP) | Full MMM |
|-----------|----------------|---------|
| Response curve shape | Linear (diminishing returns via reach cap) | Saturation + adstock (Hill function or Michaelis-Menten) |
| Carry-over effects | Not modeled | Adstock decay modeled (Weibull or geometric) |
| Cross-channel interactions | Not modeled | Synergy coefficients estimated from historical |
| Data requirement | Population segments + unit costs + reach caps | Historical spend × outcome time series (≥2 years) |
| Optimization target | Maximize persuasion-adjusted contacts | Maximize estimated revenue/KPI lift |
| Solver | CBC LP (PuLP) | Gradient-based (Nevergrad / L-BFGS) |

**Rationale for LP over MMM:** No historical spend-outcome time series existed for the reconstruction. The LP formulation is the appropriate model when the data-generating regime has not been observed over multiple campaigns with varying spend levels. The LP produces a feasible, auditable allocation under hard constraints; an MMM would require fitting saturation curves to data that does not exist.

---

## LP objective function

```
max  Σ_{d,c,w}  x[d,c,w] / unit_cost[d,c]
              × persuasion_weight[segment_affinity(d,c)]
              × (1 - reach_utilisation[d,c,w] / reach_cap[d,c])
```

The `(1 - reach_utilisation / reach_cap)` term implements **linear diminishing returns**: once a channel in a department has reached its population coverage ceiling, additional spend produces zero marginal contacts. This is the LP approximation of the saturation curve — a piecewise linear upper bound on contacts.

---

## Implicit response curve shape

The effective response curve is:

```
contacts(spend) = spend / unit_cost             if spend < cap * unit_cost
contacts(spend) = cap                            if spend >= cap * unit_cost
```

This is a linear ramp followed by a flat ceiling — equivalent to a rectangular saturation curve. It does not model:
- **Adstock:** No carry-over of spend effect from prior weeks. Each week's allocation is independent.
- **Media decay:** Each channel's persuasion weight is treated as constant across weeks.
- **Warm-up:** No ramp-up period for awareness accumulation.

---

## Where adstock would enter (upgrade path)

If historical spend-outcome data becomes available, the LP can be extended to a full MMM by:

1. Replace the linear `contacts` function with an adstock-transformed version:
   ```
   adstock_t = spend_t + λ × adstock_{t-1}
   ```
   where λ ∈ (0, 1) is the channel-specific retention rate.

2. Replace the linear reach term with a Hill saturation function:
   ```
   saturation(adstock) = adstock^α / (adstock^α + K^α)
   ```
   where K is the half-saturation point and α is the shape parameter.

3. Estimate λ, K, α per channel from historical spend-outcome time series using Bayesian inference (PyMC), then feed the posterior mean parameters back into the LP constraints.

This upgrade is a Phase 2 enhancement documented in `ROADMAP.md`.

---

## Sensitivity analysis (post-solver)

The LP solver (CBC via PuLP) produces **shadow prices (dual values)** for each binding constraint. These are the key post-solve artifacts:

| Artifact | Meaning | Module B output |
|----------|---------|-----------------|
| Shadow price — budget envelope | Marginal value of +$1,000 to department budget | `dual_budget_envelope.csv` |
| Shadow price — reach cap | Marginal value of +1% coverage ceiling | `dual_reach_caps.csv` |
| Shadow price — municipality coverage | Cost of the ≥80% municipality constraint | `dual_municipality_coverage.csv` |
| Budget expansion curve | Win-probability delta per additional $10K | `budget_expansion_curve.csv` (linked to Module C) |

These artifacts are produced by `src/module_b_resource_allocation/solver.py` after an OPTIMAL solution. The budget expansion curve requires the Module C linkage (currently unlinked — see `ROADMAP.md` known gap).

**Reference:** Vanderbei (2014) §4.2 on LP duality; PuLP documentation on `constraint.pi` for accessing dual variables from CBC.
