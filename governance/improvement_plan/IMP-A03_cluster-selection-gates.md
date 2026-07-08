---
id: IMP-A03
title: "Clustering model selection & quality-gate integrity"
absorbs: [A4, A6, A7, A8, A9]
overlaps_triage: [AUD-A2, AUD-A7, AUD-A8]
priority: P1
effort: high
depends_on: [IMP-A02, IMP-A05]
soft_depends_on: []
queue: dual
target_repo: decision-analytics-reconstruction
issue: 55
status: draft
---

# IMP-A03 — Clustering Model Selection & Quality-Gate Integrity

Five defects in `pipeline/models/segmentation.py` and its evaluation
scaffolding combine into confirmation-bias-by-construction: the number of
clusters is fixed to match a pre-written label vocabulary, the density
parameter is justified by an ad hoc multiplier rather than a diagnostic, the
stability gates were lowered after the fact to whatever the code produced,
two incompatible implementations of the same stability metric coexist, and
two additional quality metrics are fully implemented and unit-tested but
wired into nothing that gates anything.

1. **k hardcoded to match label vocabulary (A4).** `KMeansSegmenter.k`
   defaults to `_MODEL_PARAMS.get("kmeans", {}).get("default_k", 6)`
   (segmentation.py:287) and `build_segmentation_frame`'s own signature
   defaults `k: int = 6` (segmentation.py:368); `pipeline/export.py:106`
   passes `k=6` explicitly. `model_params.yaml:53` documents
   `k_range: [4, 5, 6, 7, 8]` as if a sweep occurs, but no code in the
   repository iterates that list — `k` is a constant everywhere it is used.
   The constant is not arbitrary: `SEGMENT_LABEL_MAP` (segmentation.py:40-47)
   names exactly six segments, and `assign_segment_labels`
   (segmentation.py:175-212) plus the hand-tuned `LABEL_SCORE_WEIGHTS`
   (segmentation.py:52-59) forcibly map whatever six clusters KMeans finds
   onto those six names via Hungarian assignment — then
   `_repair_committed_opposition` and `_repair_rural_committed`
   (segmentation.py:117-172) swap labels again if the Hungarian result still
   does not match the intended semantics (F-052/F-051 both had to patch this
   repair logic; the triage row AUD-A8 already flags
   `structurally_dependent_bloc`'s name as still not matched by its cluster's
   actual profile). This is model selection reverse-engineered from a label
   list, not from data.
2. **DBSCAN parameters justified by a rule of thumb, not a diagnostic (A6).**
   `dbscan.eps: 2.0` is commented (`model_params.yaml:34-36`) as "~10x the
   empirical 5th-percentile of k=5 nearest-neighbor distances... at n=10k
   (p5≈0.17)" — a heuristic multiplier, not a k-distance elbow plot.
   `min_samples: 5` is justified only as "the 2·dim rule (=26) is too
   aggressive in reduced-dim space" (`model_params.yaml:37-38`) — a
   rejection of one heuristic in favor of an arbitrary lower bound, with no
   sensitivity analysis shown.
3. **Gates set after seeing the result, inconsistently (A7).** The
   silhouette gate was lowered from 0.35 to 0.22
   (`model_params.yaml:59-63`: "The original gate of 0.35 was only satisfied
   by clipping the raw metric — removed"; 0.22 is annotated as "no
   substantial structure" on the standard Kaufman–Rousseeuw silhouette
   scale). The bootstrap-ARI gate was similarly lowered from 0.80 to 0.77 in
   the model card language pattern, but `tests/test_segmentation.py:92`
   enforces `> 0.70`, not `0.77` — the YAML comment
   (`model_params.yaml:64-67`), the model card, and the enforced test
   disagree on what the "real" gate is.
4. **Two incompatible bootstrap-ARI implementations (A8).** Production uses
   `KMeansSegmenter._bootstrap_ari` (segmentation.py:331-363): mean ARI
   between two *independently re-fit* 80% subsamples compared on their
   overlap only ("subsample-overlap ARI", chosen for BLAS/platform
   stability per its docstring). `evaluation/clustering_metrics.py:37-71`
   (`compute_bootstrap_ari`) implements a different metric entirely: ARI
   between a fixed *reference* labeling and a bootstrap refit
   ("reference-labeling ARI"). Both are unit-tested
   (`tests/test_evaluation.py:37+`, `test_clustering_metric_functions`) but
   only the first is wired into `build_segmentation_frame`'s exported
   `metrics_dict`. Two different numbers could both be called "bootstrap
   ARI" in a report and neither reviewer would know which one without
   reading the source.
