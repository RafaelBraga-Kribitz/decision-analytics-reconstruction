---
id: IMP-A01
title: "Propensity honesty: non-circular target, real AUC gate, no fabricated variance"
absorbs: [A1, A2, A3]
overlaps_triage: [AUD-A5]
priority: P0
effort: high
depends_on: []
soft_depends_on: []
queue: findings
target_repo: decision-analytics-reconstruction
issue: null
status: draft
---

# IMP-A01 — Propensity Honesty: Non-Circular Target, Real AUC Gate, No Fabricated Variance

`PropensityModel` (`module_a_population_segmentation/src/population_segmentation/pipeline/models/propensity.py`)
has three compounding integrity defects that together mean the published AUC
cannot fail, the CI gate that is supposed to catch that never runs the real
model, and the individual-level spread in the shipped parquet does not match
what any test exercises:

1. **Circular target (A1).** `_synthetic_target` (propensity.py:170-202) builds
   the binary label from `department_deviation`, itself
   `anchors["department_participation_rates"][dept] - national` — the exact
   same `calibration_anchors.department_participation_rates` dict that
   `_feature_matrix` (propensity.py:150-168) encodes as
   `department_logit_offset`, described in its own comment as "a strong
   department-level signal." The label and the strongest feature are two
   views of one lookup table. `model_card_propensity.md:50-63` states this
   plainly ("AUC ≈ 0.89 is not a generalization metric... this is circular")
   but `README.md:58-60` still lists "A7/A8/A9/A10 via propensity tests
   (AUC-ROC > 0.70...)" with no circularity caveat next to the number a
   non-specialist reader sees first.
2. **Fake CI gate (A2).** `tests/test_evaluation.py:25-34` (`test_auc_floor`)
   computes `roc_auc_score` on a hand-written 8-element toy array
   (`y_true = [0,1,0,1,1,0,1,0]`) and asserts `auc >= 0.70`. It never
   constructs a `PropensityModel`, never calls `fit_predict`, and never
   touches `calibration_anchors.yaml`. `model_params.yaml:89` nonetheless
   annotates `auc_floor: 0.70` as `"Gate A8: enforced in CI (see
   test_auc_floor)"` — the comment cites a test that cannot detect a
   regression in the actual model.
3. **Fabricated spread with test/prod parameter drift (A3).**
   `_entity_spread_signal` (propensity.py:248-268) and
   `_spread_within_departments` (propensity.py:270-308) do not recover any
   modeled uncertainty; they z-score eight unrelated demographic/behavioral
   columns, sum them into a composite, and affinely rescale that composite to
   a fixed `individual_spread_std` around each department's raked mean. The
   dataclass default is `0.065` (propensity.py:44). Production overrides this
   to `0.095` via `pipeline/export.py:83,119` reading
   `model_params.yaml:91`'s `individual_spread_std: 0.095`. But
   `tests/test_propensity.py:44` instantiates `PropensityModel(random_state=42)`
   with no override — it exercises the `0.065` default, not the `0.095` value
   that ships in `participation_propensity.parquet`. No test ever runs with
   the production parameter.

## 1. Define the Scope (The Data Guardrails)

**In-Scope:**
- `pipeline/models/propensity.py`: `_synthetic_target`, `_feature_matrix`,
  `_entity_spread_signal`, `_spread_within_departments`, and the
  `individual_spread_std` dataclass field.
- `tests/test_evaluation.py::test_auc_floor` and
  `tests/test_propensity.py` (the `individual_spread_std` parity gap).
- `config/model_params.yaml` propensity block (lines 71-92), specifically the
  `auc_floor` comment and `individual_spread_std` value.
- `README.md:58-60` gate table and `reports/model_card_propensity.md`'s AUC
  disclosure section (lines 50-71) — bringing both into agreement.
- Any CI wiring needed so the AUC gate runs against a real `fit_predict` call.

