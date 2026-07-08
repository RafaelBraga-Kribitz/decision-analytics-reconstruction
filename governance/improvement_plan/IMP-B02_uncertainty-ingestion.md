---
id: IMP-B02
title: "Uncertainty-aware ingestion of Module A outputs"
absorbs: [B3]
overlaps_triage: [AUD-S1, AUD-S3]
priority: P1
effort: high
depends_on: [IMP-A01, IMP-A03]
soft_depends_on: []
queue: issues
target_repo: decision-analytics-reconstruction
issue: 58
status: filed
---

# IMP-B02 — Uncertainty-Aware Ingestion of Module A Outputs

`features/module_a_ingestion.py:99-140` (`department_media_profile`) reduces
Module A's segment×department reachability export to one row per department
by taking a `segment_size`-weighted mean of `mean_participation_propensity`,
`mean_tv_penetration`, `mean_radio_penetration`, `mean_whatsapp_penetration`,
and `pct_internet_access` — five point estimates, no variance, no standard
error, no interval.

`models/feature_join.py:146-157` feeds those point estimates straight into
the LP as fixed coefficients: measured penetration overwrites the YAML
`reach_cap_share` prior for TV/radio/WhatsApp/internet channels
(`provenance = "MODULE_A"`), and `dept_mean_propensity` becomes a persuasion
multiplier consumed by `_propensity_weight` at `models/allocation.py:262-272`
— which itself already defaults silently to `1.0` for any null or
non-positive value. Nowhere between Module A's model and Module B's MILP does
an interval, a sampling distribution, or even a coefficient-of-variation
cross the module boundary. The MILP treats every `dept_mean_propensity` and
every measured penetration rate as certain.

There is no stochastic or robust-optimization counterpart in Module B, and no
diagnostic that asks "how much does the recommended allocation change if
Module A's propensity estimate for department X is off by its own
uncertainty band?" `reporting/budget_sensitivity.py` sweeps `budget_usd`
only (see `IMP-B01`); it has no analog for input noise originating upstream
of the LP.

## 1. Define the Scope (The Data Guardrails)

**In-Scope:**
- The A→B handshake contract: `data/processed/media_reachability_by_segment_department.csv`
  and its schema (`schema_contracts/media_reachability_by_segment_department.yaml`),
  extended to carry an uncertainty representation (interval bounds or a
  finite sample set) alongside each point estimate.
- `department_media_profile` (`features/module_a_ingestion.py:99-140`),
  extended to aggregate and propagate that uncertainty (not just the
  weighted mean) into the department-level profile.
- `build_allocation_features`'s Module A merge block
  (`models/feature_join.py:137-157`), extended so `dept_mean_propensity` (and
  the measured `reach_cap_share` overrides) carry an uncertainty band rather
  than a single float, and the silent `fillna(1.0)` at
  `feature_join.py:155` is replaced with a disclosed, counted fallback.
- Module B's response to that uncertainty: either (a) a scenario-ensemble /
  robust-counterpart re-solve, or (b) — if full robust optimization is out of
  reach for this increment — a published allocation-stability-under-input-noise
  diagnostic comparable in shape to `IMP-B01`'s parameter-sensitivity sweep,
  perturbing `dept_mean_propensity` and measured `reach_cap_share` within
  their propagated bands rather than by an arbitrary ±X%.
- The handshake schema fields needed to carry uncertainty end-to-end
  (e.g. `propensity_ci_low` / `propensity_ci_high` or
  `propensity_samples_json`, mirrored for each measured penetration column).