5. **Fully-implemented, unit-tested, unwired diagnostics (A9).**
   `compute_davies_bouldin` and `compute_calinski_harabasz`
   (`evaluation/clustering_metrics.py:74-113`) and
   `population_stability_index` (`evaluation/psi.py:8-41`) exist, have
   passing unit tests, and are called by nothing in `pipeline/export.py` or
   `build_segmentation_frame`. They neither gate anything nor appear in any
   exported manifest or report.

## 1. Define the Scope (The Data Guardrails)

**In-Scope:**
- `KMeansSegmenter` and `DBSCANNoiseFilter` (segmentation.py:249-329,
  285-329) and `build_segmentation_frame` (segmentation.py:366-423).
- `model_params.yaml`'s `kmeans` and `dbscan` blocks (lines 33-69) and the
  gate-threshold comments therein.
- `evaluation/clustering_metrics.py` (all four functions) and
  `evaluation/psi.py`.
- `tests/test_segmentation.py`'s silhouette/ARI assertions (lines 75-92) and
  their relationship to `model_card_segmentation.md`.
- `assign_segment_labels`, `LABEL_SCORE_WEIGHTS`, and the two `_repair_*`
  functions only insofar as they depend on which `k` is selected — the
  Hungarian-assignment *mechanism* itself is not in scope (see Out-of-Scope).

**Out-of-Scope:**
- The categorical-encoding fix to `FEATURE_COLUMNS` — `IMP-A02`, a hard
  dependency: k-selection and DBSCAN re-tuning must run against the corrected
  (one-hot) feature matrix, not the current Euclidean-over-ordinal-nominal
  space, or the diagnostic curves this finding demands would need to be
  redone anyway.
- The fixed-reference scaling fix to `reachability_tier` and
  `nbi_stress_prior_scaled` — `IMP-A05`, a soft-adjacent hard dependency: two
  of the thirteen `FEATURE_COLUMNS` are current-run-relative
  (reachability.py:98-102, behavioral.py:36-41), and any PCA
  explained-variance / eps diagnostic computed before that fix would need
  re-validation once those columns become fixed-reference.
- Whether `rural_committed`, `committed_opposition`, etc. are the *right*
  six label names semantically — that is triage row AUD-A8's residual
  slice, tracked separately; this finding only requires that k and DBSCAN
  parameters be chosen from data, and that the gates/metrics be internally
  consistent, regardless of what k the data-driven sweep ultimately selects.
- Propensity model gates — `IMP-A01`.

## 2. Data-Driven "Given-When-Then" Scenarios

**Scenario: Data-driven k selection actually sweeps k_range (Happy Path)**
- **Given** `model_params.yaml`'s `kmeans.k_range: [4, 5, 6, 7, 8]` and the
  PCA-reduced feature matrix `x` from `_matrix(df)` (post `IMP-A02`/`IMP-A05`),
- **When** a k-selection routine fits `KMeansSegmenter` for each `k` in
  `k_range` and records `silhouette` and `bootstrap_ari` per `k`,
