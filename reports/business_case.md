# Business case — resource allocation under uncertainty

This document frames the reconstruction as **operational analytics for a national-scale program**: segmenting an entity-scale **population dataset**, allocating a fixed budget across geographic units and **reach channels** under feasibility caps, and compressing biased **survey measurement** into probabilistic posture for the **preference proxy**. It is deliberately domain-agnostic: the motivating **outcome event** anchors calibration; the transferable product is disciplined decision support ([`reports/case_study_business.md`](case_study_business.md)).

For what is verified vs simulated vs illustrative, see [`reports/epistemic_boundaries.md`](epistemic_boundaries.md).

---

## Executive problem statement

Organizations running large **programs** face three coupled problems:

1. **Population heterogeneity.** Entities differ in participation propensity and channel feasibility; aggregate dashboards hide where spend is persuasive vs wasted.
2. **Constrained budget and time.** Spend must observe caps (reach, tiers, bilateral routing), currency conversion bands, and a finite weekly grid — not Excel “what-if” rows.
3. **Noisy inference.** Measurement firms disagree; decisions still need coherent uncertainty rather than whichever table looked best this week.

The repository shows how segmentation, MILP-backed allocation with shadow-price transparency, and hierarchical Bayesian tracking fit together — with contracts, tests, and reproducible manifests.

---

## Cost structure (reconstruction envelope)

Canonical Module B reconstruction envelope (national grid, fourteen ISO weeks anchored in `WEEK_LABELS`):

| Item | Authoritative constant / artifact |
|------|-------------------------------------|
| Nominal envelope | `CAMPAIGN_BUDGET_USD = 6_000_000.0`, tolerance `±0.5%` — `module_b_resource_allocation/src/module_b_resource_allocation/constants.py` |
| Geographic units | eighteen entries in `DEPARTMENTS` (same module) |
| Reach channels | eleven entries in `CHANNEL_NAMES` |
| Solver seed (example) | `--seed 20180422` (matches examples in `Makefile`) |

Operational **time pressure** matches the sixteen-week-ish grid described in README / architecture; downstream calendars are scenario-tagged (`baseline`, `early_lock`, …).

---

## Baselines and measured improvement

### Definitions

Two baselines accompany every allocation run manifest (`baseline_comparison` in `run_manifest_<scenario>.json`):

1. **Department-uniform naive** — equal USD per geographic unit; within each unit, uniform cap-limited water-fill across feasible channel × week combinations. Uses the **linearized marginal persuasion-per-USD** slopes aligned with the MILP LP objective. **Omits MILP bundle and coverage coupling** (see manifest `definitions` for the explicit caveat).

2. **Cap-water-fill relaxation** — single national pool competing for the same caps; useful transparency, **not guaranteed MILP-feasible** under discrete bundle logic.

### Reproducing numbers

```bash
cd /path/to/repo
make module-b-allocate SEED=20180422
# Inspect: data/processed/module_b/run_manifest_baseline.json → baseline_comparison

make module-b-allocate-sensitivity SEED=20180422
# Adds budget_expansion_curve_baseline.csv, dual exports, allocation_run_baseline.md
```

### Snapshot (scenario `baseline`, seed `20180422`, Manifest `run_id` 2026-05-12 regeneration)

Rounded for readability — **reload from JSON before external citation**:

| Comparator | Spend (USD) | Linearized persuasion proxy | Budget use vs nominal 6 M |
|-------------|-------------|------------------------------|---------------------------|
| Department-uniform naive | ~5.53 M | ~2.019×10⁸ | ~92 % (≈ 0.47 M nominally idle under naive rule) |
| MILP optimized (this run) | ~6.03 M | ~3.195×10⁸ | ~planned envelope within tolerance |

- **Lift (linear MILP projection vs naive):** manifest reports **≈ 58 % higher** Σ(coef × USD) on the MILP spend vector than naive at the naive’s own feasibility pattern.
- **Reported nonlinear total** (`persuasion_adjusted_contacts` summed on CSV rows — diminishing-returns layer): ≈ 2.527×10⁸ for MILP vs naive **not recomputed nonlinearly here** (naive baseline is CFO-transparent on the LP-linearized surrogate that the MILP optimizes internally).

Interpretation hygiene: nonlinear totals are reconstruction outputs; CFO comparisons for “budget efficiency vs naive” should lean on **`linearized_lift_pct_milp_vs_naive` + unspent envelope** (`naive_budget_left_unspent_usd`) until a nonlinear naive is implemented.

---

