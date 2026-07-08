---
id: IMP-C01
title: "MCMC convergence remediation and hard diagnostic gates"
absorbs: [C1, C13]
overlaps_triage: []
priority: P0
effort: high
depends_on: []
soft_depends_on: []
queue: dual
target_repo: decision-analytics-reconstruction
issue: 60
status: draft
---

# IMP-C01 — MCMC Convergence Remediation and Hard Diagnostic Gates

Every reported posterior in Module C — the daily forecast track, the house
effects, the battleground map, the Monte Carlo scenario draws — descends from
one `pm.sample()` call in
`models/tracking/hierarchical.py:fit_tracking_hierarchical`. The test suite
that is supposed to gate that call's convergence is permanently disabled:

- `tests/test_mcmc_diagnostics_summary.py:69-88` —
  `test_rhat_acceptable_under_mc_fast` (assert `rhat < 1.05`), marked
  `@pytest.mark.xfail(reason="MC_FAST fixture insufficient for diagnostics; use full NUTS")`.
- `tests/test_mcmc_diagnostics_summary.py:90-108` — `test_ess_acceptable`
  (assert `ess > 200`), same permanent xfail.
- `tests/test_mcmc_diagnostics_summary.py:111-127` —
  `test_no_divergences_under_full_sampling` (assert `n_div == 0`), marked
  `@pytest.mark.xfail(reason="P2-4 non-centered reparameterization pending")`.

None of these xfails carry a tracking issue, a scheduled-CI escape hatch, or
an expiry condition — they are permanent. CI formally accepts non-convergence.
`portfolio/quarto/post_mortem.qmd:370-401` (the "Sampling Diagnostics" table)
reports on the *production* fixture: R̂ "> 1.01" against a "< 1.01" pass
criterion, ESS "< 100" against a "≥ 100" criterion, and "4" NUTS divergences
against a "0" criterion — three ⚠️ rows out of five, published as narrative
rather than blocked as a gate failure. `governance/findings/F-042-mcmc-diagnostics-disclosure.yaml`
(closed 2026-06-12) required only that public docs *disclose* the
aspirational status of these gates — it explicitly did not require fixing
the sampling geometry or promoting the xfails to hard failures. That
disclosure-only closure is the recurrence risk this document exists to close.

Separately, `tests/test_reproducibility.py` (repo root) is a pure
existence/shape suite — `test_module_c_tracking_daily_posterior_exists`
(:122-131) checks column presence, `test_module_c_tracking_hdi_ordering`
(:134-141) checks ordering only. No test in that file, or anywhere in the
repository, re-runs the tracking fit twice with the fixed seed
(`config/pymc_sampler.yaml:6`, `random_seed: 42`) and asserts posterior means
or HDI bounds agree within a numeric tolerance — despite
`METHODOLOGY.md:172-185` ("Reproducibility & Seeding") explicitly claiming
"Posterior samples: Drawn in order, reproducible via saved `idata`."

## 1. Define the Scope (The Data Guardrails)

**In-Scope:**
- The tracking hierarchical model's sampling geometry:
  `models/tracking/hierarchical.py:fit_tracking_hierarchical` (lines
  133-151, the `pm.Model` block and `pm.sample` call) and its priors
  `sigma_rw ~ HalfNormal(1.5)` (:134), `sigma_house ~ HalfNormal(2.5)` (:136).
- The three permanently-xfailed convergence tests in
  `tests/test_mcmc_diagnostics_summary.py:69-127` — removing the xfail marker
  is only valid once the underlying geometry passes the same assertions on
  full-NUTS production data.
- A new posterior-stability test (tolerance-bound, seed 42, two independent
  `fit_tracking_hierarchical` calls on the same input) added to
  `tests/test_reproducibility.py` or a module-C equivalent.
- The published diagnostics narrative in
  `portfolio/quarto/post_mortem.qmd:368-401`, to the extent its *pass/fail
  status* must track the gate outcome (the surface-level table-computation
  bug — hardcoded strings instead of computed values — is IMP-C03's slice;
  this document owns only the *underlying numbers* the table should reflect).

**Out-of-Scope:**
- The exit quick-count model's own NUTS run (`models/exit/exit_model.py`) —
  its small-n reliability is IMP-C06.
- Whether `phi_transparency` and `sigma_obs` are well-calibrated — that is
  IMP-C02.
- The Quarto report's literal-HTML rendering bug that hardcodes diagnostic
  values instead of computing them from `idata` — IMP-C03.