**Out-of-Scope:**
- Fixing the source of Module A's own instability — this IMP assumes Module
  A's propensity model and its estimation procedure are the inputs, not the
  subject, of this change. That is `IMP-A01` (propensity model estimand
  stability) and `IMP-A03` (Module A's own circularity/convergence issues) —
  **hard dependencies**, not soft ones: propagating an uncertainty interval
  computed by an upstream model that is itself circular or non-convergent
  produces a number that looks rigorous but means nothing. This IMP does not
  start until both are done.
- Objective-coefficient provenance for `_tier_penalty` /
  `_scenario_week_weight` / diminishing-returns shape parameters (`IMP-B01`).
- MILP degenerate-case handling (`IMP-B03`).
- Silent-drop reporting in the data-cleaning layer (`IMP-B04`).

## 2. Data-Driven "Given-When-Then" Scenarios

**Scenario: Uncertainty crosses the A→B boundary (Happy Path)**
- **Given** Module A's export
  (`data/processed/media_reachability_by_segment_department.csv`, once
  `IMP-A01`/`IMP-A03` land) includes per-segment-department uncertainty
  columns (e.g. `participation_propensity_se`) alongside
  `mean_participation_propensity`,
- **When** `department_media_profile` aggregates segment rows to department
  rows,
- **Then** the returned profile carries both `mean_participation_propensity`
  and a propagated interval (e.g. `propensity_ci_low`,
  `propensity_ci_high`) computed from the segment-level standard errors and
  `segment_size` weights — not a bare mean.

**Scenario: Allocation-stability-under-input-noise diagnostic (Happy Path)**
- **Given** a completed baseline allocation run whose feature frame carries
  `dept_mean_propensity` with a non-degenerate `propensity_ci_low`/`_high`
  band for at least one department,
- **When** the input-noise diagnostic re-solves the MILP with
  `dept_mean_propensity` set to each department's interval bounds (holding
  all `IMP-B01`-governed coefficients fixed),
- **Then** an artifact (e.g.
  `reports/module_b/input_noise_sensitivity.csv`) records
  `total_persuasion_adjusted_contacts` and the per-department allocation
  delta at each bound, so the report answers "how much does Module A's own
  uncertainty move the recommendation" as a concrete number, not a claim.

**Scenario: Module A artifact missing an uncertainty column (Edge Case)**
- **Given** `data/processed/media_reachability_by_segment_department.csv`
  exists but lacks the new uncertainty columns (e.g. a stale export produced
  before this contract change),
- **When** `build_allocation_features(use_module_a=True)` runs,
- **Then** it must not silently proceed as if uncertainty were zero; it must
  either raise (mirroring the existing `ValueError` for missing required
  columns at `module_a_ingestion.py:90-95`) or set `provenance` to a value
  that explicitly flags degraded confidence (e.g.
  `"MODULE_A_NO_UNCERTAINTY"`), never `"MODULE_A"` unqualified.

## 3. Specify Undesirable Behaviors (Negative Constraints)

**Scenario: Preventing silent point-estimate-as-certainty**
- **Given** the current behavior at `feature_join.py:146-157`, where
  `dept_mean_propensity` is fed into the LP as a bare float,
- **When** this IMP lands,
- **Then** every `dept_mean_propensity` value consumed by
  `_propensity_weight` (`models/allocation.py:262-272`) must be traceable to
  either a propagated interval or an explicit "no uncertainty available,
  treated as point estimate with disclosed risk" flag — never an unqualified
  float with no record of its confidence.

**Scenario: Preventing the silent `fillna(1.0)` from masking missing propensity data**
- **Given** `feature_join.py:155`
  (`df["dept_mean_propensity"] = dept_series.map(propensity_by_dept).fillna(1.0)`),
- **When** any department has no matching Module A profile row and is
  silently neutralized to `1.0`,
- **Then** the feature frame must record a count of how many departments were
  neutralized this way (e.g. a `dept_mean_propensity_source` column with
  value `"MODULE_A" | "NEUTRAL_FALLBACK"`), so the fallback is visible in the
  same way `IMP-B04` requires for data-cleaning drops.

## 4. Detail Data-Specific Non-Functional Requirements

- **Model fairness / bias:** `dept_mean_propensity` differentiates persuasion
  value by department; if Module A's uncertainty is systematically wider for
  smaller or Chaco-region departments (`CHACO_DEPARTMENTS`,
  `constants.py:48-50`) due to smaller segment sizes, propagating that
  uncertainty must not silently bias the robust/ensemble solve toward
  already-well-measured departments. The diagnostic must report interval
  width by department alongside the allocation delta so this asymmetry is
  visible.
