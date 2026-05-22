---
doc_id: DOC-EVID-018
doc_type: evidence
doc_role: evidence
visibility: internal
status: active
owner: maintainer
last_reviewed: '2026-05-22'
canonical_source: null
derived_from: null
supersedes: null
tags: []
---

# Statistical Audit — Decision Analytics Reconstruction

**Date:** 2026-05-22
**Scope:** Statistical basis, models, and analysis of Modules A (segmentation),
B (resource allocation), C (probabilistic forecasting).
**Audience:** Repository author and AI agents only. Internal / candid — kept out
of hiring-facing trees per `maintainer/pre_public_cleanup_manifest.md`.
**Verdict:** **Sound engineering; the statistical *claims* need re-framing.** The
models run, the pipeline is reproducible, and the repo already discloses a great
deal honestly. But several headline numbers are *mechanically determined by
assumptions* rather than estimated from data, one headline metric is
*leakage-inflated*, and one shipped artifact column is *factually mislabeled*.
None of this is fatal for a reconstruction portfolio — but a sharp reviewer will
find these, so they should be found here first.

---

## 1. Scope & method

This audit examines the *statistical content* of the three modules — not code
style, packaging, or CI plumbing. It was produced by direct source inspection
with file/line anchors, cross-referenced against the repository's own
methodology documents (`reports/epistemic_boundaries.md`,
`reports/statistical_independence_note.md`,
`reports/statistical_metrics_summary.md`, the module model cards, and
`module_a_population_segmentation/reports/audit_report_module_a_2026-05-11.md`).

**Not done:** independent re-execution of the pipeline. The local environment
does not have the project dependencies installed (`sklearn`, `pymc` absent), and
the central finding (A1) is provable by static analysis without a run. Reported
metrics below are quoted from the repo's own artifacts and labeled as such.

**Severity scale.** Critical = invalidates a headline claim; High = materially
misleads a reviewer or breaks a stated guarantee; Medium = unjustified or
undisclosed assumption that weakens rigor; Low = minor / already disclosed.

**Disclosure column.** Whether the repo's *existing* docs already concede the
issue: Disclosed / Partial / Undisclosed.

---

## 2. Findings register

| ID | Module | Finding | Severity | Disclosure |
|----|--------|---------|----------|------------|
| A1 | A | Propensity feature–target leakage; headline AUC is invalid | **Critical** | Partial |
| A2 | A | Department "calibration" is rake-enforced, reported as validation | High | Partial |
| A3 | A | `k=6` unjustified; silhouette weak; gates lowered to match output | High | Partial |
| A4 | A | Arbitrary synthetic-distribution constants; no sensitivity analysis | Medium | Partial |
| A5 | A | Config/code drift — `model_params.yaml` not wired to runtime | Medium | Disclosed |
| A6 | A | Only AUC gate (`0.70`) is declared but never asserted in tests | Medium | Disclosed |
| A7 | A | Calibration/test split is not stratified | Low | Disclosed |
| B1 | B | Response-curve parameters are hand-coded priors, not fitted | High | Disclosed |
| B2 | B | Scenario "uplift" is set by hardcoded week-weight multipliers | High | Undisclosed |
| B3 | B | Counterfactual is a mechanical reallocation, not a re-optimization | Medium | Undisclosed |
| B4 | B | Multiplicative persuasion aggregation is unjustified | Medium | Undisclosed |
| B5 | B | Tier penalties and pay-TV lock are hardcoded without rationale | Medium | Undisclosed |
| B6 | B | Duals/sensitivity valid only inside the LP, not as real elasticity | Low | Disclosed |
| C1 | C | Central interval is shipped under `posterior_hdi_*` column names | High | Undisclosed |
| C2 | C | Per-family pollster priors are defined in YAML but never used | High | Undisclosed |
| C3 | C | No convergence diagnostics (R-hat/ESS/divergences) are enforced | High | Partial |
| C4 | C | Exit-model intercept prior `Normal(60, 15)` is unjustified | Medium | Undisclosed |
| C5 | C | No prior sensitivity analysis anywhere | Medium | Partial |
| C6 | C | `macro_context_prior.yaml` is defined but never loaded | Medium | Undisclosed |
| C7 | C | Monte Carlo shock weights/thresholds are arbitrary; circular prior | Medium | Partial |
| C8 | C | Walk-forward validation has 2 holdouts — not a meaningful estimate | Low | Disclosed |
| C9 | C | Observation noise `sigma_obs` is deterministic, not estimated | Low | Undisclosed |