- Walk-forward validation power — IMP-C06.

## 2. Data-Driven "Given-When-Then" Scenarios

**Scenario: Full-NUTS convergence on the production fixture (Happy Path)**
- **Given** the 8-wave tracking fixture, `MC_FAST` unset (full NUTS: 4
  chains × 1000 draws, `target_accept=0.95`, `max_treedepth=15` per
  `config/pymc_sampler.yaml:1-5`),
- **When** `fit_tracking_hierarchical` runs to produce `idata`,
- **Then** `az.rhat(idata).max() <= 1.01` for every parameter,
  `az.ess(idata, method="bulk").min() >= 400` and
  `az.ess(idata, method="tail").min() >= 400`, and
  `idata.sample_stats["diverging"].sum() == 0`; the three tests in
  `tests/test_mcmc_diagnostics_summary.py:69-127` have their
  `@pytest.mark.xfail` markers removed and pass unconditionally in the slow
  CI lane.

**Scenario: Posterior stability across reruns (Edge Case)**
- **Given** the same tracking input and `random_seed: 42`
  (`config/pymc_sampler.yaml:6`),
- **When** `fit_tracking_hierarchical` is invoked twice in independent
  processes,
- **Then** `posterior_mean_preference_margin_pp` agrees within an absolute
  tolerance of 0.05 pp per day and `posterior_hdi_low_pp` /
  `posterior_hdi_high_pp` agree within 0.10 pp — named, numeric tolerances
  asserted by a new test, not the current existence-only checks in
  `tests/test_reproducibility.py:122-141`.

## 3. Specify Undesirable Behaviors (Negative Constraints)

**Scenario: Preventing silent re-acceptance of non-convergence**
- **Given** a future PR that reintroduces R̂ > 1.01, ESS < 400, or any
  divergence on the full-NUTS production path,
- **When** the (now hard, non-xfail) diagnostic tests run in the slow CI
  lane,
- **Then** the test suite fails the build; no `@pytest.mark.xfail` may be
  reintroduced on these three tests without also reopening this finding
  (`status: open`) and citing a P2-tracked remediation date — a bare
  `xfail` with no expiry is itself a fail condition the Adversary must catch.