- **Performance & decay:** if a scenario-ensemble approach is chosen, the
  ensemble size (N draws) must keep total re-solve time under a documented
  ceiling (e.g. 20 draws × current single-solve wall time, published as part
  of the diagnostic run); if that ceiling is exceeded, the interval-bounds
  approach (two extra solves per department-bearing coefficient) is the
  required fallback rather than silently truncating the ensemble.
- **Data integrity:** the extended handshake schema must enforce
  `propensity_ci_low <= mean_participation_propensity <= propensity_ci_high`
  (or the sample-set analog) as a validator abort condition — an inverted or
  degenerate interval is a contract violation, not a warning.
- **Reproducibility:** any ensemble draws must use a fixed, recorded seed
  (documented alongside `solver_seed`) so the input-noise diagnostic
  reproduces byte-identically across runs.

## 5. Queue Stub (ready to file)

```
Title: Propagate Module A uncertainty into Module B's MILP objective and publish an allocation-stability-under-input-noise diagnostic

## Problem
`module_b_resource_allocation/src/module_b_resource_allocation/features/module_a_ingestion.py:99-140`
(`department_media_profile`) computes only segment-size-weighted point-estimate
means of Module A's propensity and penetration measures. No variance,
standard error, or interval crosses the module boundary.
`module_b_resource_allocation/src/module_b_resource_allocation/models/feature_join.py:146-157`
feeds those means into the MILP as fixed coefficients
(`dept_mean_propensity`), and line 155 silently `fillna(1.0)`s any
department Module A didn't cover. Module B has no stochastic or robust
counterpart, and no input-noise sensitivity diagnostic analogous to the
budget sweep in `reporting/budget_sensitivity.py`.

## Evidence
- `module_b_resource_allocation/src/module_b_resource_allocation/features/module_a_ingestion.py:99-140` — point-estimate-only aggregation.
- `module_b_resource_allocation/src/module_b_resource_allocation/models/feature_join.py:146-157` — fixed-coefficient feed into the LP, including the silent `fillna(1.0)` at line 155.
- `module_b_resource_allocation/src/module_b_resource_allocation/models/allocation.py:262-272` — `_propensity_weight`'s own silent default to `1.0` on null/non-positive input.

## Acceptance criteria
1. The A→B handshake schema
   (`schema_contracts/media_reachability_by_segment_department.yaml`) gains
   uncertainty fields (interval or sample-set) for
   `mean_participation_propensity` and each measured penetration column.
2. `department_media_profile` propagates that uncertainty into the
   department-level profile rather than emitting a bare mean.
3. `build_allocation_features` either re-solves an ensemble across the
   propagated uncertainty or publishes
   `reports/module_b/input_noise_sensitivity.csv` recording the allocation
   delta at each department's propensity interval bounds.
4. The silent `fillna(1.0)` at `feature_join.py:155` is replaced with an
   explicit `dept_mean_propensity_source` disclosure column.

## Verification
- New test asserting the handshake schema validator rejects an inverted
  interval (`ci_low > ci_high`).
- New test asserting `department_media_profile` output has non-null interval
  columns whenever input segment rows carry uncertainty, and an explicit
  degraded-confidence flag when they do not.
- New test asserting the input-noise diagnostic artifact has one row per
  department with a non-trivial propensity interval.

## Spec
governance/improvement_plan/IMP-B02_uncertainty-ingestion.md

## Labels
type:data, skill:module-b, effort:high, priority:p1, status:blocked
```

**Note on `status:blocked`:** this issue must **not** carry
`status:claude-ready` — `depends_on: [IMP-A01, IMP-A03]` is non-empty, and
per the label taxonomy `status:claude-ready` requires no unresolved
blockers. Re-label to `status:claude-ready` only after both dependency IMPs
reach `status: done`.