- **Then** the exported artifact (e.g. `data/processed/k_selection_report.json`
  or a report section) shows all five `k` values with their metrics, and the
  `k` used downstream in `build_segmentation_frame` is the one satisfying a
  **pre-registered** selection rule (e.g. "highest silhouette subject to
  `bootstrap_ari > <floor>` and all `segment_share > 0.01`") written into
  `model_params.yaml` *before* the sweep is (re-)run — not chosen to match
  `SEGMENT_LABEL_MAP`'s six names.

**Scenario: DBSCAN eps chosen from a k-distance elbow, not a multiplier (Happy Path)**
- **Given** the PCA(5)-reduced feature matrix,
- **When** a k-distance diagnostic (sorted distance to the `min_samples`-th
  nearest neighbor, plotted or tabulated) is computed,
- **Then** `dbscan.eps` in `model_params.yaml` is set to the elbow point
  identified in that diagnostic (recorded as a percentile or explicit
  distance value with the diagnostic artifact referenced in the YAML
  comment), replacing the "~10x the 5th percentile" heuristic
  (`model_params.yaml:34-36`).

**Scenario: Selection criteria recorded before re-running the sweep (Edge Case)**
- **Given** a fresh feature matrix (post `IMP-A02`/`IMP-A05`) where the old
  k=6/eps=2.0 choices are no longer known to be valid,
- **When** the k-sweep and eps-diagnostic are executed,
- **Then** the selection rule (e.g., silhouette-maximizing k subject to a
  floor) must already exist in a committed file *before* the sweep's numeric
  results are known — the verification script checks that the commit
  introducing the selection rule predates or is co-committed with (not
  subsequent to) the commit recording the chosen `k`/`eps`, preventing
  post-hoc rule-fitting.

## 3. Specify Undesirable Behaviors (Negative Constraints)

**Scenario: Preventing gate thresholds set to match observed output**
- **Given** any change to `silhouette_threshold` or `bootstrap_ari_threshold`
  in `model_params.yaml`,
- **Then** the model card's documented threshold, `model_params.yaml`'s
  comment, and the enforced value in `tests/test_segmentation.py` must all
  be numerically identical — the finding's verification script fails if it
  finds three different numbers (as currently: YAML comment says 0.77, test
  enforces 0.70) purporting to be "the bootstrap-ARI gate."

**Scenario: Preventing two conflicting metrics with the same name**
- **Given** `KMeansSegmenter._bootstrap_ari` (subsample-overlap ARI) and
  `evaluation.clustering_metrics.compute_bootstrap_ari` (reference-labeling
  ARI),
- **When** either is referenced in a report, docstring, or export manifest,
- **Then** the name used must disambiguate the method (e.g.
  `bootstrap_ari_subsample_overlap` vs `bootstrap_ari_reference_labeling`),
  and exactly one must be designated canonical in `model_params.yaml` for
  gating purposes; the other is either deleted or explicitly kept as a
  secondary diagnostic under its disambiguated name.

**Scenario: Preventing implemented-but-dead quality metrics from implying coverage that does not exist**
- **Given** `compute_davies_bouldin`, `compute_calinski_harabasz`, and
  `population_stability_index`, all unit-tested,
- **When** `build_segmentation_frame`'s `metrics_dict` or any export manifest
  is inspected,
- **Then** either these three functions are called and their outputs appear
  in the exported metrics/manifest (with documented thresholds, even if
  initially informational-only), or they are removed along with their tests
  — a unit-tested function with zero production call sites is a failing
  state for this finding's verification script.

## 4. Detail Data-Specific Non-Functional Requirements

- **Model fairness / bias:** `N/A` for the selection-mechanics slice
  (k-sweep, eps diagnostic) directly; however, re-running k-selection may
  change which entities land in which segment, so the PR must report
  `rural_flag`/`gender_encoded`(-derived)/`youth_flag` mean shifts per
  segment before/after, matching the bias-drift check already required by
  `IMP-A02`.
- **Performance & decay:** a full k-sweep over 5 values plus 25-bootstrap ARI
  each (`bootstrap_n_samples: 100` documented but `range(25)` hardcoded at
  segmentation.py:342 — a pre-existing drift this finding does not need to
  fix, only not worsen) must complete in a bounded time budget; document the
  sweep's wall-clock cost at n=15,000 in the PR and gate CI runtime if the
  sweep runs there.
- **Data integrity:** the DBSCAN `max_noise_rate: 0.01` gate
  (`model_params.yaml:44`) must still be checked against whatever `eps` the
  elbow diagnostic selects — if the elbow-derived `eps` pushes noise rate
  above 1%, the selection rule must say what happens (re-diagnose, or accept
  documented higher noise with rationale), not silently pass.
- **Reproducibility:** the k-sweep and eps diagnostic must be deterministic
  under `random_state=42`; the k-selection report/artifact must be
  regeneratable byte-for-byte (or metric-for-metric within floating-point
  tolerance) from the same feature matrix and seed.

## 5. Queue Stub (ready to file)

This finding splits across both queues. The **finding** (governance-class)
owns the gate-inconsistency and dead-metric slice (A7/A8/A9) — these are
integrity/consistency defects fixable without new modeling judgment. The
**issue** (feature-class) owns the re-selection slice (A4/A6) — choosing a
new `k` and DBSCAN parameters is a modeling decision requiring the
`IMP-A02`/`IMP-A05` feature-matrix fixes to land first.

### Finding slice (A7, A8, A9 — gate/metric integrity)

```yaml
id: F-XXX            # assigned at filing time
title: "Clustering gate thresholds inconsistent across YAML/model-card/tests; dead stability metrics unwired"
category: fragmented_standards
kind: recurrence_invariant
status: open
opened_at: 2026-07-08
closed_at: null
recurrence_count: 0
evidence: |
  model_params.yaml:59-67 documents silhouette gate lowered 0.35->0.22 and
  bootstrap-ARI gate as 0.77, but tests/test_segmentation.py:92 enforces
  bootstrap_ari > 0.70 — three sources (YAML comment, model card, enforced
  test) disagree on the bootstrap-ARI number. Two incompatible ARI
  implementations coexist: segmentation.py:331-363 KMeansSegmenter._bootstrap_ari
  (subsample-overlap) vs evaluation/clustering_metrics.py:37-71
  compute_bootstrap_ari (reference-labeling) — both unit-tested, only the
  first wired to production. evaluation/clustering_metrics.py:74-113
  (Davies-Bouldin, Calinski-Harabasz) and evaluation/psi.py:8-41 (PSI) are
  implemented and unit-tested but called from no production code path.
verification_script: scripts/check_clustering_gate_consistency.py
notes: |
  Proposed script behavior: (1) parse model_params.yaml's
  kmeans.bootstrap_ari_threshold and silhouette_threshold, grep
  tests/test_segmentation.py's corresponding assert thresholds, and fail on
  any numeric mismatch; (2) grep reports/model_card_segmentation.md for the
  same two gate numbers and fail on mismatch there too; (3) confirm exactly
  one of KMeansSegmenter._bootstrap_ari / compute_bootstrap_ari is called
  from pipeline/export.py or segmentation.py production code, and that any
  second implementation is named distinctly in its docstring/module comment;
  (4) for compute_davies_bouldin, compute_calinski_harabasz, and
  population_stability_index, grep pipeline/export.py and segmentation.py
  for call sites — fail if a tested function has zero production callers,
  unless it appears in an explicit governance/DEAD_METRICS.md allowlist with
  a removal-or-wire-by date.
  Spec: governance/improvement_plan/IMP-A03_cluster-selection-gates.md
  Triage: AUD-A7 (approved_revisions), AUD-A8 (approved_revisions).
```

### Issue slice (A4, A6 — data-driven re-selection)

**GitHub Issue body:**

```markdown
### Problem

`k=6` and `dbscan.eps=2.0`/`min_samples=5` are hardcoded constants, not the
output of any selection sweep, despite `model_params.yaml` documenting a
`k_range: [4, 5, 6, 7, 8]` that nothing iterates. `k=6` was chosen to match
the six-name `SEGMENT_LABEL_MAP`, and the Hungarian-assignment label-repair
logic (`_repair_committed_opposition`, `_repair_rural_committed`,
segmentation.py:117-172) exists specifically to force whatever clusters
KMeans finds into that pre-written vocabulary — model selection driven by
label count, not data.

### Evidence

- `pipeline/models/segmentation.py:287` — `KMeansSegmenter.k` defaults from
  `model_params.yaml`'s `default_k: 6`.
- `pipeline/export.py:106` — `k=6` passed explicitly.
- `config/model_params.yaml:53-54` — documents `k_range` that is never swept.
- `pipeline/models/segmentation.py:40-59` — `SEGMENT_LABEL_MAP` (6 names)
  and `LABEL_SCORE_WEIGHTS`.
- `pipeline/models/segmentation.py:117-172` — `_repair_committed_opposition`,
  `_repair_rural_committed` forcibly swap labels post-hoc when Hungarian
  assignment doesn't match intended semantics (F-051 showed repairs can
  still fail — see triage row AUD-A8).
- `config/model_params.yaml:33-38` — `dbscan.eps=2.0` justified as "~10x the
  5th-percentile kNN distance"; `min_samples=5` chosen only by rejecting the
  "2×dim=26" rule as "too aggressive," with no k-distance elbow diagnostic.

### Acceptance Criteria

1. **Depends on `IMP-A02` and `IMP-A05` landing first** (feature matrix must
   use one-hot categorical encoding and fixed-reference scaling before this
   sweep is meaningful).
2. A k-sweep over `model_params.yaml`'s `k_range` computes silhouette and
   bootstrap-ARI (the single canonical metric fixed by this doc's finding
   slice) for each `k`, and a pre-registered selection rule (documented in
   `model_params.yaml` before the sweep's numeric results are recorded)
   picks the final `k`.
3. A k-distance diagnostic (sorted `min_samples`-NN distances in PCA(5)
   space) replaces the "~10x 5th-percentile" heuristic for `dbscan.eps`; the
   elbow point and the diagnostic artifact are referenced in
   `model_params.yaml`'s comment.
4. If the sweep selects `k != 6`, `SEGMENT_LABEL_MAP` and
   `LABEL_SCORE_WEIGHTS` are updated to the new cluster count, and the
   `_repair_*` functions are re-validated against the new label set (or
   removed if the new `k`/feature-matrix combination no longer needs
   post-hoc repair — report which, with silhouette/ARI evidence).
5. `max_noise_rate: 0.01` (`model_params.yaml:44`) is re-checked against the
   new `eps`; if noise rate exceeds 1%, the PR states the resolution.

### Verification

Re-run `pytest module_a_population_segmentation/tests/test_segmentation.py`
against the new `k`/`eps` and the new feature matrix; report before/after
silhouette, bootstrap-ARI, noise_rate, and segment_share deltas in the PR
description.

Spec: `governance/improvement_plan/IMP-A03_cluster-selection-gates.md`
```

**Labels:** `type:refactor`, `skill:module-a`, `effort:high`, `priority:p1`,
`status:blocked` (depends on `IMP-A02` and `IMP-A05`; do not apply
`status:claude-ready` until both have merged).
