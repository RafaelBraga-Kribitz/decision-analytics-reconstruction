---
id: IMP-C04
title: "Shock and herding parameters: calibration or sensitivity-bounded disclosure"
absorbs: [C5]
overlaps_triage: []
priority: P1
effort: high
depends_on: []
soft_depends_on: []
queue: issues
target_repo: decision-analytics-reconstruction
issue: 62
status: filed
---

# IMP-C04 — Shock & Herding Parameter Calibration

Module C's scenario machinery is driven end-to-end by asserted constants that
have never been fit, cross-validated, or historically calibrated:

- `module_c_forecasting_scenarios/config/shock_params.yaml:1-4` —
  `lambda1: 0.08`, `lambda2: 0.35`, `lambda3: 0.12`,
  `m_star_extreme_pp: 12.0`.
- `src/module_c_forecasting_scenarios/features/shock_scores.py:38,50-57` —
  `scenario_bucket_for_margin` cuts on `phi < 0.35` and `rho > 0.4`.
- `src/module_c_forecasting_scenarios/features/herding_weights.py:10-23` —
  `rho_herd_for_row` hardcodes a date window (2018-03-15..31) and substring
  matches on carrier names (`"vierci" in carrier`, `"ica" in carrier`) mapped
  to covariance values 0.55/0.35/0.25/0.05, self-labeled "(modeling
  hypothesis)" in its own docstring.

These parameters deterministically assign every poll and every Monte Carlo
draw to one of the three canonical scenario buckets
(`baseline` / `extreme_tracker` / `compounded_herd`,
`scenarios/monte_carlo.py:27-45`), so every scenario-level summary the
project publishes is a function of numbers with no statistical provenance.
The substring matching is additionally fragile: a renamed or newly added
pollster silently falls into the default covariance.

## 1. Define the Scope (The Data Guardrails)

**In-Scope:**
- Provenance for every constant in `shock_params.yaml` and every threshold in
  `shock_scores.py`: each value either (a) estimated from a documented
  historical polling-error dataset with the estimation method recorded, or
  (b) kept as an explicit modeling hypothesis with a pre-registered
  sensitivity envelope showing how bucket assignments move under perturbation.
- Replacement of substring-based carrier matching in `herding_weights.py`
  with an explicit pollster→herding-group mapping table in config, with a
  defined behavior for unmapped pollsters (default group + logged warning,
  never a silent match).
- A published sensitivity artifact: bucket-assignment stability table under
  ±25% and ±50% perturbation of λ1/λ2/λ3, the 12 pp extreme cutoff, and the
  0.35/0.4 bucket thresholds.
- Disclosure requirements: every artifact downstream of the bucket assignment
  (Monte Carlo summaries, scenario box plots) carries a caption noting the
  parameters are hypothesis-driven, until calibration lands.

**Out-of-Scope:**
- The Monte Carlo bucket *sampling proportions* (IMP-C08).
- The transparency proxy φ feeding observation noise (IMP-C02) — φ appears
  here only as a bucket-threshold input; its construction is IMP-C02's.
- The hierarchical model's convergence (IMP-C01).

## 2. Data-Driven "Given-When-Then" Scenarios

**Scenario: Parameter provenance ledger (Happy Path)**
- **Given** the shock/herding configuration,
- **When** a reader inspects `shock_params.yaml` (or its companion doc),
- **Then** every parameter row names one of: `estimated` (with dataset,
  method, fit date, and standard error) or `hypothesis` (with its sensitivity
  envelope reference) — no unlabeled constants remain.

**Scenario: Explicit pollster mapping (Happy Path)**
- **Given** a poll row whose carrier is listed in the pollster→group mapping
  table,
- **When** `rho_herd_for_row` resolves its herding covariance,
- **Then** the value comes from the table entry, and the resolution is
  reproducible from config alone — no string containment logic participates.

**Scenario: Unmapped pollster (Edge Case)**
- **Given** a poll row whose carrier does not appear in the mapping table
  (new pollster, renamed outlet),
- **When** herding covariance is resolved,
- **Then** the row receives the documented default group, a structured
  warning naming the unmapped carrier is emitted to the run log, and the run
  summary counts unmapped carriers — the pipeline never silently
  substring-matches a new name into a high-covariance group.

**Scenario: Bucket-assignment sensitivity (Edge Case)**
- **Given** the canonical tracking dataset and the perturbation grid
  (±25%, ±50% on each hypothesis parameter),
