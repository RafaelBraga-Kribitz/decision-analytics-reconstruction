---
id: IMP-A02
title: "Categorical encoding for distance-based methods"
absorbs: [A5]
overlaps_triage: []
priority: P1
effort: medium
depends_on: []
soft_depends_on: []
queue: issues
target_repo: decision-analytics-reconstruction
issue: 54
status: filed
---

# IMP-A02 — Categorical Encoding for Distance-Based Methods

`FEATURE_COLUMNS`
(`module_a_population_segmentation/src/population_segmentation/pipeline/models/segmentation.py:215-229`)
feeds two nominal (non-ordinal) integer-encoded columns straight into
`StandardScaler → PCA → DBSCAN/KMeans`, a pipeline whose every step (`_matrix`,
segmentation.py:232-246) operates in Euclidean distance:

- `preference_proxy_encoded`: `{A: 0, B: 1, other: 2, none: 3}`
  (`features/behavioral.py:29-32`) — four unordered preference-proxy
  categories mapped to consecutive integers. Euclidean distance now says
  "none" (3) is 3x farther from "A" (0) than "B" (1) is, and that "other" (2)
  sits exactly halfway between "B" and "none" — none of which reflects any
  real relationship between the categories.
- `gender_encoded`: `{M: 1.0, F: 0.0, unknown: 0.5}`
  (`features/demographic.py:51`) — `unknown` is placed at the arithmetic
  midpoint of `M` and `F`, which is a modeling choice with real consequences
  for cluster boundaries (an `unknown`-heavy stratum will pull toward
  whichever cluster centroid the 0.5 value lands near) but is presented as if
  it were a neutral numeric feature.

Because `StandardScaler` treats all thirteen `FEATURE_COLUMNS` (including
these two) as continuous, and PCA/DBSCAN/KMeans operate purely on Euclidean
distance in the resulting space, this imposes false ordinal/metric structure
on two nominal variables that feed directly into the six-segment clustering
consumed by Module B (`segment_labels.parquet`).

## 1. Define the Scope (The Data Guardrails)

**In-Scope:**
- `pipeline/models/segmentation.py:215-229` (`FEATURE_COLUMNS`) and
  `pipeline/models/segmentation.py:232-246` (`_matrix`).
- The two implicated columns: `preference_proxy_encoded`
  (`features/behavioral.py:29-32`) and `gender_encoded`
  (`features/demographic.py:51`).
- `config/model_params.yaml:104-117` (`segmentation_features` list), which
  must mirror whatever column set replaces the raw integer encodings.
- Re-validation of the downstream cluster structure (silhouette, bootstrap
  ARI, segment shares) after the encoding change, since PCA dimensionality
  and distances shift when one-hot columns replace integer columns.

**Out-of-Scope:**
- The propensity model's own use of `gender_encoded` and
  `preference_proxy_strength` (`propensity.py` `FEATURES`, lines 16-26) —
  logistic regression with a scaled continuous coefficient does not impose
  the same false-metric assumption that Euclidean clustering does, so that
  path is unaffected unless a future audit finds otherwise.
- k-selection, DBSCAN eps/min_samples tuning, and gate-threshold consistency
  — `IMP-A03` (this issue only changes the input feature space; A03 re-runs
  selection on top of it).
- `LABEL_SCORE_WEIGHTS` and the Hungarian label-repair logic
  (segmentation.py:52-172) — unaffected by encoding choice, since they
  operate on interpretable profile means, not the raw distance-based feature
  matrix.

## 2. Data-Driven "Given-When-Then" Scenarios

**Scenario: One-hot preference proxy in the clustering feature matrix (Happy Path)**
- **Given** a feature frame with `preference_proxy` values in
  `{A, B, other, none}` and the fix applied,
- **When** `_matrix(df)` builds the pre-PCA matrix,
- **Then** the matrix contains three or four indicator columns (e.g.
  `preference_proxy_is_A`, `_is_B`, `_is_other`, with `none` as the reference
  level or all four present per a documented rationale) instead of the single
  `preference_proxy_encoded` integer column, and no pairwise Euclidean
  distance between two rows differing only in preference category depends on
  which two categories they are (all cross-category distances at fixed other
  features become equal, up to the chosen encoding scheme).

**Scenario: Gender treated as a genuine three-level category, not a scalar (Edge Case)**
- **Given** the `unknown` gender bucket, which `features/demographic.py:51`
  currently places at exactly 0.5 (the midpoint of `M`/`F`),
- **When** the fix applies one-hot (or leaves gender out of the
  distance-based feature set with documented rationale, e.g. because it
  correlates weakly with the other twelve features),
- **Then** entities with `unknown` gender are never implicitly nearer to
  entities with a "moderate" mix of `M`/`F` traits — the verification script
  confirms `gender_encoded` (the raw scalar) is absent from
  `FEATURE_COLUMNS`/`segmentation_features` unless replaced by indicator
  columns.

## 3. Specify Undesirable Behaviors (Negative Constraints)

**Scenario: Preventing silent reintroduction of ordinal-coded nominal features**
- **Given** any future addition to `FEATURE_COLUMNS` or
  `config/model_params.yaml:segmentation_features`,
- **When** a new column is a `*_encoded` integer column derived from a
  `.map({...})` over more than two unordered string categories,