Count: 1 Critical, 7 High, 9 Medium, 4 Low. Undisclosed or partially disclosed:
15 of 21.

---

## 3. Cross-cutting: the circularity spine (X1)

Every module shares one structural pattern. It is defensible *as a
reconstruction method*, but it bounds what the project's numbers can mean.

```
calibration anchors (TSJE/DGEEC/INE/BCP)
        │
        ▼
synthetic data generated to hit those anchors          (Module A generator)
        │
        ▼
models trained / solved / sampled on the synthetic data
        │
        ├─ Module A: the anchors RE-ENTER as a model feature  → A1 leakage
        ├─ Module B: "results" are fixed by hardcoded params  → B1, B2
        └─ Module C: validation runs only on synthetic fixtures → C8
        │
        ▼
metrics & "uplift" reported as outcomes
```

The distinction a reviewer will probe is **discovered vs. mechanically
determined**:

- **Discovered** (defensible): the verified anchors themselves — TSJE outcome
  margin +3.70 pp, department participation rates, EPHC internet penetration,
  BCP FX corridor. These are real and independently checkable.
- **Mechanically determined** (must be framed as such): the propensity model's
  discrimination (A1), Module B's scenario "uplift" (B2), the diminishing-returns
  curve shape and saturation ceilings (B1), Monte Carlo bucket frequencies (C7).
  These are *outputs of assumptions*, not findings.

`reports/epistemic_boundaries.md` handles this honestly at the **artifact**
level (VERIFIED / CALIBRATED / SIMULATED / ILLUSTRATIVE). What it does not do is
descend to the **model-internal** level — where the leakage, the mislabeled
interval, and the config/code drift live. That is the gap this audit fills.

---

## 4. Module A — Population Segmentation

### A1 — Propensity feature–target leakage *(Critical)*

`PropensityModel` in
`module_a_population_segmentation/src/population_segmentation/pipeline/models/propensity.py`:

- The **target** is synthetic (`_synthetic_target`, lines 165–197). Its mean is
  `base = national + dept_deviation + youth_adj + gender_adj`, where
  `dept_deviation = dept_rate − national` (lines 179–193).
- The **feature matrix** (`_feature_matrix`, lines 145–163) adds
  `department_logit_offset = logit(dept_rate)` — computed from the *same*
  `department_participation_rates` anchors.

