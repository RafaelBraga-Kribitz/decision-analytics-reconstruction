# Module A Code Audit Report — 2026-05-11

**Scope:** `module_a_population_segmentation/` (src, tests, app, config, reports, schema_contracts)
**Auditor:** Cursor module-a-specialist (session 2026-05-11)
**Baseline:** 79 tests / 92% coverage (session 2026-05-07)

---

## Critical Audit Summary — Top 5 Issues

| # | Issue | File(s) | Risk |
|---|-------|---------|------|
| 1 | **Double PCA/scaler fit in segmentation pipeline** — `build_segmentation_frame` computed `_matrix(df)` once, then passed the raw DataFrame to `KMeansSegmenter.fit_predict`, which called `_matrix(df)` again internally. Two independent StandardScaler + PCA(5) fits on the same data. | `segmentation.py` | Performance at scale; subtle PCA non-determinism under parallel BLAS |
| 2 | **`media_reachability_by_segment` excluded from runtime contract gate** — Three entity-level artifacts were validated at export exit; the fourth CSV was written with no runtime check. | `export.py` | Silent bad artifact; downstream Module B would receive non-conformant channel caps |
| 3 | **`segment_id.max: 7` in schema contract for k=6 code** — Contract allowed segment IDs up to 7 while code produces only 0–5. Out-of-range values would not be caught by the gate. | `schema_contracts/segment_labels.yaml` | Contract enforcement gap; bugs producing index 6–7 would go undetected |
| 4 | **Dashboard reliability chart mislabelled** — Tab 2 generated `y_true ~ Bernoulli(national_rate_only)` while presenting a "Propensity Calibration" heading. Model trains on labels with department/youth/gender deviations; the chart was measuring a different quantity. | `streamlit_dashboard.py` | Statistical mis-presentation; reviewer could mistake reference baseline for held-out calibration |
| 5 | **`model_params.yaml` claims "No values hardcoded in src/" — incorrect** — PCA, DBSCAN, KMeans, split fractions, and C=1.0 (no CV grid) are all hardcoded in model classes with no runtime config loading. SHAP declared in YAML is not implemented. | `model_params.yaml`, `segmentation.py`, `propensity.py` | Config/code drift creates false confidence; any YAML edits have no runtime effect |

---

## Detailed Findings

### 1. Engineering & Code Quality

#### DRY/SOLID — Segmentation preprocessing (FIXED in this session)

**Finding:** `_matrix(df)` (StandardScaler + PCA) was called twice per `build_segmentation_frame` call.

- `build_segmentation_frame` line 133: `x = _matrix(df)` → used only for DBSCAN
- `KMeansSegmenter.fit_predict` line 76: `x = _matrix(df)` → independent second fit

**Root cause:** The two classes had separate scaler/PCA lifecycles with no shared precomputed state. `build_segmentation_frame` also bypassed `DBSCANNoiseFilter`, inlining DBSCAN with hardcoded `eps=2.0, min_samples=5` — duplicating parameters already defined in the dataclass.

**Fix applied:**
- `DBSCANNoiseFilter.fit_transform(df, *, x=None)` — accepts precomputed matrix
- `KMeansSegmenter.fit_predict(df, *, x=None)` — accepts precomputed matrix
- `build_segmentation_frame` computes `x = _matrix(df)` once, passes to both
- Inline DBSCAN replaced with `DBSCANNoiseFilter()` to consolidate parameter ownership
- `DBSCANNoiseFilter.fit_transform` now also returns `noise_flags` (per-row bool array)

**Tests added:** `test_matrix_computed_once_in_build_segmentation_frame` (patches `_matrix` and asserts call_count == 1), `test_dbscan_noise_filter_returns_noise_flags`, `test_dbscan_noise_filter_accepts_precomputed_matrix`.

---

#### DRY — Flaw table / cleaner normalization map (open, low risk)

