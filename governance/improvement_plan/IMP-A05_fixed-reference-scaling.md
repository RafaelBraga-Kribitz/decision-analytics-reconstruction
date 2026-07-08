---
id: IMP-A05
title: "Fixed-reference feature scaling"
absorbs: [A14, A15]
overlaps_triage: []
priority: P2
effort: medium
depends_on: []
soft_depends_on: []
queue: issues
target_repo: decision-analytics-reconstruction
issue: 56
status: filed
---

# IMP-A05 — Fixed-Reference Feature Scaling

Two Module A feature-engineering steps scale or bin against the **current
run's own empirical distribution** instead of a fixed, documented reference,
so the meaning of the resulting feature silently changes with sample size and
input distribution:

1. **Quantile-relative reachability tiers (A14).**
   `build_reachability_features`
   (`features/reachability.py:98-102`) assigns `reachability_tier` by
   comparing `reachability_index` to the current frame's own
   `.quantile(0.33)` / `.quantile(0.66)`. By construction, ~33% of every run
   is "low" and ~33% is "high" regardless of what the underlying index values
   are — a dev run (`sample_size: 100000`, `generation.yaml:5`) and the full
   4,260,816-entity run (`N_full`, `generation.yaml:6`) will draw different
   tier boundaries, and any drift in the input distribution (e.g. the
   internet-access rates that were already revised once,
   `generation.yaml:217-218`) silently moves the cutpoints. Downstream,
   `media_reachability_by_segment.csv` is exported to Module B
   (`module_a_population_segmentation/README.md:37`) as if "low/medium/high"
   were stable, comparable categories.
2. **Sample-relative min-max scaling of an already-bounded prior (A15).**
   `build_behavioral_features` (`features/behavioral.py:36-41`) min-max
   scales `nbi_stress_prior` to the sample's own `min()`/`max()` to produce
   `nbi_stress_prior_scaled` — even though the generator explicitly clips
   raw NBI values to `[0, 1]` (`generator.py:335`:
   `np.clip(nbi_vals + nbi_noise, 0.0, 1.0)`). The natural fixed reference
   range exists and is already enforced upstream; re-normalizing to the
   sample extremes means the same raw NBI value maps to different scaled
   values across runs (the sample max at n=100k will differ from the max at
   n=4.26M), and `nbi_stress_prior_scaled` feeds both segmentation
   (`FEATURE_COLUMNS`, segmentation.py:229) and the cluster-profile
   `nbi_stress` axis used for label assignment (segmentation.py:99).

## 1. Define the Scope (The Data Guardrails)

**In-Scope:**
- `features/reachability.py:98-102` (tier cutpoints) and the
  `reachability_tier` column contract.
- `features/behavioral.py:36-41` (`nbi_stress_prior_scaled`).
- `config/model_params.yaml` (or `generation.yaml`): a new committed block
  declaring the fixed reference ranges/cutpoints and their provenance.
- A drift alert: an observable check comparing the current run's empirical
  distribution against the fixed reference.

**Out-of-Scope:**
- The `reachability_weights` values themselves and the `reachability_index`
  formula (`reachability.py:92-96`) — the index computation is not disputed,
  only the tier binning on top of it.
- `StandardScaler` inside `segmentation._matrix` — per-fit standardization
  of the clustering matrix is a modeling choice reviewed under `IMP-A03`,
  not a cross-run comparability contract (segment labels are re-derived per
  fit anyway).
- Cleaner-side imputation defects — `IMP-A04`.
- Which downstream Module B logic consumes `media_reachability_by_segment.csv`
  — Module B adapts to a stable contract; it does not change here.

## 2. Data-Driven "Given-When-Then" Scenarios

**Scenario: Fixed tier cutpoints survive a change in sample size (Happy Path)**
- **Given** fixed reachability tier cutpoints committed to config (e.g.
  `reachability_tier_bounds: {low_max: <x>, high_min: <y>}` in
  `model_params.yaml`, with a comment recording that they were derived once
  from a named reference run — seed 42, n and date stated),
- **When** `build_reachability_features` runs at `sample_size: 100000` and
  again at `N_full: 4260816`,
- **Then** an entity with the same `reachability_index` value receives the
  same `reachability_tier` in both runs, and the tier *shares* (not the
  boundaries) are what varies between runs — verifiable by asserting the
  cutpoints used are byte-equal to the config values, not recomputed
  quantiles.

**Scenario: NBI scaling anchored to the generator's clip range (Happy Path)**
- **Given** `nbi_stress_prior` values clipped to `[0, 1]` upstream
  (`generator.py:335`),
- **When** `build_behavioral_features` runs,
- **Then** `nbi_stress_prior_scaled` equals `nbi_stress_prior` mapped through
  the **fixed** `[0, 1]` reference (i.e. the identity, or a documented fixed
  affine transform) — never through the sample's own `min()`/`max()` — so a
  raw value of 0.55 scales identically at any `n` and any seed.

**Scenario: Drift alert when the empirical distribution departs the reference (Edge Case)**
- **Given** a future run whose `reachability_index` distribution has shifted
  (e.g. after an internet-access-rate config revision) such that a fixed
  cutpoint yields a tier share outside a documented tolerance band (e.g.
  any tier < 15% or > 55% of entities),
- **When** the pipeline export stage runs,
- **Then** it emits an explicit drift warning naming the tier, its share, and
  the tolerance band into the QA report / export manifest (and optionally
  fails a gate if configured), rather than silently rebinning — the operator
  decides whether to re-derive reference cutpoints, and that re-derivation is
  itself a reviewed config change, not runtime behavior.

