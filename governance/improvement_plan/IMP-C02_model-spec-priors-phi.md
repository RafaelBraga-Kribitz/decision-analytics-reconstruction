---
id: IMP-C02
title: "Hierarchical model specification: wire-or-remove pollster prior families; calibrate transparency φ→σ_obs"
absorbs: [C4, C6]
overlaps_triage: []
priority: P1
effort: high
depends_on: [IMP-C01]
soft_depends_on: []
queue: issues
target_repo: decision-analytics-reconstruction
issue: 61
status: filed
---

# IMP-C02 — Hierarchical Model Specification: Dead Prior-Family Config and Uncalibrated φ

Two independent modeling gaps sit inside the same likelihood
(`models/tracking/hierarchical.py:fit_tracking_hierarchical`), and both feed
every published credible interval in Module C.

**Dead pollster-family config.** `config/pollster_prior_families.yaml:2-17`
defines a `families` map keyed by `pollster_bias_family` — `capli`
(`student_nu: 12.0`, `house_sigma_pp: 4.0`), `ica` (`student_nu: 4.0`,
`house_sigma_pp: 8.0`), `grau` (`house_loc_pp: 2.0`, `house_sigma_pp: 5.0`),
`ati_snead` (`house_sigma_pp: 6.0`, `time_varying: true`), and `default`
(`student_nu: 8.0`, `house_sigma_pp: 5.0`). None of these per-family
hyperparameters reach the model. `hierarchical.py:134-137` fits exactly one
pooled prior for every pollster regardless of family:
`sigma_house = pm.HalfNormal("sigma_house", 2.5)` then
`house_offset = pm.Normal("house_offset", 0.0, sigma=sigma_house, dims="pollster")`
— a single shared `sigma_house`, no per-family Student-t degrees of freedom,
no per-family location offset, no time-varying structure. The
`pollster_bias_family` column survives only as a passthrough label:
`cleaning_pipeline.py:129` writes it onto the clean row, and
`hierarchical.py:215,225` re-attaches it to the exported house-effects table
(`fam = tracking.groupby("pollster_id")["pollster_bias_family"].first()`
then `"pollster_bias_family": str(fam.get(p, "default"))`) purely for
display. `METHODOLOGY.md` caveat #2 ("House effects as random effects... 
Assumes offsets are exchangeable across firms. Violates if firm-family
effects... are systematic and non-modeled") *admits* the exchangeability
assumption but does not explain why a config file exists that implies the
opposite decision was made.

**Uncalibrated transparency-to-noise mapping.**
`data/transparency.py:10-25` (`compute_phi_transparency`) derives φ from four
booleans (`has_ficha`, `sample_size_known`, `field_window_known`,
`mode_known`) via `base = 0.55 if not has_ficha else 0.85`, `step = 0.12`,
`phi = base + step * n_ok`, clamped into `[PHI_MIN=0.08, PHI_MAX=1.0]`
(`:5-6`) with ad hoc special cases at `n_ok <= 1` and `n_ok == 0`
(`:21-24`). Every one of those constants (0.55, 0.85, 0.12, 0.08) is
asserted, not fit or validated against realized poll accuracy. φ then
directly sets the width of every reported HDI:
`sigma_obs = clip(6.0 / sqrt(phi), 1.0, 25.0)` at
`models/tracking/hierarchical.py:81-87` (`observation_sigma`). A pollster
with `has_ficha=False` and zero known pillars gets `phi = 0.12` →
`sigma_obs = clip(6.0/sqrt(0.12), 1.0, 25.0) = 17.3` pp — a difference of
more than 10× versus a fully-transparent pollster's `sigma_obs ≈ 6.1` pp
(`phi=0.97`) — riding entirely on the uncalibrated heuristic above.

## 1. Define the Scope (The Data Guardrails)

**In-Scope:**
- `config/pollster_prior_families.yaml` — either wired into
  `hierarchical.py`'s `pm.Model` block, or deleted with the exchangeability
  decision documented in an ADR.
- `data/transparency.py:compute_phi_transparency` (:10-25) and its constants
  `PHI_MIN`, `PHI_MISSING_TWO_OR_MORE`, `base`, `step`.
- `models/tracking/hierarchical.py:observation_sigma` (:81-87) — the
  φ→σ_obs mapping and its `[1.0, 25.0]` clip bounds.
- Any prior-predictive check or LOO/WAIC model-comparison artifact this
  document's remediation produces.

**Out-of-Scope:**
- The sampler's convergence behavior — a precondition tracked in IMP-C01
  (this document depends on it: reparameterizing priors before the sampler
  itself converges compounds diagnosis).
- The shock-score and herding-weight parameters (`lambda1..3`, `rho_herd`) —
  IMP-C04.
- The battleground/geo idiosyncratic-uncertainty calibration — IMP-C05.

## 2. Data-Driven "Given-When-Then" Scenarios

**Scenario: Prior families wired with a documented modeling decision (Happy Path)**
- **Given** `config/pollster_prior_families.yaml` families for `capli`,
  `ica`, `grau`, `ati_snead`, `default`,
- **When** `fit_tracking_hierarchical` builds its `pm.Model`,
- **Then** each pollster's `house_offset` prior uses its family's
  `student_nu`/`house_sigma_pp`/`house_loc_pp` (Student-t location-scale
  instead of the current pooled `Normal(0, sigma_house)`), a prior-predictive
  check confirms the resulting marginal house-effect distribution is
  plausible (no family's prior predictive places > 50% mass outside
  `[-15, 15]` pp), and a LOO or WAIC comparison against the pooled model is
  published showing the family model is not worse by more than 4 SE.

