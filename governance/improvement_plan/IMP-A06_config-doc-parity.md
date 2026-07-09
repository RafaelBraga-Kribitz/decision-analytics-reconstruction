---
id: IMP-A06
title: "Config-runtime parity and documentation truth for Module A"
absorbs: [A16, A17, A18]
overlaps_triage: []
priority: P1
effort: medium
depends_on: []
soft_depends_on: []
queue: findings
target_repo: decision-analytics-reconstruction
issue: null
status: draft
---

# IMP-A06 — Config-Runtime Parity & Documentation Truth

Module A's configuration file, README, model cards, and notebooks make claims
the code does not honor. Three defect groups:

1. **Config not wired (A16).** `module_a_population_segmentation/config/model_params.yaml:8-15`
   states most PCA/DBSCAN/KMeans/propensity-CV parameters are "NOT yet wired to
   runtime loading (code defaults match)" — and they have already drifted:
   `bootstrap_n_samples: 100` (`model_params.yaml:68`) versus the hardcoded
   `range(25)` loop in
   `src/population_segmentation/pipeline/models/segmentation.py:342`, a 4×
   disagreement between the documented and executed parameter. F-044 closed
   the general pattern without a config loader being built.
2. **README contradicts the model card (A17).** `README.md:58-60` advertises
   "AUC-ROC > 0.70, Brier < 0.22, reliability deviation < 3 pp" as enforced
   gates, while `reports/model_card_propensity.md:23,50-63` demotes AUC to
   informational (circularity, see IMP-A01) and sets the real Brier bar at
   < 0.237. `README.md:47-51` links four reports that do not exist anywhere in
   the repository (`segment_action_matrix.md`, `transformation_log.md`,
   `decision_log.md`, `statistical_independence_note.md`), and the repeated
   "14-step cleaning" claim is unverifiable — `data/cleaner.py:222-241` chains
   roughly 9–10 discrete transformations.
3. **Notebooks are stubs or stale (A18).** Four of five notebooks contain a
   single markdown title cell and no analysis; the one substantive notebook
   (`01_end_to_end_walkthrough.ipynb`) references columns (`sex`,
   `has_cedula`, `is_rural`, `education_level`) and segment labels
   (`high_reach_urban`, `rural_low_contact`) that exist nowhere in the current
   schema or `SEGMENT_LABEL_MAP` — it would fail with `KeyError` if executed.

This is the `fake_completion` / documentation-drift class the governance
system targets: a reader trusting the doc surface gets numerically wrong,
methodologically over-confident information.

## 1. Define the Scope (The Data Guardrails)

**In-Scope:**
- Every parameter key in `config/model_params.yaml` either (a) loaded at
  runtime by the code path it describes, or (b) removed from the YAML (with
  the code default documented inline in the code, not the config).
- One source of truth for each quality gate: README quotes the model card (or
  links it) instead of restating numbers; every stated threshold matches the
  value a test or gate actually enforces.
- README links resolve: nonexistent report links removed or the reports
  written; the "14-step" claim replaced by an accurate, verifiable count or a
  link to the cleaner's own transformation list.
- Notebooks: each stub notebook is either populated with real, executable
  diagnostics or deleted; the walkthrough notebook updated to the current
  schema and label vocabulary (or deleted with its purpose folded into the
  README).
- A recurrence invariant (verification script) that checks config-code parity
  for the named keys and that README gate lines match the model-card values.

**Out-of-Scope:**
- Changing any gate's *value* (silhouette/ARI levels are IMP-A03; propensity
  gates are IMP-A01). This document makes claims truthful, not different.
- The content of the propensity evaluation itself (IMP-A01).
- Cross-module schema contracts (IMP-C07).

## 2. Data-Driven "Given-When-Then" Scenarios