**Out-of-Scope:**
- Clustering k-selection, DBSCAN parameterization, and stability-metric
  consolidation — `IMP-A03`.
- Categorical feature encoding for distance-based clustering — `IMP-A02`.
- General config-to-runtime wiring (the broader pattern from F-044) —
  `IMP-A06`.
- Redesigning `_rake`'s department-targeting algorithm itself; the rake's
  mechanics are not disputed here, only the label/feature circularity and the
  post-rake spread step.

## 2. Data-Driven "Given-When-Then" Scenarios

**Scenario: Ablation-based honest discrimination metric (Happy Path)**
- **Given** a fitted `PropensityModel` on `feature_df` (Module A feature
  matrix) and `calibration_anchors.yaml`,
- **When** the evaluation step re-fits the model on the same split with
  `department_logit_offset` removed from `FEATURES` (or the label regenerated
  from a held-out set of department anchors not used in `_feature_matrix`),
- **Then** the reported metric is labeled `auc_roc_ablated` (or
  `auc_roc_holdout_anchors`), is distinct from the circular `auc_roc` field
  already in the `metrics` dict, and is the number gated in CI and shown in
  `README.md`'s quality-gate table — not the circular figure.

**Scenario: CI gate runs the real model (Happy Path)**
- **Given** the fixture population used elsewhere in
  `tests/test_propensity.py` (`generate_population` → `inject_flaws` →
  `clean_population` → feature builders, n=15,000, seed=42),
- **When** a new or modified test calls
  `PropensityModel(random_state=42).fit_predict(feature_df, anchors)` and
  reads `out["metrics"]["auc_roc_ablated"]` (or the chosen honest metric),
- **Then** the assertion runs against that real output, not a toy 8-row
  array, and a deliberate leakage regression (e.g., re-adding
  `department_logit_offset` to the ablated feature set) makes the test fail.

**Scenario: Test/production spread parameter parity (Edge Case)**
- **Given** `config/model_params.yaml:91` sets `individual_spread_std: 0.095`
  and `pipeline/export.py:83` reads it into the production `PropensityModel`,
- **When** `tests/test_propensity.py` instantiates `PropensityModel` for any
  gate assertion,
- **Then** it must construct the model with
  `individual_spread_std=<value loaded from model_params.yaml>` (not the bare
  dataclass default), so the exact object under test is the one whose output
  ships in `participation_propensity.parquet`.

## 3. Specify Undesirable Behaviors (Negative Constraints)

**Scenario: Preventing an unlabeled circular AUC from reaching stakeholder-facing docs**
- **Given** `README.md`'s "Quality gates (implemented)" table,
- **When** the table lists any AUC-ROC figure derived from `_synthetic_target`
  and `department_logit_offset` together,
- **Then** the entry must carry an explicit circularity caveat (e.g., "AUC≈0.89,
  circular — see model card §Limitations") or be replaced with the ablated
  metric; a bare `"AUC-ROC > 0.70"` gate with no caveat is a failing state for
  this finding's verification script.

**Scenario: Preventing a CI gate from citing a test it does not exercise**
- **Given** any comment in `config/model_params.yaml` or `README.md` that
  claims a numeric gate is "enforced in CI (see `<test name>`)",
- **When** the verification script statically inspects `<test name>`,
- **Then** the test must import and call the model class the comment
  references (`PropensityModel.fit_predict`), not a hand-built array; a gate
  comment naming a test that never calls the production code path is a
  failing state.

**Scenario: Preventing fabricated dispersion from being confused with modeled uncertainty**
- **Given** `_entity_spread_signal` and `_spread_within_departments`,
- **When** these methods run,
- **Then** their output must be labeled in code comments and the model card as
  a **cosmetic dispersion restoration step**, not "individual variation" or
  "uncertainty" — and the model card's Known Limitations section (currently
  lines 65-70) must state that within-department spread is an affine rescale
  of an unrelated composite z-score, not a posterior or bootstrap-derived
  quantity, until a principled replacement (e.g., prediction-interval-based
  or per-entity bootstrap variance) lands.

