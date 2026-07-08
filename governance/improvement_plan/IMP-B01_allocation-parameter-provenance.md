---
id: IMP-B01
title: "Allocation parameter provenance: persuasion weights and diminishing-returns curves"
absorbs: [B1, B2, B4]
overlaps_triage: [AUD-B1, AUD-B2, AUD-B4, AUD-B6]
priority: P1
effort: high
depends_on: []
soft_depends_on: [IMP-B02]
queue: issues
target_repo: decision-analytics-reconstruction
issue: 57
status: filed
---

# IMP-B01 — Allocation Parameter Provenance

Module B's MILP objective is a chord interpolant of `_expected_contacts`
multiplied by six coefficients per (department, channel, week) cell —
`attention_multiplier`, `salience_multiplier`, `network_hostility`,
`_scenario_week_weight`, `_tier_penalty`, `_propensity_weight`
(`models/allocation.py:368`, restated for the post-solve report at
`models/allocation.py:646`). Three of the six trace to an anchored,
documented source (`constants.py:90-93`: "Anchored persuasion stack (plan
§4.4): psi_radio = 0.2148 ... Channels without a measured anchor carry the
neutral 1.0"). The other two hand-picked multipliers do not follow that
discipline:

- `_tier_penalty` (`models/allocation.py:258-259`) assigns
  `{stronghold: 1.00, swing: 1.10, opposition: 0.85, negligible: 0.55}` with
  no citation, no calibration data, and no sensitivity test — a 45-point
  swing in persuasion value between `opposition` and `swing` departments
  driven by a constant that could as easily have been `{1.0, 1.0, 1.0, 1.0}`.
- `_scenario_week_weight` (`models/allocation.py:249-255`) assigns
  `1.15`/`0.95` (`early_lock`) and `0.92`/`1.20` (`late_flex`) per-week
  multipliers with the same absence of derivation.

Underneath both, `features/diminishing_returns.py:33-73` hard-codes 33
floats (11 channels × `_SAT_SHARE`, `_INFLECTION_PCT`, `_K_SHAPE`) that shape
the concave reach-saturation curve every LP cell optimizes against — again
with no calibration source or directional test.

`reporting/budget_sensitivity.py:11-81` already sweeps the one input that
*is* well-governed (`BUDGET_EXPANSION_MULTIPLIERS = (0.25, 0.5, 0.75, 1.0,
1.5, 2.0)`, matched against duals surfaced by `_build_lp_diagnostics` at
`models/allocation.py:559-574`). It does not sweep `_tier_penalty`,
`_scenario_week_weight`, the diminishing-returns shape parameters, or
`COVERAGE_LOWER_BOUND_PCT` (`constants.py:144`, `0.80`). The sensitivity
report therefore validates LP *mechanics* (budget monotonicity) but says
nothing about how sensitive the recommended allocation is to the coefficients
someone invented.

## 1. Define the Scope (The Data Guardrails)

**In-Scope:**
- `_scenario_week_weight` and `_tier_penalty` (`models/allocation.py:249-259`)
  and their two call sites (`:368` objective assembly, `:646` post-solve row
  reconstruction — both must stay identical, per the existing objective-identity
  test).
- `_SAT_SHARE`, `_INFLECTION_PCT`, `_K_SHAPE` (`features/diminishing_returns.py:33-73`)
  and `build_dr_params` (`:83-120`).
- A new provenance manifest (e.g. `config/allocation_parameter_provenance.yaml`)
  that lists every objective coefficient family, its current value(s), and a
  `provenance` tag drawn from the existing `VALID_PROVENANCE` enum
  (`constants.py:161`: `VERIFIED | PRIOR | ESTIMATED`) plus a fourth value
  `NEUTRAL` for the documented "carries 1.0" fallback already used by
  `constants.py:95-105`.
- A mandatory parameter-sensitivity sweep (tornado/perturbation style) that
  extends `reporting/budget_sensitivity.py`'s pattern to `_tier_penalty`,
  `_scenario_week_weight`, `k_shape`/`inflection_pct`, and
  `COVERAGE_LOWER_BOUND_PCT`, published as an artifact alongside every
  allocation run.
- Acceptance thresholds for allocation stability under ±X% perturbation of
  each unverified coefficient family.

**Out-of-Scope:**
- Sourcing real calibration data for `_tier_penalty` or the DR shape
  parameters (a data-collection effort, not a code change); this IMP defines
  the disclosure and sensitivity gate that makes the *absence* of that data
  visible, and mandates the neutral-1.0 fallback (per the `constants.py:90-93`
  precedent) wherever no source exists.
- Module A → Module B uncertainty propagation (`IMP-B02`).
- MILP degenerate-case handling and the `week_index` contract bound
  (`IMP-B03`).