**Scenario: Preventing "aspirational" language from substituting for a gate**
- **Given** `reports/C_research_proof_table.md:23-27` ("MCMC diagnostics
  (aspirational)... not a merge gate while `MC_FAST=1` is the default CI
  path"),
- **When** this remediation lands,
- **Then** that section is rewritten to state the full-NUTS diagnostics ARE
  a merge gate in the slow lane, with the lane named explicitly — "aspirational"
  language describing a currently-unenforced gate is banned from any
  committed artifact once the gate is enforced.

## 4. Detail Data-Specific Non-Functional Requirements

- **Model fairness / bias:** N/A — this is a sampler-geometry and
  test-enforcement change; it does not alter which entities or subgroups are
  modeled.
- **Performance & decay:** Full-NUTS remediation (denser day-grid handling,
  non-centered `GaussianRandomWalk`/`HalfNormal` reparameterization, or an
  increased `tune`/`draws` budget) must keep the full-NUTS fit under 10
  minutes wall-clock in the slow CI lane; if a change increases runtime past
  that, it must be paired with a `draws`/`tune` reduction that still clears
  the R̂/ESS/divergence thresholds above. Any metric regression beyond the
  stated thresholds must trigger reopening this finding.
- **Data integrity:** The daily posterior parquet's `model_version` field
  (`models/tracking/hierarchical.py:18`, currently
  `c_tracking_hierarchical_v0.3`) must be bumped on any reparameterization,
  per the existing convention used for the v0.1→v0.2 HDI-honesty fix.
- **Reproducibility:** Seed 42 fixed in `config/pymc_sampler.yaml:6`; the new
  posterior-stability test is the enforcement mechanism for the
  `METHODOLOGY.md:172-185` reproducibility claim, which currently has no
  test backing it at all.

## 5. Queue Stub (ready to file)

**Finding slice** — owns the fact that convergence gates are permanently
disabled while reports publish the resulting posteriors as if the model
converged (a `fake_completion`-class governance defect, independent of
whether the eventual model fix is hard).

```yaml
id: F-XXX            # assigned at filing time
title: "MCMC convergence gates are permanently xfail'd while reports publish the resulting posteriors"
category: fake_completion
kind: recurrence_invariant
status: open
opened_at: 2026-07-08
closed_at: null
recurrence_count: 1   # F-042 previously closed this class via disclosure-only remediation
evidence: |
  tests/test_mcmc_diagnostics_summary.py:69-88 (test_rhat_acceptable_under_mc_fast,
  assert rhat < 1.05), :90-108 (test_ess_acceptable, assert ess > 200), and
  :111-127 (test_no_divergences_under_full_sampling, assert n_div == 0) are all
  marked @pytest.mark.xfail with no expiry or tracked remediation date.
  portfolio/quarto/post_mortem.qmd:370-401 (the "Sampling Diagnostics" table)
  shows the production fixture actually failing all three: R̂ > 1.01, ESS < 100,
  4 divergences vs a stated "0" pass criterion. F-042 (closed 2026-06-12) required
  only narrative disclosure of this gap, not remediation or hard-gating — this is
  the second cycle of the same underlying defect.
verification_script: scripts/check_mcmc_convergence_gates_hard.py
notes: |
  Proposed script behavior: (1) parse
  module_c_forecasting_scenarios/tests/test_mcmc_diagnostics_summary.py and fail
  if any of test_rhat_acceptable_under_mc_fast, test_ess_acceptable,
  test_no_divergences_under_full_sampling carry an xfail marker; (2) grep
  reports/C_research_proof_table.md for the string "aspirational" in the MCMC
  diagnostics section and fail if present without an adjacent "ENFORCED" marker
  keyed to a CI lane name. Distinct from F-042's verification_script
  (scripts/check_mcmc_diagnostics_disclosure.py), which only checks that the
  aspirational status is *disclosed* — this script checks the gate is *removed*.
  Spec: governance/improvement_plan/IMP-C01_mcmc-convergence-gates.md
```

**Issue slice** — owns the model remediation itself (reparameterization,
sampling-budget changes, the posterior-stability test).

```
Title: Remediate MCMC convergence on the tracking hierarchical model to hard R̂/ESS/divergence gates

Problem:
models/tracking/hierarchical.py:fit_tracking_hierarchical (models/tracking/hierarchical.py:133-151)
does not converge on the production 8-wave fixture under full NUTS:
portfolio/quarto/post_mortem.qmd:370-401 reports R̂ > 1.01 (criterion < 1.01),
ESS < 100 (criterion ≥ 100), and 4 divergences (criterion 0). The three tests
that should catch this — test_rhat_acceptable_under_mc_fast,
test_ess_acceptable, test_no_divergences_under_full_sampling in
tests/test_mcmc_diagnostics_summary.py:69-127 — are permanently xfail'd.
Every downstream artifact (daily_posterior_forecast.parquet,
posterior_house_effects.parquet, battleground_department_probability.parquet,
monte_carlo_draws.parquet) inherits an unvalidated posterior.

Evidence file:line:
- tests/test_mcmc_diagnostics_summary.py:69-127
- portfolio/quarto/post_mortem.qmd:370-401
- models/tracking/hierarchical.py:133-151 (sigma_rw ~ HalfNormal(1.5), sigma_house ~ HalfNormal(2.5))
- METHODOLOGY.md:172-185 (reproducibility claims with no backing test)

Acceptance criteria:
- Full-NUTS fit on the production fixture achieves R̂ ≤ 1.01 for every
  parameter, ESS bulk and tail ≥ 400, and 0 divergences — OR a documented
  non-centered reparameterization is committed with a written rationale in
  METHODOLOGY.md explaining the change.
- The three xfail markers in tests/test_mcmc_diagnostics_summary.py:69-127
  are removed; the tests pass unconditionally in the slow CI lane.
- A new posterior-stability test asserts two independent fits (same seed 42
  input) agree within 0.05 pp (posterior mean) and 0.10 pp (HDI bounds) per
  day.
- MODEL_VERSION in hierarchical.py:18 is bumped past c_tracking_hierarchical_v0.3.

Verification:
Run `poetry run pytest module_c_forecasting_scenarios/tests/test_mcmc_diagnostics_summary.py -m slow`
with MC_FAST unset; all three previously-xfailed tests must report PASS (not
XFAIL/XPASS). Run the new posterior-stability test twice back to back and
confirm tolerance bounds hold.

Doc link: governance/improvement_plan/IMP-C01_mcmc-convergence-gates.md

Labels: type:bug, skill:module-c, effort:high, priority:p0
```
