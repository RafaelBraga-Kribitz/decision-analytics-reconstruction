---
id: IMP-V03
title: "SHAP artifact provenance: remove the fabricated-data generator that can silently overwrite the real SHAP chart"
absorbs: [V5]
overlaps_triage: [AUD-SHAP]
priority: P0
effort: low
depends_on: []
soft_depends_on: []
queue: findings
target_repo: decision-analytics-reconstruction
issue: null
status: draft
---

# IMP-V03 — SHAP Artifact Provenance

Two scripts write to the same published artifact path
`reports/module_a/shap_summary.png`:

- `scripts/generate_module_a_report_charts.py:57-98` — the **real** generator,
  computing SHAP values from the actual fitted propensity model on real
  pipeline features;
- `scripts/generate_module_a_shap.py:27-37` — an orphan generator that fits a
  throwaway `LogisticRegression` on `rng.normal(size=(800, 6))` **fabricated
  data** and writes a SHAP plot of that noise to the identical path.

Running the wrong script (the names are near-identical; neither is
disambiguated by a Makefile target) replaces a published model-evidence
artifact with fabricated content, silently. This is the same
`fake_completion`-class integrity hazard the governance system exists to
prevent (cf. F-070, the fabricated heatmap formula).

## 1. Define the Scope (The Data Guardrails)

**In-Scope:**
- Deletion (or explicit quarantine outside `scripts/`) of
  `scripts/generate_module_a_shap.py`.
- A single, unambiguous canonical producer for
  `reports/module_a/shap_summary.png`, registered in
  `governance/FIGURE_MANIFEST.yaml` with `generator:` pointing at
  `scripts/generate_module_a_report_charts.py`.
- A recurrence invariant (verification script) that fails if any file under
  `scripts/` other than the canonical generator writes to
  `reports/module_a/shap_summary.png`, or if the manifest entry is missing.

**Out-of-Scope:**
- The visual design of the SHAP chart itself (labeling of model/target —
  that is triage row AUD-SHAP's residual slice, executed with IMP-V05).
- The statistical validity of the propensity model the SHAP values explain
  (IMP-A01).
- General manifest-coverage enforcement for all figures (IMP-V02).

## 2. Data-Driven "Given-When-Then" Scenarios

**Scenario: Canonical SHAP regeneration (Happy Path)**
- **Given** a completed Module A pipeline run with a fitted propensity model
  and the feature matrix used in production,
- **When** the canonical generator (`scripts/generate_module_a_report_charts.py`)
  runs,
- **Then** `reports/module_a/shap_summary.png` is regenerated from the fitted
  model's SHAP values on real features, and the figure's manifest entry
  (`governance/FIGURE_MANIFEST.yaml`) names exactly this script as its sole
  `generator`.

**Scenario: Attempted fabricated regeneration (Edge Case)**
- **Given** the historical orphan script (or any successor) that synthesizes
  its own input data,
- **When** the recurrence-invariant verification script runs (locally via
  `make verify` or in the Adversary CI job),
- **Then** it exits non-zero, naming the offending file and the artifact path
  collision, before any PR containing such a script can merge.

## 3. Specify Undesirable Behaviors (Negative Constraints)

**Scenario: Preventing silent artifact overwrite by non-canonical producers**
- **Given** any script, notebook, or test in the repository other than the
  manifest-registered generator,
- **When** it attempts to write to a path registered in
  `governance/FIGURE_MANIFEST.yaml`,
- **Then** the verification layer must flag it — a published figure path may
  have exactly one producer; two producers for one path is a failing state
  regardless of which one "usually" runs.

**Scenario: Preventing synthetic stand-in data in published evidence artifacts**
- **Given** a chart whose manifest entry classifies it as model evidence,
- **When** its generator is inspected (statically) for data provenance,
- **Then** the generator must consume pipeline artifacts (parquet/CSV outputs
  or the fitted model), never module-local `numpy.random` draws; a generator
  that fabricates its input must either be deleted or its output relabeled
  and relocated as an explicitly synthetic illustration, outside
  `reports/module_a/`.

## 4. Detail Data-Specific Non-Functional Requirements

- **Model fairness / bias:** N/A — no model behavior changes; this is an
  artifact-provenance guarantee.
- **Performance & decay:** the verification script is static analysis only
  (no model fitting) and must complete in < 5 s so it adds negligible cost to
  `make verify` and the Adversary job.
- **Data integrity:** `reports/module_a/shap_summary.png` must be traceable to
  a single generator and a real pipeline run; the manifest entry is the
  authority. Absence of the manifest entry, or a second writer, is an abort
  condition for the governance gate.
- **Reproducibility:** regenerating the SHAP chart from the same pipeline run
  (fixed seed 42 upstream) must be deterministic; the generator must not
  introduce its own unseeded randomness (e.g., unseeded SHAP sampling).

## 5. Queue Stub (ready to file)

```yaml
id: F-XXX            # assigned at filing time
title: "Fabricated-data SHAP generator can silently overwrite the real model-evidence chart"
category: fake_completion
kind: recurrence_invariant
status: open
opened_at: <filing date>
closed_at: null
recurrence_count: 0
evidence: |
  scripts/generate_module_a_shap.py:27-37 fits a throwaway LogisticRegression
  on rng.normal(size=(800, 6)) synthetic data and writes the resulting SHAP
  summary plot to reports/module_a/shap_summary.png — the same path produced
  by the real generator scripts/generate_module_a_report_charts.py:57-98,
  which uses the actual fitted propensity model. Neither script is
  disambiguated by a Makefile target; running the wrong one replaces a
  published evidence artifact with fabricated content, with no error.
verification_script: scripts/check_shap_artifact_provenance.py
notes: |
  Proposed script behavior: (1) assert scripts/generate_module_a_shap.py does
  not exist; (2) parse governance/FIGURE_MANIFEST.yaml and assert
  reports/module_a/shap_summary.png has exactly one generator entry, equal to
  scripts/generate_module_a_report_charts.py; (3) grep scripts/ and
  reports/**/*.py for any other writer of that path and fail on a match.
  Spec: governance/improvement_plan/IMP-V03_shap-provenance.md
```