- **Then** the change must document, in the same PR, why Euclidean distance
  over that encoding is a defensible approximation (or must one-hot it) —
  the finding's rationale should not need to be re-discovered.

## 4. Detail Data-Specific Non-Functional Requirements

- **Model fairness / bias:** `gender_encoded`'s current midpoint placement of
  `unknown` is exactly the kind of proxy-distortion this repo's governance
  exists to catch; the fix must not introduce a *new* distortion, e.g. by
  one-hotting gender in a way that makes `unknown` entities systematically
  attract to a specific cluster via an unintended reference-level asymmetry.
  Re-run `cluster_profiles` (segmentation.py:74-103) post-fix and confirm no
  segment's `unknown`-gender share moves by more than 5 percentage points
  versus the pre-fix run, as a bias-drift sanity check.
- **Performance & decay:** one-hotting adds at most 4 columns (3 for
  preference proxy, 1-2 for gender) to the pre-PCA matrix (13 → ~17-19
  columns); `pca.n_components: 5` (`model_params.yaml:30`) should be
  re-validated (explained variance ratio) rather than assumed to still
  capture "the dominant variance" per the existing comment
  (segmentation.py:235-239).
- **Data integrity:** `evaluation/schema_validator.py` and
  `pipeline/models/segmentation.py`'s `FEATURE_COLUMNS` list must stay in
  sync — if one-hot columns are added upstream in a feature-builder module,
  the segmentation feature list must reference the new column names exactly,
  and a missing-column `KeyError` at `_matrix` is the correct failure mode
  (no silent fillna-to-zero).
- **Reproducibility:** `StandardScaler` + `PCA(random_state=42)` remains
  deterministic under the new column set; the acceptance criteria include a
  before/after diff of `silhouette`, `bootstrap_ari`, and `segment_share` at
  the existing test fixture (n=15,000, seed=42) recorded in the PR
  description, not merely "structure looks similar."

## 5. Queue Stub (ready to file)

**GitHub Issue body:**

```markdown
### Problem

`FEATURE_COLUMNS` in
`module_a_population_segmentation/src/population_segmentation/pipeline/models/segmentation.py:215-229`
feeds two nominal (unordered) integer-encoded columns into a Euclidean
distance pipeline (`StandardScaler → PCA → DBSCAN/KMeans`):

- `preference_proxy_encoded` (`A=0, B=1, other=2, none=3`,
  `features/behavioral.py:29-32`) — four unordered categories on a
  numeric scale.
- `gender_encoded` (`M=1.0, F=0.0, unknown=0.5`,
  `features/demographic.py:51`) — `unknown` sits at the arithmetic midpoint
  of `M`/`F`, imposing an artificial "in-between" relationship.

`_matrix()` (segmentation.py:232-246) standardizes and PCA-reduces all 13
`FEATURE_COLUMNS` together, so both columns' false ordinal structure
propagates into every downstream cluster boundary used for
`segment_labels.parquet` (consumed by Module B).

### Evidence

- `pipeline/models/segmentation.py:215-229` — `FEATURE_COLUMNS` list
  including `preference_proxy_encoded` and `gender_encoded`.
- `pipeline/models/segmentation.py:232-246` — `_matrix()`: StandardScaler +
  PCA over the raw integer columns, comment claims "5 principal components
  capture the dominant variance" without accounting for encoding choice.
- `features/behavioral.py:29-32` — `pref_map = {"A": 0, "B": 1, "other": 2,
  "none": 3}`.
- `features/demographic.py:51` — `gender_map = {"M": 1.0, "F": 0.0,
  "unknown": 0.5}`.
- `config/model_params.yaml:104-117` — `segmentation_features` list mirrors
  the same raw column names.

### Acceptance Criteria

1. `preference_proxy_encoded` is replaced in the clustering feature matrix
   by one-hot indicator columns (or excluded with a written rationale
   committed alongside the code, e.g. in a docstring or `governance/adrs/`).
2. `gender_encoded`'s raw scalar form is not fed into `_matrix()`'s Euclidean
   space; either one-hot indicators replace it, or it is excluded with
   documented rationale.
3. `config/model_params.yaml`'s `segmentation_features` list is updated to
   match the new column set exactly (no drift between YAML and
   `FEATURE_COLUMNS`).
4. Post-change, `silhouette`, `bootstrap_ari`, and per-segment `rural`/`metro`
   /`youth` profile means (`cluster_profiles`, segmentation.py:74-103) are
   recomputed at the existing n=15,000/seed=42 fixture and the before/after
   deltas are reported in the PR description.
5. No `unknown`-gender or `none`-preference entity's segment assignment
   changes purely as an artifact of the *old* midpoint/ordinal encoding (spot
   check: compare segment membership for a sample of `unknown`-gender
   entities before/after).

### Verification

Re-run `pytest module_a_population_segmentation/tests/test_segmentation.py`
and confirm `test_kmeans_bootstrap_ari_above_threshold` and the silhouette
test still pass against `model_params.yaml`'s existing thresholds (0.77,
0.22) with the new feature matrix — a large regression in either metric
means the encoding change needs `IMP-A03`-style k/DBSCAN re-tuning before
merge, not a silent gate-lowering.

Spec: `governance/improvement_plan/IMP-A02_categorical-encoding.md`
```

**Labels:** `type:refactor`, `skill:module-a`, `effort:medium`,
`priority:p1`, `status:claude-ready`