**Scenario: φ recalibrated against realized poll accuracy (Edge Case)**
- **Given** a historical or synthetic dataset of poll-vs-outcome residuals
  keyed by transparency pillar combination,
- **When** `compute_phi_transparency`'s constants are refit (or the mapping
  is replaced with a documented, monotonic function fit to residual
  variance),
- **Then** the fitted `sigma_obs(phi)` curve at each of the four pillar-count
  levels (`n_ok` ∈ {0,1,2,3}) is published alongside the empirical residual
  standard deviation it targets, with the gap quantified (not merely
  asserted as "reasonable").

## 3. Specify Undesirable Behaviors (Negative Constraints)

**Scenario: Preventing config that implies an undisclosed modeling decision**
- **Given** any config file under `config/` that names a per-entity
  hyperparameter (student_nu, house_sigma_pp, house_loc_pp, time_varying),
- **When** the model-fitting code is inspected,
- **Then** either the config value is consumed in the `pm.Model` block, or
  the config file is removed — a config that looks wired but is a dead
  passthrough label is a fail condition regardless of whether the pooled
  model "works fine in practice."

**Scenario: Preventing unbounded influence of an uncalibrated heuristic**
- **Given** `compute_phi_transparency`'s output feeds `sigma_obs` which sets
  every reported HDI width,
- **When** φ is not calibrated against real accuracy data,
- **Then** a sensitivity analysis must be published (bound φ's plausible
  range, refit, show the resulting HDI width delta) so the report can state
  a numeric bound on how much of the reported uncertainty is attributable to
  the heuristic rather than to genuine poll-to-poll variance — silence on
  this point is the fail condition, not the heuristic's existence per se.

## 4. Detail Data-Specific Non-Functional Requirements

- **Model fairness / bias:** the `pollster_bias_family` categories
  (`capli`, `ica`, `grau`, `ati_snead`) are firm identities, not protected
  population attributes — N/A for subgroup fairness. However, wiring
  per-family priors changes which pollsters' house effects get
  wider/narrower credible intervals; document this redistribution in the
  house-effects table caption once wired.
- **Performance & decay:** LOO/WAIC computation must add no more than 2
  minutes to the full-NUTS pipeline run; if wiring per-family priors
  degrades R̂/ESS below the IMP-C01 thresholds, this document's remediation
  is blocked until IMP-C01's gates re-pass.
- **Data integrity:** `sigma_obs` must remain clipped to a finite range
  (currently `[1.0, 25.0]` pp) regardless of how φ is recalibrated — an
  unclipped or negative `sigma_obs` must raise, not silently degrade.
- **Reproducibility:** any refit of `compute_phi_transparency`'s constants
  must be checked into `data/transparency.py` as literals (not computed at
  runtime from a mutable dataset) so seed-42 reruns remain deterministic.

## 5. Queue Stub (ready to file)

```
Title: Wire or remove pollster prior-family config; calibrate the φ→σ_obs mapping

Problem:
config/pollster_prior_families.yaml:2-17 defines per-pollster-family PyMC
hyperparameters (student_nu, house_sigma_pp, house_loc_pp, time_varying) for
capli/ica/grau/ati_snead/default, but models/tracking/hierarchical.py:134-137
fits one pooled prior for every pollster (sigma_house ~ HalfNormal(2.5),
house_offset ~ Normal(0, sigma_house)). pollster_bias_family is used only as a
passthrough display label (cleaning_pipeline.py:129, hierarchical.py:215,225).
Separately, data/transparency.py:10-25 (compute_phi_transparency) sets every
poll's sigma_obs via hierarchical.py:81-87 (observation_sigma) using
hand-asserted constants (base 0.55/0.85, step 0.12, floor 0.08) with no
calibration against real poll accuracy — this heuristic directly sets the
width of every published HDI.

Evidence file:line:
- config/pollster_prior_families.yaml:2-17
- models/tracking/hierarchical.py:134-137, :215, :225
- data/cleaning_pipeline.py:129
- data/transparency.py:5-25
- models/tracking/hierarchical.py:81-87

Acceptance criteria:
- Either (a) per-family priors are wired into the pm.Model block with a
  published prior-predictive check and a LOO/WAIC comparison against the
  pooled model showing the family model is not worse by > 4 SE, or (b)
  config/pollster_prior_families.yaml is deleted and METHODOLOGY.md caveat #2
  is amended to state exchangeability is the deliberate modeling decision
  (not an oversight).
- compute_phi_transparency's constants are either refit against a documented
  poll-accuracy dataset, or a published sensitivity analysis bounds the HDI
  width delta attributable to plausible φ misspecification.
- The φ→σ_obs mapping (data/transparency.py + hierarchical.py:81-87) is
  documented in METHODOLOGY.md with its justification, replacing the current
  unexplained constants.

Verification:
New test (or extension of module_c_forecasting_scenarios/tests/test_private_helpers_unit.py)
asserts either (a) hierarchical.py references
config/pollster_prior_families.yaml's families dict inside the pm.Model
construction, or (b) the config file no longer exists and METHODOLOGY.md
contains an explicit exchangeability-decision statement. A second test
asserts data/transparency.py's constants are covered by a calibration
docstring citing a named dataset or sensitivity bound.

Doc link: governance/improvement_plan/IMP-C02_model-spec-priors-phi.md

Labels: type:refactor, skill:module-c, effort:high, priority:p1, status:blocked
```

Note: `status:blocked` is applied (not `status:claude-ready`) because
`depends_on: [IMP-C01]` is non-empty — the sampler must converge on the
pooled model before per-family reparameterization is diagnosable.