## 3. Specify Undesirable Behaviors (Negative Constraints)

**Scenario: Preventing run-relative statistics from defining exported categorical contracts**
- **Given** any exported column whose values are category labels derived from
  numeric thresholds (`reachability_tier` today; any future `*_tier` /
  `*_bucket` column),
- **When** the threshold is computed,
- **Then** it must come from committed config with documented provenance,
  never from `.quantile()`, `.min()`, `.max()`, `.mean()`, or `.std()` of
  the frame being transformed — a runtime-computed cutpoint feeding an
  exported categorical column is a failing state for this change's
  verification.

**Scenario: Preventing double normalization of already-bounded inputs**
- **Given** a column whose generator/upstream contract already bounds it to a
  known range (as `generator.py:335` bounds `nbi_stress_prior` to `[0, 1]`),
- **When** feature engineering rescales it,
- **Then** the rescale must reference the contractual bounds, and the code
  comment must name the upstream guarantee — sample-extreme min-max over a
  contractually bounded column is banned.

## 4. Detail Data-Specific Non-Functional Requirements

- **Model fairness / bias:** rural entities concentrate in the low tail of
  `reachability_index` (digital reach gated on `internet_access_flag`,
  reachability.py:76-78); moving from quantile tiers to fixed cutpoints will
  change the rural share of the "low" tier. The PR must report the
  before/after rural/urban composition per tier at n=15k seed=42 so the
  shift is a reviewed, visible consequence rather than a silent one.
- **Performance & decay:** negligible — replacing two quantile computations
  with config lookups is if anything cheaper. The drift check adds one
  histogram/share computation per run (< 1 s at n=100k).
- **Data integrity:** the drift tolerance band (per-tier share bounds) lives
  in config next to the cutpoints; the export stage's QA report records the
  observed shares each run. Abort conditions: cutpoints missing from config
  (KeyError, fail fast — no silent fallback to quantiles), or a NaN
  `reachability_index` reaching the tier assignment.
- **Reproducibility:** with fixed cutpoints, `reachability_tier` and
  `nbi_stress_prior_scaled` become pure functions of each row's inputs —
  identical values across runs, seeds, and sample sizes for identical raw
  inputs. This is the definition of done: a two-run diff (n=15k vs n=50k,
  same seed, intersecting entities) shows zero tier/scale disagreement on
  shared entities.

## 5. Queue Stub (ready to file)

**GitHub Issue body:**

```markdown
### Problem

Two Module A features are scaled/binned against the current run's own
distribution instead of a fixed reference, so their meaning silently changes
across dev (n=100k) vs full (N=4,260,816) runs and with any input-distribution
drift — while downstream consumers treat them as stable:

1. `reachability_tier` is cut at the current frame's `.quantile(0.33)` /
   `.quantile(0.66)` (`features/reachability.py:98-102`); ~33% of every run
   is "low" by construction, and `media_reachability_by_segment.csv` exports
   these tiers to Module B as if comparable across runs.
2. `nbi_stress_prior_scaled` is min-max scaled to the sample's own
   `min()`/`max()` (`features/behavioral.py:36-41`) even though the
   generator already clips the raw value to [0, 1] (`generator.py:335`) —
   the fixed reference range exists and is ignored.

### Evidence

- `module_a_population_segmentation/src/population_segmentation/features/reachability.py:98-102`
  — `q_low = out["reachability_index"].quantile(0.33)` etc.
- `module_a_population_segmentation/src/population_segmentation/features/behavioral.py:36-41`
  — `min_val = out["nbi_stress_prior"].min(); max_val = ...max()` min-max.
- `module_a_population_segmentation/src/population_segmentation/data/generator.py:335`
  — `np.clip(nbi_vals + nbi_noise, 0.0, 1.0)` upstream bound.
- `module_a_population_segmentation/config/generation.yaml:5-6` —
  `sample_size: 100000` vs `N_full: 4260816` (the two scales between which
  quantile cutpoints diverge).
- `module_a_population_segmentation/README.md:37` —
  `media_reachability_by_segment.csv` consumed by Module B.

### Acceptance Criteria

1. Reachability tier cutpoints are fixed values in
   `config/model_params.yaml` (with provenance comment: reference run seed,
   n, date), and `build_reachability_features` reads them — no
   `.quantile()` call remains in the tier assignment.
2. `nbi_stress_prior_scaled` uses the contractual [0, 1] range (or a
   documented fixed affine transform), not sample min/max; the code comment
   names the `generator.py` clip guarantee.
3. A drift check compares each run's per-tier shares against a configured
   tolerance band and writes a warning to the QA report / export manifest
   when breached; re-deriving cutpoints requires a config change, never
   happens at runtime.
4. PR reports before/after tier shares and rural/urban composition per tier
   at n=15,000, seed=42.
5. Cross-run comparability demonstrated: same entity, same raw inputs, two
   different sample sizes → identical `reachability_tier` and
   `nbi_stress_prior_scaled`.

### Verification

Run the feature builders at two sample sizes with the same seed; assert zero
tier/scale disagreement on shared entities. Existing segmentation tests
(`tests/test_segmentation.py`) must still pass — `nbi_stress_prior_scaled`
feeds `FEATURE_COLUMNS`, so report the silhouette/ARI deltas.

Spec: `governance/improvement_plan/IMP-A05_fixed-reference-scaling.md`
```

**Labels:** `type:data`, `skill:module-a`, `effort:medium`, `priority:p2`,
`status:claude-ready`