**Finding:** `raw_injector.py` defines `_DEPT_TYPOS` and `_GENDER_VARIANTS`; `cleaner.py` defines `_DEPT_NORMALIZE` and `_GENDER_MAP`. These are two handwritten mirrors of the same domain rules — typos to inject in one direction, normalization to reverse in the other.

**Impact:** Editing one requires a synchronized edit to the other. Easy to miss during future maintenance. No correctness risk today because the flaw/clean cycle is tested end-to-end.

**Recommendation:** Extract a shared `config/domain_variants.yaml` (or a `utils/domain.py` constant module) that both injector and cleaner import. Low priority — refactor when the flaw type list next changes.

---

#### DRY/KISS — Dashboard vs export orchestration duplication

**Finding:** `_build_sample` in `streamlit_dashboard.py` and `run_export` in `export.py` encode the same generate → inject → clean → feature → segment → propensity pipeline. They can drift silently.

**Partial fix applied:** `_build_sample` now attaches `segment_id` and `dbscan_noise_flag` to match the export merge. The underlying duplication remains.

**Recommendation:** Extract a shared `build_pipeline_sample(config, anchors, seed, sample_size, qa_dir)` function in `pipeline/` that both callers use. Medium priority.

---

#### YAGNI — `_load_config` dead function in generator

**Finding:** `generator.py` defines `_load_config` (around line 119–121) but it is never called.

**Recommendation:** Remove. Confirmed dead by AST-level graphify coverage and grep.

---

#### YAGNI — `language_guarani_flag` unused in model features

**Finding:** `build_behavioral_features` computes `language_guarani_flag` but it appears in neither `FEATURE_COLUMNS` (segmentation) nor `FEATURES` (propensity). Only referenced in tests.

**Recommendation:** Document as reserved for future module use, or remove if no plans exist.

---

#### Clean Code — Schema column name literals scattered

**Finding:** `utils/schema.py` documents canonical column names but many files use bare string literals directly (`"cedula"`, `"department"`, etc.) without importing from `schema.py`.

**Recommendation:** Enforce via a Ruff/flake8 check or progressively replace. Low priority vs correctness.

---

### 2. Data Science & Statistical Rigour

#### Feature/label coupling in propensity (documented, not a bug)

**Finding:** `PropensityModel._feature_matrix` adds `department_logit_offset` computed from the same calibration anchors used to generate synthetic labels in `_synthetic_target`. In isolation this looks like leakage, but the model card (`model_card_propensity.md` "Key design note") explicitly documents that this is the intended reconstruction design — the feature encodes the prior, not held-out empirical data.

**Status:** Documented. AUC/Brier metrics are measures of in-distribution fit, not external generalization. Gate labels in `schema_contracts/participation_propensity.yaml` correctly mark informational vs enforced.

---

#### Calibration split stratification gap (open)

**Finding:** `fit_predict` stratifies the first 60/40 split on `department` only. `model_params.yaml` documents `stratify_by: [department, age_bin, gender]`. The cal/test 50/50 split uses no stratification at all.

**Impact:** For rare departments or unbalanced synthetic `y`, the calibration partition may have a different label distribution from the test partition. At n=15 k the effect is small but could surface at unusual seeds.

**Recommendation:** Either implement full stratification as documented, or update `model_params.yaml` to reflect what the code actually does. Medium priority.

---

#### Dashboard reliability diagram: y_true mismatch (FIXED in this session)

**Finding:** The original Tab 2 code created `y_true ~ Bernoulli(national_rate)` using only the national rate, while `PropensityModel` was trained on labels incorporating department/youth/gender deviation. The chart comparison was between raked propensities (department-adjusted) and reference labels (national-only), yet was presented as "Propensity Calibration."

**Fix applied:** Extracted `_make_national_reference_labels(n, national_rate, seed)` as a named, documented function. Updated the chart heading to "Propensity — National-Rate Reference Diagnostic" with an explicit note that this is a reference baseline, not held-out calibration.

---

#### Gender "unknown" treated as non-F in _synthetic_target

**Finding:** `_synthetic_target` uses `np.where(df["gender"] == "F", 0.02, -0.02)` for gender adjustment. Entities with `gender == "unknown"` receive `−0.02` (same as male), which may be semantically incorrect.

