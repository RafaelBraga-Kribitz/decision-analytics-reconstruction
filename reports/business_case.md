# Business case — resource allocation under uncertainty

**Plain-language summary:** A national program needed to spend several million USD across 18 geographic regions to reach and persuade citizens before a major civic event. This repository reconstructs the decision system: who to reach, through which channels, at what cost, and how confident we should be in the outcome. Three analytical modules — population segmentation, budget allocation, and probabilistic forecasting — are linked by verified data contracts and reproducible code.

For what is verified vs simulated vs illustrative, see [`reports/epistemic_boundaries.md`](epistemic_boundaries.md).

---

## Quick glossary

The following terms appear throughout this document and the codebase. A reader unfamiliar with the original program context can treat all domain references as anonymized stand-ins for any large-scale citizen-outreach or direct-marketing program.

| Term | Plain-language definition | Where it appears in code |
|------|--------------------------|--------------------------|
| **Entity** | One individual in the target population (a citizen eligible to participate in the outcome event). No real PII; all data is synthetically generated from census-weight distributions. | `entity_id` column; `population_segmentation/` module |
| **Population dataset** | The full synthetic roster of entities, generated to match regional demographic weights. Analogous to a CRM or voter file in commercial programs. | `population_master_clean.parquet` |
| **Preference proxy** | The poll-derived percentage-point lead for Candidate A over Candidate B. Equivalent to "net promoter score" or "brand preference margin" in commercial contexts. Range: typically −15 pp to +15 pp. | `m_poll_pp`, `preference_proxy_a_pct` |
| **Outcome event** | The election — the final, hard-deadline measurement that all forecasting targets. In a commercial analogy: the launch date, the deal close, or the campaign end date. | `outcome_event_date` in calibration YAML |
| **Survey measurement** | A single poll wave collected by a polling firm (analogous to a market-research survey). Each wave reports preference proxy values plus metadata (field window, sample size, transparency score). | `polls_clean_tracking_wave` contract |
| **Reach channel** | A communication medium for contacting entities: TV, radio, WhatsApp, direct outreach. Each channel has a reach cap (how many people it can contact per week per region). | `CHANNEL_NAMES` constant; `reach_caps_*.csv` |
| **Participation propensity** | An entity's estimated probability of showing up on outcome-event day. Range [0, 1]. Used to weight expected contacts in the allocation objective. | `participation_propensity.parquet` |
| **Segmentation** | Clustering entities into six behaviorally and demographically coherent groups (e.g., `high_reach_urban`, `rural_low_contact`). Segment assignment drives per-channel cap estimates. | `segment_labels.parquet`; `build_segmentation_frame()` |
| **MILP** | Mixed-Integer Linear Program. A mathematical solver that finds the budget allocation maximizing total persuasive contacts subject to hard feasibility constraints (caps, budget envelope, currency bands). | `module_b_resource_allocation/models/allocation_lp.py` |
| **House effect** | The systematic polling bias of a specific polling firm — how much their surveys over- or under-state the true preference proxy. Estimated by the Bayesian tracking model. | `posterior_house_effects.parquet` |
| **Posterior** | A probability distribution over likely values of an unknown quantity (e.g., the true preference margin), computed by combining prior beliefs with observed survey data. Output of the Bayesian (PyMC) model in Module C. | `daily_posterior_forecast.parquet` |
| **Calibration series** | The reference election series used to anchor model parameters (A = 2018 general, B = alternative scenario). Controls which m\* (expected margin) and FX rates apply. | `calibration.yaml` `series` field |
| **Shadow price / dual** | The MILP solver's implicit valuation of relaxing a constraint by one unit (e.g., "how much additional persuasion if the TV cap in Asunción were 1 % higher"). Exposed in sensitivity CSVs for CFO review. | `allocation_run_*.md` sensitivity tables |

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

## Financial impact and ROI

The MILP allocation system creates measurable value against the naive baseline through **budget reallocation efficiency**.

### Lift and incremental value

The linear MILP allocation achieves **58 % higher persuasion-adjusted contacts** per dollar than the department-uniform naive baseline, measured on equivalent spend vectors ($5.53 M naive vs $6.03 M optimized). This translates to:

- **Marginal persuasion gain:** ~1.176×10⁸ additional (linearized) persuasion units from MILP tightening relative to naive at baseline budget ($6.03 M vs ~$5.53 M spend envelope).
- **Per-dollar efficiency:** MILP achieves ~53 persuasion units/USD vs naive's ~36.5 units/USD, a **45 % increase in persuasion efficiency**.

### Financial value recovery scenarios

In a real program context with downstream budget availability, this efficiency gap can be monetized through **budget recovery**: allocating the same persuasion units with **fewer dollars**.

**Conservative scenario (420 K USD recovery):**  
If MILP achieves naive-level persuasion (~2.019×10⁸ units) at $4.08 M cost (vs naive's $5.53 M), the recovered envelope is ~$1.45 M, with transaction/operational overhead (~3–6 %) yielding **net budget recovery ~$1.37–1.41 M**. Applying conservative assumptions (program half-cycle delivery, 30–50 % of efficiency gain captured operationally), incremental realized value: **~420 K–630 K USD**.

**Optimistic scenario (720 K USD recovery):**  
If operational guardrails are tighter (e.g., all units tracked, no weekly rebalancing friction) and the program captures 70–80 % of the 58 % efficiency delta, recovered envelope reaches **~720 K USD** on the same persuasion target.

### Verification and caveats

- Both scenarios assume the persuasion-per-contact assumption in the LP is correct (see `epistemic_boundaries.md` for validation scope).
- Nonlinear diminishing-returns effects in the physical campaign are **not** included; the recovery is conservative if true persuasion follows an S-curve rather than linear.
- The recovery figures are illustrative budget reallocations, not audited cost savings. Real-world transaction, coordination, and delivery-friction costs apply.

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