- Silent-drop / silent-substitution behavior in the data-cleaning layer
  (`IMP-B04`).

## 2. Data-Driven "Given-When-Then" Scenarios

**Scenario: Provenance manifest covers every objective coefficient (Happy Path)**
- **Given** `config/allocation_parameter_provenance.yaml` lists an entry for
  each of `_tier_penalty`'s four tier values, `_scenario_week_weight`'s two
  scenario curves, and each of the 11 `(k_shape, inflection_pct, sat_share)`
  channel triples from `features/diminishing_returns.py`,
- **When** a static provenance-completeness check runs (part of `make verify`),
- **Then** it exits 0 and reports 100% coefficient coverage — no
  objective-affecting constant used by `models/allocation.py` or
  `features/diminishing_returns.py` is absent from the manifest.

**Scenario: Parameter-sensitivity sweep published with each run (Happy Path)**
- **Given** a completed baseline allocation run (`scenario_id="baseline"`,
  `solver_seed=20180422`),
- **When** the sensitivity sweep runs `_tier_penalty` at ±20% (e.g.
  `swing: 1.10 → {0.88, 1.32}`), the DR curves' `k_shape`/`inflection_pct`
  at ±20%, and `COVERAGE_LOWER_BOUND_PCT` at ±10% (`0.80 → {0.72, 0.88}`),
  re-solving at each perturbation with the same `budget_usd` and
  `solver_seed`,
- **Then** a tornado artifact (e.g.
  `reports/module_b/parameter_sensitivity.csv`) records
  `total_persuasion_adjusted_contacts` and `total_budget_usd` per
  perturbation, alongside the baseline value, for every swept parameter.

**Scenario: Coefficient perturbation exceeds the stability threshold (Edge Case)**
- **Given** the sensitivity sweep above,
- **When** any single ±20% coefficient perturbation moves
  `total_persuasion_adjusted_contacts` by more than 15% from baseline,
- **Then** the sweep artifact flags that row `stability_breach: true` and the
  allocation run's summary (e.g. `reports/module_b/run_summary.md`) surfaces
  a named warning citing the offending parameter — the run is not blocked,
  but the instability is not allowed to be silent.

## 3. Specify Undesirable Behaviors (Negative Constraints)

**Scenario: Preventing new unlabeled coefficients**
- **Given** a future code change adds a new hand-picked multiplier to the
  objective (following the `_tier_penalty` / `_scenario_week_weight` pattern),
- **When** the provenance-completeness check (added by this IMP) runs,
- **Then** it fails, naming the new constant and requiring either a
  `provenance` manifest entry or the documented neutral-1.0 fallback before
  the PR can merge — this is the `AUD-B1`/`AUD-B6` recurrence this IMP closes.

**Scenario: Preventing sensitivity sweeps from becoming optional**
- **Given** a Module B allocation run invoked via
  `pipeline/run_allocation.py` or the FastAPI `GET /allocation/*` routes,
- **When** the run completes without also producing
  `reports/module_b/parameter_sensitivity.csv` for that `scenario_id` and
  `solver_seed`,
- **Then** the run is treated as incomplete by the governance gate — the
  sweep is mandatory output, not an opt-in flag.

## 4. Detail Data-Specific Non-Functional Requirements

- **Model fairness / bias:** `_tier_penalty` weights persuasion value by
  `department_tier` (`stronghold | swing | opposition | negligible`), which
  is itself a political-lean classification of the electorate
  (`department_tiers.yaml`, consumed by `features/district_tiers.py`). A
  0.55–1.10 multiplier spread by political classification is a proxy
  weighting of the target population by political affiliation; this IMP
  requires the provenance manifest to disclose that risk explicitly wherever
  `_tier_penalty` remains non-neutral, and the sensitivity sweep to report
  how much of the final allocation's cross-department variance is explained
  by tier penalty alone versus reach caps and cost.
- **Performance & decay:** the full sensitivity sweep (six budget multiples
  already exist; this IMP adds roughly a dozen more perturbation solves) must
  complete in under 10 minutes on the reference CBC configuration so it stays
  inside `make verify`'s existing CI budget; if wall time exceeds that, the
  sweep must down-sample (e.g. one perturbation per parameter family) rather
  than being skipped.
- **Data integrity:** the provenance manifest schema requires
  `parameter_name`, `current_value(s)`, `provenance` (`VERIFIED | PRIOR |
  ESTIMATED | NEUTRAL`), and `source` (citation string or `"neutral fallback
  per constants.py:90-93"`); a manifest entry missing `provenance` or
  `source` is a validator abort, mirroring the `VALID_PROVENANCE` enforcement
  already present for other Module B artifacts.
