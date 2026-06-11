
# Case Study — Decision Analytics Reconstruction

Practitioner reconstruction of a national-scale program analytics stack: population
modeling (Module A), constrained resource allocation (Module B), and probabilistic
scenario analysis (Module C). **Canonical numbers:** see
[`NUMERIC_SSOT.md`](NUMERIC_SSOT.md).

---

## Business framing

**Setting.** A time-constrained program targeted a national eligible population
(**4,260,816** entities at full electoral-roll scale; **50,000** in the default
production reconstruction run) to influence a verifiable binary outcome on a fixed
date.

**Constraints.**

- **18-week** program scope; reconstruction pipeline models **weeks 1–14** (2018-W01–W14) where operational data exists
- **$6M USD** solver envelope (sole budget figure in portfolio narrative)
- 18 geographic units, 11 reach channels, four fixture survey measurement sources

**Verified outcome (TSJE, Series A):** **+3.70 pp** margin (46.43% vs 42.73%);
national participation rate **61.25%**.

We do **not** claim a causal counterfactual ("analytics added X pp"). The
reconstruction demonstrates how segmentation, optimization, and forecasting
*could* support decisions under those constraints; the +3.70 pp anchor is the
public ground truth, not an A/B lift estimate.

---

## System 1 — Population segmentation (Module A)

Six operationally labeled segments from DBSCAN pre-pass + K-Means (k=6) on
synthetic features calibrated to TSJE/DGEEC marginals.

**Enforced CI gates:** silhouette **> 0.22** (measured ~0.2566); bootstrap ARI
**> 0.70** (measured ~0.7615). Legacy aspirational gates (0.35 / 0.80) are retired.

**Propensity model:** Platt-calibrated logistic regression with department raking
to participation anchors. **Brier 0.071** vs gate **< 0.237**. Reported **AUC
0.9679 is circular** (target shares calibration anchors with features) — see model
card; do not headline AUC as generalization.

---

## System 2 — Resource allocation (Module B)

MILP over **2,772** rows (18 × 11 × 14) maximizing linearized
persuasion-adjusted contacts under budget, reach-cap, FX corridor, and **80%**
coverage floor constraints. Solver status **OPTIMAL** on baseline scenario.

**Solver comparator (provable):** MILP vs department-uniform naive baseline yields
**~54.8%** more linearized persuasion-proxy contacts on the $6M envelope
(`run_manifest_baseline.json`; golden metric `linearized_lift_pct_milp_vs_naive`).
Framed as reconstruction-envelope optimization — not verified 2018 causal lift.

Department "calibration" in Module A is **post-hoc raking** to verified rates — it
validates aggregate alignment, not predictive skill on withheld microdata.

---

## System 3 — Probistic forecasting (Module C)

Bayesian hierarchical tracking (Gaussian random walk + pollster house effects) and
stratified Monte Carlo shock scenarios (**10,000** draws default). Posterior
margins on sparse fixtures are **wide and prior-dominated** — they illustrate
uncertainty machinery, not a tight election-eve point forecast. Always pair model
outputs with the verified **+3.70 pp** anchor.

**Diagnostics (honest):** full NUTS runs may show **14 divergences** and R̂>1.01 on
some parameters; these are tracked remediation items, not hidden blockers.

---

## Technical stack (summary)

| Module | Core outputs | Contract |
|---|---|---|
| A | `population_master_clean.parquet`, segments, propensity | `schema_contracts/participation_propensity.yaml` |
| B | `allocation_baseline.parquet`, routing | `schema_contracts/allocation_output.yaml` |
| C | `daily_posterior_forecast.parquet`, MC draws | wired via `--allocation-parquet` (F-040) |

Run full chain: `make pipeline-full`. Golden metrics: `reports/golden_metrics.json`.

---

## Domain transfer (illustrative)

Methods transfer to territory planning, SKU allocation, and churn programs when
the same structure applies: heterogeneous units, constrained budgets, noisy
signals, single outcome event. Scale numbers above are reconstruction-specific;
swap entity definitions and anchors for other domains.

*See `ARCHITECTURE.md`, module READMEs, and `epistemic_boundaries.md` for artifact
status (verified / calibrated / simulated / illustrative).*