So a feature is a strictly monotone transform of the dominant additive term of
the target's own mean. This is textbook target leakage. The code comment at
lines 149–151 records that the feature was *added later* ("previously absent
from the feature matrix — added here as a strong department-level signal").

**Consequence:** the reported **AUC-ROC of 0.9679**
(`reports/statistical_metrics_summary.md` line 34, "Near-perfect
discrimination") is leakage-inflated and is **not** a valid discrimination
metric. The "71% improvement vs. naive baseline" framing of the Brier score
(0.0710) inherits the same problem. The model is not discovering who
participates; it is reading the answer off a feature.

**Why this matters:** "near-perfect discrimination" is exactly the phrase a
reviewer pattern-matches to leakage. Better to state plainly: the propensity
model is a *calibration device* that reproduces TSJE department rates in a
synthetic population — its AUC is not interpretable as predictive skill.

**Disclosure: Partial.** The propensity model card calls the department feature
"the single strongest predictor"; `epistemic_boundaries.md` marks the artifact
CALIBRATED. Neither says the headline AUC is invalid.

### A2 — Rake-enforced "calibration" reported as validation *(High)*

After Platt scaling, predictions are multiplicatively raked to department
targets (`_rake`, lines 199–241), including an iterative additive correction
when clipping bites (lines 229–239). `_calibration_report` (lines 243–263) then
reports department means — which now match the targets *by construction*.

This is an enforcement step, not an out-of-sample check. Any document that
presents the department-calibration "pass" as evidence of model quality is
describing a tautology. State it as: department aggregates are *pinned* to
anchors; only the within-department spread is model output.

**Disclosure: Partial** (`epistemic_boundaries.md` notes "department rake
applied post-calibration" but not that this makes the calibration report
circular).

### A3 — Clustering: `k=6` unjustified, weak separation, gates fitted to output *(High)*

In `.../pipeline/models/segmentation.py`: `k=6` is hardcoded.
`config/model_params.yaml` declares a `k_range` of `[4..8]`, but no
elbow / silhouette-curve / Davies-Bouldin selection is run — the range is
decorative. Segment label names are assigned post-hoc.

Per `reports/statistical_metrics_summary.md` (line 36) silhouette ≈ 0.26; the
Module A audit report records it at ≈ 0.28. Either way that is **weak**
structure (the conventional 0.26–0.50 band is "weak"; below 0.25 is "no
substantial structure"). The CI gate was lowered from 0.35 to 0.22, and DBSCAN
`eps` widened 0.7 → 2.0 (yielding 0% flagged noise), to match what the synthetic
data actually produces. That is an honest move *as long as it is labeled as
such* — but `epistemic_boundaries.md` presents "silhouette ≥ 0.22" as if 0.22
were a principled bar rather than a post-hoc one.

**Disclosure: Partial** (the Module A audit report is candid about hardcoded
params and gate history; the public-facing docs are not).

### A4 — Arbitrary synthetic-distribution constants; no sensitivity analysis *(Medium)*

In `.../data/generator.py` several distributional choices have no cited source:
structural-dependency base rates (≈ 35% rural / 12% urban), the relation
`NBI_urban = 0.35 · NBI_rural + 0.10`, and language adjustments (≈ +10 pp rural
Guaraní, +8 pp metro Spanish). The IPF "rake" steps then pin national marginals,
which masks whether the *conditional* structure is plausible. No sensitivity
analysis varies any of these constants.

`reports/statistical_independence_note.md` honestly concedes the broader
joint-distribution problem, so this is **Partial** — but the specific
unsourced constants and the absence of a sensitivity sweep are not called out.

### A5 — Config/code drift *(Medium, Disclosed)*

`config/model_params.yaml` declares PCA/DBSCAN/KMeans parameters and split
fractions that are not loaded at runtime; SHAP is declared but not implemented;
reachability weights differ between code and YAML. Fully documented as issue #5
of `audit_report_module_a_2026-05-11.md`. Listed here only for completeness — a
YAML that has no runtime effect creates false confidence.

### A6 — AUC gate declared but never enforced *(Medium, Disclosed)*

`model_params.yaml` states `auc_threshold: 0.70`. No test asserts it (Module A
audit report, lines 141–145). Note this `0.70` is a *floor*, not a measured
value — there is **no** metric contradiction with the measured 0.9679. The real
issue is that the one AUC gate is inert, and (per A1) the metric it would gate
is leakage-inflated anyway.

### A7 — Unstratified calibration/test split *(Low, Disclosed)*

`propensity.py` lines 91–101: the first split is stratified; the cal/test split
(line 99–101) is not. Minor; can skew the Platt calibration set for rare strata.

---

## 5. Module B — Resource Allocation

### B1 — Response-curve parameters are hand-coded priors *(High, Disclosed)*

`.../features/diminishing_returns.py` defines `_SAT_SHARE` (line 33),
`_INFLECTION_PCT` (line 47), `_K_SHAPE` (line 61). These saturation shares,
inflection points and shape constants are design priors, not fitted to any
spend–response data. They set each channel's spend ceiling
(`max_usd = dept_budget · sat_share`), which in turn defines the LP's feasible
region. The whole "optimal allocation" therefore inherits whatever those
dictionaries assert. `reports/response_curve_spec.md` is commendably candid that
no Media-Mix-Model fit was possible. Kept here so the dependency chain
(hand-coded constants → LP feasible region → "optimal" result) is explicit.

### B2 — Scenario "uplift" is mechanically determined *(High, Undisclosed)*

`.../models/allocation.py` `_scenario_week_weight` (lines 203–208):

```
early_lock : 1.15 if week ≤ 5 else 0.95
late_flex  : 0.92 if week ≤ 7 else 1.20
```

These multipliers enter the objective directly. The scenario advantages reported
in `reports/statistical_metrics_summary.md` (early_lock +2.5%, late_flex +6.7%)
are therefore *consequences of these hardcoded weights*, not an empirical
comparison of strategies. As written, the docs read as if the optimizer
*discovered* that early-locking helps. It did not — the analyst told it so. This
must be framed as a what-if parameterization, not a finding.

### B3 — Counterfactual is reallocation, not re-optimization *(Medium, Undisclosed)*

`.../counterfactual.py` shifts a fixed `shift_share` of broadcast spend to
in-person channels and recomputes contacts with a post-hoc unit-cost inference.
It never re-solves the LP, so the reallocated plan is not checked against the
original bundle/reach/coverage constraints — it can be silently infeasible. The
reported "broadcast-to-direct" delta is a hand computation, not an optimization
result, and should be labeled that way.

### B4 — Multiplicative persuasion aggregation is unjustified *(Medium, Undisclosed)*

The objective multiplies `contacts · attention · salience · hostility ·
scenario_w · tier_w`. Multiplicativity (as opposed to additive or
log-additive composition) is a strong functional-form assumption with no
supporting evidence. It should at least be named as an assumption.

### B5 — Hardcoded tier penalties and pay-TV lock *(Medium, Undisclosed)*

Department tier multipliers (≈ 0.55–1.10 across stronghold/swing/opposition/
negligible) and the pay-TV eligibility lock to three departments are hardcoded
in `allocation.py` with no documented rationale. These materially shape the
allocation; their provenance should be in the decision log.

### B6 — Dual values / sensitivity scope *(Low, Disclosed)*

Shadow prices and the budget-expansion curve are correct *for the LP*. They are
not real-world elasticities. Largely covered by `epistemic_boundaries.md`
(allocation = SIMULATED, "persuasion-adjusted contacts are a proxy metric").

---

## 6. Module C — Probabilistic Forecasting

### C1 — Central interval shipped under HDI column names *(High, Undisclosed)*

`.../models/tracking/hierarchical.py` `export_daily_posterior_table`
(lines 110–135) computes `post.quantile(0.05)` and `post.quantile(0.95)`
(lines 117–118) and writes them to columns named `posterior_hdi_low_pp` /
`posterior_hdi_high_pp` (lines 129–131). A 5–95% **central** credible interval
is not a **highest-density interval**. For a skewed posterior they differ. This
is a factual mislabel in a *shipped artifact schema* (`daily_posterior_forecast.parquet`)
and its schema contract. Fix: either compute `az.hdi(...)` or rename the columns
to `..._q05_pp` / `..._q95_pp`.

### C2 — Per-family pollster priors defined but unused *(High, Undisclosed)*

`config/pollster_prior_families.yaml` specifies per-family hyperparameters
(e.g. `capli`, `ica` with distinct `student_nu` / `house_sigma_pp`).
`hierarchical.py` lines 95–96 apply a single global
`house_offset ~ Normal(0, HalfNormal(2.5))` to every pollster. The YAML is never
read by the model. A reviewer who opens that config will assume a sophistication
the code does not implement — worse than not having the file.

### C3 — No convergence diagnostics enforced *(High, Partial)*

`hierarchical.py` lines 99–107 call `pm.sample(...)` and return the
`InferenceData` with no inspection of R-hat, ESS, or divergence count. A smoke
test confirms `az.summary()` runs but asserts no threshold.
`epistemic_boundaries.md` itself concedes "14 NUTS divergences" for the daily
posterior — i.e. a known-non-clean fit is exported with no gate. For a Bayesian
model this is the single most important missing guardrail.

### C4 — Exit-model intercept prior is unjustified *(Medium, Undisclosed)*

`.../models/exit/exit_model.py` line 61: `intercept ~ Normal(mu=60.0,
sigma=15.0)`. A 60-point prior mean is strongly informative and implausible for
a competitive race; no rationale is given. With the few data points an exit
model has, this prior will move the posterior.

### C5 — No prior sensitivity analysis *(Medium, Partial)*

No script in `src/` or `tests/` refits any Module C model under alternative
priors. `METHODOLOGY.md` recommends sensitivity analysis "for high-stakes
decisions"; none is implemented. Given C2 and C4, the priors *are* doing work,
so their influence is currently unquantified.

### C6 — `macro_context_prior.yaml` defined but unused *(Medium, Undisclosed)*

`config/macro_context_prior.yaml` (GDP growth, unemployment, inflation) is
metadata only — never loaded into any model. Same credibility risk as C2.

### C7 — Monte Carlo shock design is arbitrary *(Medium, Partial)*

Shock-score weights (`λ₁=0.08, λ₂=0.35, λ₃=0.12`) and bucket thresholds
(12 pp margin, 0.35 transparency, 0.4 herding) in `.../scenarios/` and
`config/shock_params.yaml` are hardcoded with no sensitivity analysis. The
LogNormal bucket priors are described as "calibrated so bucket means roughly
track empirical observed scores when tracking is dense" — yet they are invoked
precisely when tracking is *sparse*, so the calibration target is not available
when the prior is used. Missing buckets are synthesized from the prior with no
user-facing warning. `epistemic_boundaries.md` calls the multipliers
"illustrative" (hence Partial), but the circular calibration and silent
synthesis are not disclosed.

### C8 — Walk-forward validation is underpowered *(Low, Disclosed)*

Four tracking polls → two holdouts at `min_train_size=2`. A coverage rate over
n=2 (and the Brier 0.528 / log-loss 2.709 in `statistical_metrics_summary.md`,
both flagged ⚠) is not a statistically meaningful estimate. The repo discloses
this in the `walk_forward.py` docstring and `module_c_forecast_validation.md` —
credit for honesty; noted only so it is not mistaken for a real coverage result.

### C9 — Deterministic observation noise *(Low, Undisclosed)*

`hierarchical.py` line 87: `sigma_obs = clip(6.0/sqrt(phi), 1.0, 25.0)` — the
observation SD is a deterministic function of a transparency proxy, not an
estimated parameter. Defensible as a design choice; should be stated as an
assumption (the likelihood cannot widen to reflect data-driven dispersion).

---

## 7. Disclosure-gap analysis (X2)

The repo's honesty is real but uneven. Three tiers:

- **Already disclosed well** — A5, A6, A7 (Module A audit report), B1
  (`response_curve_spec.md`), B6, C8 (`module_c_forecast_validation.md`). A
  reviewer who reads these docs will not feel misled.
- **Partially disclosed — framing too soft** — A1, A2, A3, C3, C7. The artifact
  status is honest, but the *consequence* is understated: "near-perfect
  discrimination" (A1), "silhouette ≥ 0.22" as a principled gate (A3),
  "14 divergences noted as structural" with no mention that nothing checks them
  (C3).
- **Undisclosed** — B2, B3, B4, B5, C1, C2, C4, C6, C9. These are where a sharp
  reviewer finds something the author appears not to have noticed. B2 and C1 are
  the most damaging: B2 because a reported "uplift" is actually an input, C1
  because a shipped column name is factually wrong.

**Highest-value action:** convert the Partial and Undisclosed rows into one or
two honest sentences each in the relevant public doc. Self-disclosed limitations
read as rigor; reviewer-discovered ones read as blind spots.

---

## 8. Documentation-accuracy check (X3)

Specific lines that overstate, with suggested re-framing:

| Location | Current | Problem | Suggested framing |
|----------|---------|---------|-------------------|
| `statistical_metrics_summary.md:34` | "Propensity AUC-ROC 0.9679 — Near-perfect discrimination" | Leakage-inflated (A1) | "AUC is not interpretable as predictive skill; the model is a calibration device." |
| `statistical_metrics_summary.md:35` | "Brier 0.071 → 71% improvement vs naive" | Same leakage inheritance | Report Brier without the "improvement" claim, or alongside the leakage caveat. |
| `statistical_metrics_summary.md` (Module B scenarios) | early_lock +2.5%, late_flex +6.7% | Set by hardcoded weights (B2) | "Scenario weights are analyst inputs; the deltas are what-if parameterizations, not discovered effects." |
| `daily_posterior_forecast.parquet` schema + contract | `posterior_hdi_low_pp` / `posterior_hdi_high_pp` | It is a central interval (C1) | Rename to `_q05_pp` / `_q95_pp`, or compute a true HDI. |
| `epistemic_boundaries.md` (segment row) | "silhouette ≥ 0.22 ... enforced" | 0.22 is a post-hoc floor (A3) | Note the gate was set to the achievable value for synthetic data. |

---

## 9. Prioritized recommendations

Audit only — nothing below has been implemented.

**Must address before any external / hiring review**

1. **A1** — Rewrite every place that reports propensity AUC/Brier as skill.
   State that the propensity model is a calibration device and the department
   feature encodes the prior. Optionally report AUC *without*
   `department_logit_offset` to show the honest discrimination level.
2. **B2** — Re-label scenario "uplift" everywhere as a what-if parameterization
   driven by analyst-set week weights.
3. **C1** — Fix the `posterior_hdi_*` mislabel (rename columns or compute a real
   HDI) and update the schema contract.

**Should address (rigor)**

4. **C2 / C6** — Either wire `pollster_prior_families.yaml` and
   `macro_context_prior.yaml` into the models, or delete them and remove the
   claims they imply.
5. **C3** — Add an R-hat / ESS / divergence gate after `pm.sample()`; fail or
   loudly warn on R-hat > 1.01 or divergences > 0.
6. **A3** — Run and report a k-selection analysis (silhouette curve / elbow over
   k = 2..10); document that the silhouette gate is the synthetic-data
   achievable value.
7. **B3** — State that the counterfactual is a non-re-optimized reallocation, or
   re-solve the LP under the shifted-channel constraints.
8. **A2** — Reframe the department-calibration report as enforcement, not
   validation.

**Nice to have**

9. **A4 / C4 / C5 / C7** — Cite or justify the hand-set constants; add a minimal
   prior-sensitivity sweep for Module C.
10. **B4 / B5 / C9** — Record the multiplicative-aggregation choice, the tier
    penalties, the pay-TV lock, and the deterministic `sigma_obs` as explicit,
    sourced assumptions in `reports/decision_log.md`.
11. **A5 / A6 / A7** — Already disclosed; close out when convenient.

---

## 10. What the project gets right

A rigorous audit is balanced. Genuine strengths:

- **The epistemic taxonomy** (`epistemic_boundaries.md`) — the VERIFIED /
  CALIBRATED / SIMULATED / ILLUSTRATIVE register is unusually disciplined and is
  the right backbone; this audit mostly asks it to descend one level deeper.
- **Honest failure reporting** — the walk-forward miss (C8) and the ⚠-flagged
  Brier/log-loss are reported, not buried.
- **Reproducibility** — fixed seeds, `poetry.lock`, DVC pipeline, run manifests.
- **Schema contracts** — ~19–23 YAML contracts enforce shape, ranges, and
  provenance at module boundaries.
- **Self-auditing culture** — `audit_report_module_a_2026-05-11.md` and
  `statistical_independence_note.md` already do, for parts of the system,
  exactly what this document does for the rest.

The gap is narrow and specific: the project is honest about *what its artifacts
are*, less so about *what its model-internal numbers mean*. Closing the dozen
Partial/Undisclosed rows above turns a good reconstruction into a candid one.

---

## 11. Verification appendix

**Primary sources inspected (read in full):**

- `module_a_population_segmentation/src/population_segmentation/pipeline/models/propensity.py`
- `module_c_forecasting_scenarios/src/module_c_forecasting_scenarios/models/tracking/hierarchical.py`
- `reports/epistemic_boundaries.md`

**Anchors confirmed by targeted inspection:**

- `module_b_resource_allocation/src/module_b_resource_allocation/models/allocation.py:203-208`
  (`_scenario_week_weight`).
- `module_b_resource_allocation/src/module_b_resource_allocation/features/diminishing_returns.py:33,47,61`
  (`_SAT_SHARE` / `_INFLECTION_PCT` / `_K_SHAPE`).
- `module_c_forecasting_scenarios/src/module_c_forecasting_scenarios/models/exit/exit_model.py:61`
  (`intercept ~ Normal(60, 15)`).
- `reports/statistical_metrics_summary.md:34-36` (AUC 0.9679, Brier 0.0710,
  silhouette 0.2566).
- `module_a_population_segmentation/reports/audit_report_module_a_2026-05-11.md:141-145`
  (`auc_threshold: 0.70` declared, not enforced).

**Metrics:** all quoted from repository artifacts; none were independently
re-computed (local environment lacks installed project dependencies). A1 is
established by static analysis and requires no run.

**A6 resolution:** the "0.70" in the Module A audit report is the
`auc_threshold` gate floor in `model_params.yaml`, not a measured AUC. There is
no metric contradiction with the measured 0.9679; A6 is recorded as an
unenforced-gate finding only.