- **When** the sensitivity artifact is regenerated,
- **Then** it reports, per parameter, the fraction of polls whose bucket
  assignment changes; any parameter whose ±25% perturbation reassigns more
  than 20% of polls is flagged `assignment-critical` in the artifact, and
  every scenario-level chart consuming buckets must disclose the
  assignment-critical list in its caption.

## 3. Specify Undesirable Behaviors (Negative Constraints)

**Scenario: Preventing hypothesis constants masquerading as estimates**
- **Given** any report, chart caption, or schema description touching
  scenario buckets,
- **When** it describes the bucket construction,
- **Then** it must not use estimation language ("fitted", "calibrated",
  "learned") for parameters whose ledger row says `hypothesis`.

**Scenario: Preventing silent identity drift in pollster matching**
- **Given** any future change to poll ingestion that introduces new carrier
  strings,
- **When** the herding resolution runs,
- **Then** it must never assign a non-default covariance to a carrier absent
  from the mapping table — partial string matches, case-folding coincidences,
  and alias guessing are prohibited resolution mechanisms.

**Scenario: Preventing sensitivity results from being computed once and left to rot**
- **Given** a change to `shock_params.yaml`, `shock_scores.py` thresholds, or
  the mapping table,
- **When** CI runs on that change,
- **Then** the sensitivity artifact must be regenerated in the same PR (its
  recorded parameter hash must match the config), otherwise the check fails —
  a stale sensitivity table is treated as no sensitivity table.

## 4. Detail Data-Specific Non-Functional Requirements

- **Model fairness / bias:** the pollster→group mapping must be exhaustively
  enumerable and reviewable — no pollster may be structurally advantaged or
  penalized by an undocumented string coincidence.
- **Performance & decay:** the full sensitivity grid (2 perturbation levels ×
  ~6 parameters × canonical dataset) must complete in < 10 minutes in the
  `MC_FAST` configuration so it can run per-PR; the full-draw variant may run
  in the scheduled lane.
- **Data integrity:** `shock_params.yaml` gains a schema (types, bounds:
  λ ∈ (0,1), m_star_extreme_pp ∈ (0, 30]); loading aborts on out-of-bounds
  values or unknown keys.
- **Reproducibility:** bucket assignment is a pure function of (poll row,
  config); identical inputs yield identical buckets across runs and machines
  — no wall-clock or ordering dependence.

## 5. Queue Stub (ready to file)

**GitHub issue body:**

> **Title:** Module C: calibrate or sensitivity-bound the shock & herding parameters (IMP-C04)
>
> **Problem.** Scenario-bucket assignment for every poll and Monte Carlo draw
> is driven by uncalibrated constants: λ1/λ2/λ3 and the 12 pp extreme cutoff
> (`config/shock_params.yaml:1-4`), bucket thresholds `phi < 0.35` /
> `rho > 0.4` (`features/shock_scores.py:38,50-57`), and herding covariances
> resolved by date windows plus substring matching on carrier names
> (`features/herding_weights.py:10-23`). None is estimated from data; the
> substring matching silently misclassifies renamed/new pollsters.
>
> **Acceptance criteria.**
> 1. Every shock/herding parameter carries a provenance ledger row:
>    `estimated` (dataset, method, SE) or `hypothesis` (sensitivity envelope).
> 2. Substring matching replaced by an explicit pollster→group config table;
>    unmapped carriers get the default group + logged warning + run-summary
>    count.
> 3. Sensitivity artifact published: bucket reassignment fractions under
>    ±25%/±50% perturbation per parameter; `assignment-critical` parameters
>    flagged and disclosed in downstream captions.
> 4. `shock_params.yaml` schema-validated on load (bounds, unknown-key abort).
> 5. CI fails when the sensitivity artifact's parameter hash mismatches the
>    config (stale-artifact guard).
>
> **Verification.** Rerun pipeline on the canonical fixture: identical bucket
> assignments across two runs; inject an unknown carrier and observe default
> group + warning; perturb λ2 by +25% and observe the artifact regenerate
> with changed reassignment fractions.
>
> **Spec:** `governance/improvement_plan/IMP-C04_shock-herding-calibration.md`

**Labels:** `type:data`, `skill:module-c`, `effort:high`, `priority:p1`,
`status:claude-ready`