**Scenario: Config value drives the run (Happy Path)**
- **Given** `config/model_params.yaml` sets `bootstrap_n_samples: 100`,
- **When** the segmentation pipeline computes bootstrap stability,
- **Then** exactly 100 bootstrap iterations execute (observable in the model
  run manifest's recorded parameters), and changing the YAML value to 50
  changes the executed count to 50 on the next run without a code edit.

**Scenario: Gate statement traceability (Happy Path)**
- **Given** any quality-gate number stated in `README.md`,
- **When** the parity verification script cross-references it,
- **Then** an identical value exists in the authoritative surface it cites
  (model card table or config key), and the script exits 0 only when every
  stated gate resolves.

**Scenario: Stale notebook (Edge Case)**
- **Given** a committed notebook under `module_a_population_segmentation/notebooks/`,
- **When** it is executed top-to-bottom against the current pipeline outputs,
- **Then** it completes without `KeyError`/`FileNotFoundError`, or the
  notebook is not in the repository. A notebook that cannot run against
  current artifacts is a failing state, not documentation.

## 3. Specify Undesirable Behaviors (Negative Constraints)

**Scenario: Preventing config-as-decoration**
- **Given** a YAML key that describes a model hyperparameter,
- **When** no runtime loader consumes it,
- **Then** the key must not exist in the config file. A config key that the
  code ignores is a false affordance — the next maintainer will "tune" it and
  observe no effect, or worse, believe they changed production behavior.

**Scenario: Preventing gate inflation in public docs**
- **Given** the README or any module-level doc surface,
- **When** it states an acceptance gate,
- **Then** it must not state a stricter, looser, or differently-scoped value
  than the enforced one, and must not present an informational metric (e.g.,
  the circular AUC) as an enforced gate.

**Scenario: Preventing dead links as evidence**
- **Given** a doc claims "see report X" as evidence for a methodology claim,
- **When** X does not exist in the repository,
- **Then** the claim and link must be removed together — an unverifiable
  citation is treated the same as an unverifiable navigation claim under the
  CLAUDE.md anti-patterns.

## 4. Detail Data-Specific Non-Functional Requirements

- **Model fairness / bias:** N/A — no model behavior changes; parameter
  wiring must be value-preserving at switchover (first wired run reproduces
  the previous code-default behavior when YAML values equal the old defaults).
- **Performance & decay:** the parity verification script is static (YAML
  parse + source scan + README grep) and must run in < 5 s inside
  `make verify`; notebook execution checks may run only in the scheduled CI
  lane if they exceed 60 s.
- **Data integrity:** the model run manifest must record the effective
  hyperparameters actually used (post-wiring), so any future config/code
  divergence is observable in artifacts rather than requiring source
  archaeology.
- **Reproducibility:** with an unchanged YAML, two runs record identical
  effective-parameter blocks in the manifest.

## 5. Queue Stub (ready to file)

```yaml
id: F-XXX            # assigned at filing time
title: "Module A config keys, README gates, and notebooks contradict runtime behavior"
category: fake_completion
kind: recurrence_invariant
status: open
opened_at: <filing date>
closed_at: null
recurrence_count: 0
evidence: |
  config/model_params.yaml:8-15 admits hyperparameters are not wired to
  runtime; bootstrap_n_samples: 100 (yaml:68) vs range(25) hardcoded at
  pipeline/models/segmentation.py:342. README.md:58-60 advertises
  "AUC-ROC > 0.70, Brier < 0.22" as enforced gates while
  reports/model_card_propensity.md:23,50-63 demotes AUC (circularity) and
  sets Brier < 0.237. README.md:47-51 links four nonexistent reports. Four of
  five notebooks are single-cell stubs; 01_end_to_end_walkthrough.ipynb
  references columns and segment labels that do not exist in the current
  schema (would KeyError). F-044 closed the config-wiring pattern without a
  loader being built.
verification_script: scripts/check_module_a_config_doc_parity.py
notes: |
  Proposed script behavior: (1) parse model_params.yaml and, for each key in
  a named parity list (bootstrap_n_samples, kmeans/dbscan/pca params,
  propensity CV params), assert a runtime loader call site exists and no
  conflicting hardcoded literal remains at the known call sites; (2) extract
  gate numbers from README.md and assert equality with the model-card /
  config values they cite; (3) assert none of the four dead report links
  remains in README.md; (4) assert each committed Module A notebook either
  executes clean under nbclient against current fixtures or has been removed
  (CI-lane check, skippable locally via env flag).
  Spec: governance/improvement_plan/IMP-A06_config-doc-parity.md
```