## 4. Detail Data-Specific Non-Functional Requirements

- **Model fairness / bias:** `_synthetic_target`'s gender adjustment
  (propensity.py:196, ±0.02) and youth adjustment are zero-sum by
  construction; any replacement evaluation design must preserve that the
  synthetic label does not introduce a new gender or youth skew beyond what
  `calibration_anchors.yaml` already encodes. `N/A` beyond that — no new
  protected-attribute proxy is introduced by this change.
- **Performance & decay:** the ablated/held-out metric must be computable in
  the same `fit_predict` call (no second full model fit beyond one ablated
  refit) so `make module-a-export` runtime does not regress by more than
  ~2x; if a full k-fold-by-department scheme is chosen instead, cap it at 4
  folds (matching the 4 verified departments in
  `calibration_anchors.department_participation_rates`) to bound runtime.
- **Data integrity:** the CI gate script must assert
  `"auc_roc_ablated" in out["metrics"]` (or equivalent honest key) and fail
  if `department_logit_offset` (or any column built from
  `department_participation_rates`) is present in the feature set used to
  compute it. `individual_spread_std` used in any test must be read from
  `config/model_params.yaml`, not hardcoded, so a future YAML edit cannot
  silently desync test coverage from production again.
- **Reproducibility:** all changes preserve determinism under
  `random_state=42` — the ablated metric, like the existing `auc_roc`, must
  be bit-reproducible across runs given the same `df`/`anchors`/seed.

## 5. Queue Stub (ready to file)

```yaml
id: F-XXX            # assigned at filing time
title: "Propensity AUC gate is circular and untested; production spread param untested"
category: fake_completion
kind: recurrence_invariant
status: open
opened_at: 2026-07-08
closed_at: null
recurrence_count: 0
evidence: |
  propensity.py:170-202 _synthetic_target derives the binary label from
  anchors["department_participation_rates"]; propensity.py:150-168
  _feature_matrix encodes the same dict as department_logit_offset, the
  strongest feature (model_card_propensity.md:46-48). AUC ~0.89 is therefore
  circular, as model_card_propensity.md:50-63 itself documents, but
  README.md:58-60 states "AUC-ROC > 0.70" with no caveat.
  tests/test_evaluation.py:25-34 test_auc_floor computes roc_auc_score on a
  hand-built 8-element array and never calls PropensityModel.fit_predict;
  model_params.yaml:89 claims "Gate A8: enforced in CI (see test_auc_floor)" —
  false, the test cannot detect a model regression.
  propensity.py:44 individual_spread_std default is 0.065; export.py:83,119
  override to 0.095 via model_params.yaml:91 in production;
  tests/test_propensity.py:44 constructs PropensityModel(random_state=42)
  with no override, so the shipped participation_propensity.parquet spread
  (0.095) is never exercised by any test.
verification_script: scripts/check_propensity_gate_integrity.py
notes: |
  Proposed script behavior: (1) parse tests/test_evaluation.py and confirm
  test_auc_floor (or its replacement) imports PropensityModel and calls
  fit_predict — fail if the AUC assertion operates on a literal/inline array;
  (2) load config/model_params.yaml, read propensity.individual_spread_std,
  and grep tests/test_propensity.py for a PropensityModel(...) construction
  that passes that same value (fail if only the bare dataclass default is
  used in any assertion touching spread/variance); (3) grep README.md for an
  AUC-ROC gate line and require either a circularity caveat string or removal
  of the raw figure in favor of an "_ablated"/"_holdout" key.
  Spec: governance/improvement_plan/IMP-A01_propensity-honesty.md
  Related: F-052 (closed) fixed collapsed within-department variance by
  introducing individual_spread_std; this finding is about the evaluation
  design and test/prod parity around that same mechanism, not its existence.
```