- **Reproducibility:** every sweep point reuses `solver_seed=20180422` (the
  `build_problem` default) and the same `fx_series_id`; only the swept
  parameter changes between runs, so re-running the sweep twice must produce
  byte-identical `parameter_sensitivity.csv` rows.

## 5. Queue Stub (ready to file)

```
Title: Publish objective-coefficient provenance manifest + mandatory parameter-sensitivity sweep for Module B

## Problem
Module B's MILP objective multiplies six coefficients per (department,
channel, week) cell. Three are anchored and documented
(`constants.py:90-105`, "Channels without a measured anchor carry the
neutral 1.0"). Two are not:

- `_tier_penalty` (`module_b_resource_allocation/src/module_b_resource_allocation/models/allocation.py:258-259`)
  — `{stronghold: 1.00, swing: 1.10, opposition: 0.85, negligible: 0.55}`,
  no derivation, no citation.
- `_scenario_week_weight` (`module_b_resource_allocation/src/module_b_resource_allocation/models/allocation.py:249-255`)
  — `1.15`/`0.95` and `0.92`/`1.20` per-week multipliers, same gap.

Both feed the objective at `models/allocation.py:368` and the post-solve
report at `:646`. Underneath them,
`module_b_resource_allocation/src/module_b_resource_allocation/features/diminishing_returns.py:33-73`
hard-codes 33 more floats (`_SAT_SHARE`, `_INFLECTION_PCT`, `_K_SHAPE` × 11
channels) shaping the concave response curve the whole LP optimizes against
— also uncalibrated.
`module_b_resource_allocation/src/module_b_resource_allocation/reporting/budget_sensitivity.py:11-81`
sweeps only `budget_usd` (0.25×–2.00×); it never perturbs `_tier_penalty`,
the DR shape parameters, or `COVERAGE_LOWER_BOUND_PCT`
(`constants.py:144`, `0.80`), so the existing sensitivity report validates LP
mechanics but says nothing about the hand-tuned coefficients driving the
recommendation.

## Evidence
- `module_b_resource_allocation/src/module_b_resource_allocation/models/allocation.py:249-259` — `_scenario_week_weight`, `_tier_penalty`.
- `module_b_resource_allocation/src/module_b_resource_allocation/models/allocation.py:368` — six-way objective coefficient multiply.
- `module_b_resource_allocation/src/module_b_resource_allocation/models/allocation.py:646` — duplicate persuasion formula in the post-solve row builder.
- `module_b_resource_allocation/src/module_b_resource_allocation/constants.py:90-106` — the anchored-vs-neutral discipline these two functions skip.
- `module_b_resource_allocation/src/module_b_resource_allocation/features/diminishing_returns.py:33-73` — 33 uncalibrated shape floats.
- `module_b_resource_allocation/src/module_b_resource_allocation/reporting/budget_sensitivity.py:11-81` — budget-only sweep.
- `module_b_resource_allocation/src/module_b_resource_allocation/models/allocation.py:559-574` — `_build_lp_diagnostics`, the dual-price surface the sweep already publishes.

## Acceptance criteria
1. `config/allocation_parameter_provenance.yaml` exists and has one entry per
   `_tier_penalty` value, `_scenario_week_weight` curve, and DR channel
   triple, each tagged `provenance: VERIFIED|PRIOR|ESTIMATED|NEUTRAL` with a
   `source` string.
2. A static check (invoked from `make verify`) fails if any objective
   coefficient in `models/allocation.py` or `features/diminishing_returns.py`
   is absent from the manifest.
3. `reporting/budget_sensitivity.py` (or a new sibling module) adds a
   parameter-perturbation sweep covering `_tier_penalty` (±20%),
   `_scenario_week_weight` (±20%), DR `k_shape`/`inflection_pct` (±20%), and
   `COVERAGE_LOWER_BOUND_PCT` (±10%), publishing
   `reports/module_b/parameter_sensitivity.csv` with a `stability_breach`
   column flagging >15% swings in `total_persuasion_adjusted_contacts`.
4. `pipeline/run_allocation.py` (or its CLI wrapper) is updated so a run is
   not considered complete without the sweep artifact for that
   `scenario_id`/`solver_seed`.

## Verification
- New test (e.g. `tests/test_parameter_provenance.py`) asserts manifest
  completeness against a static enumeration of coefficients read from
  `models/allocation.py` and `features/diminishing_returns.py`.
- New test (e.g. `tests/test_parameter_sensitivity_sweep.py`) runs the sweep
  on a small fixture problem and asserts the artifact has one row per swept
  parameter × perturbation direction, with `stability_breach` computed
  correctly against the 15% threshold.

## Spec
governance/improvement_plan/IMP-B01_allocation-parameter-provenance.md

## Labels
type:data, skill:module-b, effort:high, priority:p1, status:claude-ready
```