**Impact:** Small; `unknown` is rare in the synthetic population and the gender gate is informational-only.

**Recommendation:** Change to a three-way branch or zero for unknown. Low priority.

---

#### `auc_threshold: 0.70` declared but not enforced in tests

**Finding:** `model_params.yaml` states `auc_threshold: 0.70` as a gate. No test asserts `auc_roc > 0.70`. Tests assert Brier, department calibration, and no-masking guards; AUC is returned but not validated.

**Recommendation:** Add a test that asserts `prop_out["metrics"]["auc_roc"] > 0.70`. Low effort.

---

#### `reliability_max_deviation_pp: 3.0` declared but not enforced

**Finding:** `model_params.yaml` declares a max reliability deviation gate but `compute_reliability_deviation` from `evaluation/calibration_metrics.py` is imported in test_evaluation.py only and never called on actual propensity output in any test.

**Recommendation:** Wire to a test: call `PropensityModel.fit_predict` on a sample, build the reliability frame, compute `reliability_deviation`, and assert it is below `3.0 pp`. Medium priority.

---

### 3. Infrastructure & Architecture

#### Export contract: media_reachability_by_segment not validated (FIXED in this session)

**Finding:** `_validate_export_contracts` in `export.py` validated the three entity-level parquet artifacts but did not validate the fourth artifact (`media_reachability_by_segment.csv`).

**Fix applied:**
- Added `_VALID_REACH_CHANNELS` and `_MEDIA_REQUIRED_COLUMNS` module-level constants
- Extended `_validate_export_contracts(reach: pd.DataFrame | None = None)` with checks for: required columns, row count == k=6, unique segment label, canonical label values, valid `primary_reach_channel`, proportion columns in [0, 1], `segment_size > 0`
- Updated `run_export` to pass `reach_df` to the gate
- Added 12 tests in `test_contract_violations.py`

---

#### Schema contract `segment_id.max` bound (FIXED in this session)

**Finding:** `schema_contracts/segment_labels.yaml` declared `segment_id.max: 7` while the code produces 0-based k=6 labels (max = 5). This 2-unit margin would hide any bug producing invalid indices 6 or 7.

**Fix applied:** Changed to `max: 5` with a clarifying description.

---

#### `logging` not used — `print()` throughout

**Finding:** `export.py` uses `print()` statements for pipeline progress. No structured logging (`logging.getLogger`) is used anywhere in `src/`.

**Recommendation:** Replace with `import logging; logger = logging.getLogger(__name__)` pattern. Add `LOG_LEVEL` env var support. Medium priority — not a blocker but makes log scraping and test isolation harder.

---

#### Config: hardcoded paths and seeds scattered

**Finding:** `run_export` hardcodes `seed=42` for generate, inject, clean, segment, and propensity calls. These are not overridable without modifying source. `model_params.yaml` declares `random_state: 42` in each section.

**Recommendation:** Add a `--seed` CLI flag to `export.py` and pass it through. The YAML `random_state` values could then serve as the default. Low priority for reconstruction (determinism is a feature), but needed if ablation experiments are planned.

---

#### Cross-module readiness

**Finding:** Modules B and C are planned but not in-repository. `schema_contracts/README.md` documents the A→B→C lineage; no downstream integration tests exist. When B/C land, `test_input_schema.py`-style tests should validate that outputs produced by `run_export` satisfy whatever the downstream loader expects.

**Status:** Out of scope for this session. Documented here for the next session.

---

### 4. Testing & Evidence

#### `test_dashboard.py` was smoke-only (FIXED in this session)

**Finding:** The original `test_dashboard.py` had one test that only checked top-level return keys. No assertion on required columns, dtypes, or helper semantics.

**Fix applied:** Added 9 new tests covering segment column presence, `segment_id` range, `dbscan_noise_flag` dtype, propensity range, and 5 tests for `_make_national_reference_labels` (shape, dtype, empirical mean, determinism, seed independence).