## Risk and uncertainty — three numeric shocks

Illustrative, reconstruction-internal (see epistemic file for scope):

| Stress | Mechanism illustrated | Numeric read (this repo) |
|--------|-----------------------|----------------------------|
| **Budget −20 % nominal** | MILP rebuild at `0.8 × CAMPAIGN_BUDGET_USD`, seed unchanged | Solver output (one-off invocation, seed 20180422): total nonlinear contacts drops to **229 200 627.9** from **252 721 160.7** at ~1× envelope — roughly **−9.3 %** on summed nonlinear contacts (~**4.824 M** USD booked vs ~**6.030 M** at baseline). Command: build `AllocationProblem(..., budget_usd=6_000_000*0.8)` + `solve`. |
| **FX band** | BCP-aligned corridor enforced in formulation | Corridor parameters `FX_BAND_MAX_PCT_VS_BCP = 0.005`, `CAMPAIGN_BUDGET_TOLERANCE` `0.005` — constants file above. Operational translation: shocks outside modeled FX tiers require new rate tables (`fx_layer_<series>.csv`) before reallocating; manifest duals quantify binding pressure on envelopes when sensitivity CSVs flag it. |
| **Participation rate −10 % (scenario)** | Participation rate enters Module A segmentation / propensity story | No single closed-form national shock is merged into Module B in this reconstruction; directional impact: lowered expected eligible reach lowers effective caps downstream and tightens persuasive headroom — re-run Module A exports before trusting historic Module B parquet inputs. Tie to empirical bounds in [`reports/epistemic_boundaries.md`](epistemic_boundaries.md). |

For systematic budget multipliers shipped with the codebase, open `budget_expansion_curve_baseline.csv` (rows at 0.25–2.0 × nominal target).

---

## Assumptions a peer will challenge

1. **Fixed population-scale synthesis** — N of the calibrated **population dataset** is anchored to external registries named in appendix files; redistribution is illustrative.
2. **Stationary weekly unit economics** except scheduled FX tiers — diminishing-returns breakpoints are parameterized, not market-discovered prices.
3. **Reconstruction, not audited cash** — dollars are plausible magnitudes traced to manifests, not bank reconciliations (see narrative honesty in README “Honest narrative”).

---

## System flow

```mermaid
flowchart LR
    programConstraints[program_constraints]
    popDataset[population_dataset_A]
    allocEngine[allocation_engine_B]
    forecastPosterior[probabilistic_track_C]
    decisions[KPI_dashboards]
    programConstraints --> popDataset
    popDataset --> allocEngine
    allocEngine --> forecastPosterior
    forecastPosterior --> decisions
```

---

## Elevator recap (CFO-ready, 30–45 seconds)

“A national-scale program had to steer several million USD across heterogeneous geographies under hard feasibility rules and noisy polls. Module A organizes entity-level heterogeneity into six operational segments plus participation propensity; Module B allocates the envelope with MILP proofs and publishes shadow-price evidence; Module C summarizes measurement disagreement into probabilistic posterior tracks. Compared with spending the same nominal envelope uniformly by geography—with undifferentiated week-by-channel distribution subject to feasibility caps—a naive benchmark leaves measurable budget idle and forfeits persuasive contact proxy measured on aligned linear slopes (~58 % lift on that proxy versus naive in baseline seed 20180422). Documented sensitivities quantify budget truncation; FX corridors and participation shocks are parameterized with caveats spelled out separately.”

### FAQ pitfalls

| Pitfall | One-sentence response |
|---------|-----------------------|
| “Budget cut 20 % — what disappears first?” | Rerun MILP at the cut envelope (~0.8× reproduced above); persuasive contacts fall ~9 % nonlinear sum in that single reconstruction solve — combine with curve CSV for nonlinear scaling vs multiplier. |
| “Participation rate drops 10 % nationally?” | Synthetic Module A lowers engagement; reach caps tighten before Module B resolves — rerun A→features→B rather than multiplying post-hoc results. |
| “FX leaps outside the modeled band?” | `FX_BAND_MAX_PCT_VS_BCP` encodes permissible deviation; violating rates invalidate current `tc_rate_*` conversions until Treasury inputs refresh dual-feasibility. |

---

## Acceptance criterion

After reading **this file only**, a CFO-level reviewer should be able to explain **why MILP-guided allocation materially exceeds a transparent naive budgeting rule**, how **budget truncation** behaves at a reproducible rerun, where **truth vs simulation** divides, and which **Makefile commands** regenerate the proofs.