---

#### `test_contract_violations.py` did not exist (FIXED in this session)

**Fix applied:** 12 new tests covering all violation scenarios for both entity-level artifacts and the media aggregate CSV.

---

## Refactor Roadmap (ordered by impact)

| Priority | Item | Effort | Status |
|----------|------|--------|--------|
| P1 | Segmentation double-fit (DRY/SOLID) | 1 h | **DONE** |
| P1 | Media aggregate contract gate | 1 h | **DONE** |
| P1 | `segment_id.max` schema fix | 5 min | **DONE** |
| P1 | Dashboard reliability chart honest labelling | 30 min | **DONE** |
| P1 | `model_params.yaml` honesty annotation | 15 min | **DONE** |
| P2 | AUC gate wired to test | 30 min | Open |
| P2 | Reliability deviation gate wired to test | 1 h | Open |
| P2 | Propensity split: full `stratify_by` or YAML correction | 2 h | Open |
| P2 | Dashboard/export shared pipeline function | 2 h | Open |
| P3 | Replace `print()` with `logging` | 2 h | Open |
| P3 | Config-loading adapter in `export.py` for `model_params.yaml` | 3 h | Open |
| P3 | Flaw table / cleaner map unified in `domain_variants.yaml` | 2 h | Open |
| P3 | Remove dead `_load_config` function in generator | 10 min | Open |
| P3 | SHAP: implement or remove from model_params/rubrics | — | Open (scope decision) |
| P4 | Cross-module: `test_input_schema.py` for B/C inputs | — | Blocked (B/C absent) |

---

## Refactor Implementation — Highest-Priority Fix

The highest-priority DRY/SOLID fix (double PCA/scaler computation) is fully implemented in `segmentation.py`. The refactored surface is reproduced here for reference:

```python
# DBSCANNoiseFilter — accepts optional precomputed matrix
def fit_transform(
    self, df: pd.DataFrame, *, x: np.ndarray | None = None
) -> dict[str, object]:
    if x is None:
        x = _matrix(df)
    labels = DBSCAN(eps=self.eps, min_samples=self.min_samples, metric="euclidean").fit_predict(x)
    noise_flags: np.ndarray = labels == -1
    return {"noise_rate": float(noise_flags.mean()), "noise_flags": noise_flags}

# KMeansSegmenter — accepts optional precomputed matrix
def fit_predict(
    self, df: pd.DataFrame, *, x: np.ndarray | None = None
) -> dict[str, object]:
    if x is None:
        x = _matrix(df)
    km = KMeans(n_clusters=self.k, init="k-means++", n_init="auto",
                random_state=self.random_state)
    labels = km.fit_predict(x)
    ...

# build_segmentation_frame — single matrix computation, routed through DBSCANNoiseFilter
def build_segmentation_frame(df, k=6, random_state=42):
    x = _matrix(df)                                    # computed ONCE
    noise_result = DBSCANNoiseFilter().fit_transform(df, x=x)   # reuses x
    seg = KMeansSegmenter(k=k, random_state=random_state)
    seg_out = seg.fit_predict(df, x=x)                 # reuses x
    ...
```

Regression test:

```python
def test_matrix_computed_once_in_build_segmentation_frame(feature_df):
    from unittest.mock import patch
    import population_segmentation.models.segmentation as seg_module

    call_count = 0
    original = seg_module._matrix

    def counter(df, **kwargs):
        nonlocal call_count
        call_count += 1
        return original(df, **kwargs)

    with patch.object(seg_module, "_matrix", side_effect=counter):
        seg_module.build_segmentation_frame(feature_df)

    assert call_count == 1  # was 2 before refactor
```

---

## Session Evidence Summary

| Check | Result |
|-------|--------|
| `test_segmentation.py` (12 tests) | PASS |
| `test_contract_violations.py` (12 tests) | PASS |
| `test_dashboard.py` (10 tests) | PASS |
| Full suite + coverage | See `task_verify_TASK-20260511-002.md` |
