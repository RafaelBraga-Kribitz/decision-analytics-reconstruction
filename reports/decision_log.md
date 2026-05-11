# Decision Log

Records every non-trivial architectural choice: decision, alternatives considered, reason, date.

---

## 2026-05-07 — Module A: K selection strategy

**Decision:** Use k=6 as default with silhouette validation across k ∈ {4,5,6,7,8}.

**Alternatives considered:**
- DBSCAN-only segmentation: rejected because downstream allocation (Module B) requires a fixed, stable number of segments with interpretable profiles.
- k=8: silhouette diagnostic showed diminishing returns beyond k=6 and domain knowledge maps cleanly to 6 archetypes.

**Reason:** Fixed-k K-Means with domain-validated k=6 provides operationally targetable, named segments. Divergence between silhouette-optimized k and domain k=6 is logged as a quality artifact, not a blocker.

**Source:** scope_module_A §7.2

---

## 2026-05-07 — Module A: DBSCAN vs Isolation Forest for noise pre-pass

**Decision:** Use DBSCAN noise pre-pass rather than Isolation Forest.

**Alternatives considered:**
- Isolation Forest: more robust in high dimensions but produces a score (not a binary flag), requires threshold selection, and does not provide density-based intuition.
- Local Outlier Factor: similar density basis but slower at N=4.26M scale.

**Reason:** DBSCAN's noise label is deterministic given (ε, MinPts); fits the scope requirement for deterministic, seeded pipelines; well-understood behavior in the standardized feature space. MinPts = 2*p rule-of-thumb documented in scope §7.1.

**Source:** scope_module_A §7.1

---

## 2026-05-07 — Module A: Platt calibration vs isotonic regression

**Decision:** Use Platt (sigmoid) calibration rather than isotonic regression.

**Alternatives considered:**
- Isotonic regression: more flexible, but requires more calibration data and can overfit on small calibration sets. Calibration set at sample_size=100k is 20k rows — acceptable for Platt, potentially marginal for isotonic.
- Temperature scaling: simpler (1 parameter) but does not shift mean, only rescales variance.

**Reason:** Platt calibration with a 20% holdout gives stable A,B estimates at all realistic sample sizes. The two-parameter sigmoid is sufficient to correct the systematic offset typical in logistic regression scores. Documented limitation: at sample_size < 500k, calibration may be noisier — flagged in model card.

**Source:** scope_module_A §7.3

---

## 2026-05-07 — Module A: Department rake approach

**Decision:** Post-hoc department-level rake multiplier stored in calibration_anchors.yaml, applied after Platt calibration.

**Alternatives considered:**
- Department one-hot encoding: 18 dummy variables in logistic model; risks overfitting and hides the calibration target.
- Pre-computed `department_logit_offset` feature (scope approach): used as a single feature rather than one-hot; rake multiplier applied post-Platt as a final correction.

**Reason:** Separating the logistic model's discriminative power from the department-level participation rate constraint prevents calibration leak into model selection. The rake multiplier magnitude is logged and visible as a quality artifact.

**Source:** scope_module_A §7.3

---

## 2026-05-07 — Schema contracts: Module A → B → C dependency

**Decision:** Schema contracts for population_master_clean, segment_labels, participation_propensity, and media_reachability_by_segment are defined once in schema_contracts/ and validated at Module A pipeline exit.

**Reason:** These four files are the cross-module contract boundary. Defining them once, with version numbers, prevents silent breakage when Module A modeling parameters change. Breaking changes require schema_version bump + decision_log entry + integration-impact-auditor sign-off.

**Source:** scope_master §6, cross-module impact gate rule

---

## 2026-05-11 — Local Docker: Colima instead of Docker Desktop (Mac Pro maintainer)

**Decision:** Document and verify Module A `docker compose` using **Colima** + Homebrew Docker CLI; Docker Desktop is not the supported local path on Metal-degraded legacy Macs.

**Alternatives considered:** Docker Desktop GUI (rejected: freezes and GPU stack issues); dropping Docker from the repo (rejected without product sign-off).

**Reason:** Colima provides a headless Linux VM and matches project rule [`.cursor/rules/06-developer-machine-macpro-6-1.mdc`](.cursor/rules/06-developer-machine-macpro-6-1.mdc). `poetry install` in the image requires `README.md` in the build context when `readme` is set in `pyproject.toml`, so the Dockerfile copies it into `/app/`.

**Source:** CI infra hardening session

---

## 2026-05-11 — Module A: Batch export pipeline — 4-artifact contract-aligned emitter

**Decision:** Add `population_segmentation.pipeline.export` CLI module that runs the full Module A pipeline and writes all four contract-aligned artifacts: `population_master_clean.parquet`, `segment_labels.parquet`, `participation_propensity.parquet`, `media_reachability_by_segment.csv`.

**Producers / consumers per schema_contracts/README.md:**
- `population_master_clean.parquet` — produced by Module A cleaner + feature stack; consumed by Module B (entity base) and Module C (strata weights).
- `segment_labels.parquet` — produced by Module A `build_segmentation_frame()`; consumed by Module B (channel cap per segment) and Module C (segment-level forecast strata).
- `participation_propensity.parquet` — produced by Module A `PropensityModel`; consumed by Module B (allocation weight) and Module C (calibration target).
- `media_reachability_by_segment.csv` — produced by Module A `aggregate_media_reachability_by_segment()`; consumed by Module B (channel caps per segment per district).

**Alternatives considered:** Per-step scripts (rejected: fragile, no single entry point); DVC pipeline (deferred: adds dependency, no cross-module runner yet).

**Source:** scope_master §6, schema_contracts cross-module impact gate

---

## 2026-05-11 — CI: docker-smoke job on ubuntu-latest

**Decision:** Add `docker-smoke` GitHub Actions job after the `module-a` job. Runs on `ubuntu-latest`, builds the Module A image with `docker compose build module_a`, runs `import population_segmentation` smoke, and verifies `docker compose up --build --no-start module_a`.

**Reason:** Validates that the Docker image is buildable and importable in a clean Linux CI environment, decoupled from the developer's Colima-based local setup. Catches packaging regressions (missing files, pyproject changes) before they reach production or the Render deploy.

**Source:** cross-module impact gate; CI Docker smoke validation

---

## 2026-05-11 — Module A audit refactor (session 2)

### Segmentation: compute _matrix once per build_segmentation_frame call

**Decision:** Refactor `DBSCANNoiseFilter.fit_transform` and `KMeansSegmenter.fit_predict` to accept an optional keyword argument `x: np.ndarray | None = None`. `build_segmentation_frame` now computes `_matrix(df)` once and passes the result to both. The inline DBSCAN in `build_segmentation_frame` was also replaced with `DBSCANNoiseFilter()` so DBSCAN parameters live in a single place.

**Reason:** The original code computed `StandardScaler().fit_transform` + `PCA(5).fit_transform` twice on identical data — once for DBSCAN and once inside `KMeansSegmenter.fit_predict`. With N=15 k rows this is ~1 s of redundant fitting per export call; at N=50 k or production scale (4.26 M) it is material. The DRY/SOLID violation was also a maintenance risk: separate fits produce slightly different PCA projections when sklearn BLAS non-determinism is present.

**Impact:** Purely internal; public API (`build_segmentation_frame`, `DBSCANNoiseFilter`, `KMeansSegmenter`) is backward-compatible. `DBSCANNoiseFilter.fit_transform` now also returns `noise_flags` (per-row bool array) in addition to `noise_rate`.

**Tests added:** `test_matrix_computed_once_in_build_segmentation_frame`, `test_dbscan_noise_filter_returns_noise_flags`, `test_dbscan_noise_filter_accepts_precomputed_matrix`.

### Contract validation: media_reachability_by_segment added to runtime gate

**Decision:** Extend `_validate_export_contracts` (export.py) to also validate the `media_reachability_by_segment` DataFrame: row count == k=6, unique segment labels, canonical segment label values, `primary_reach_channel` in `{tv, radio, whatsapp, direct}`, proportion columns in [0, 1], `segment_size > 0`.

**Reason:** The fourth artifact was written by `run_export` but never validated at the contract gate, meaning a silent bug in `aggregate_media_reachability_by_segment` would produce a non-conformant CSV that downstream Module B would reject. Contract enforcement surface now matches the documented four-artifact schema.

**Tests added:** 12 tests in `test_contract_violations.py` covering all entity-level and media-aggregate violation scenarios.

### Schema contract: segment_id.max corrected to 5

**Decision:** Changed `segment_labels.yaml` `segment_id.max` from `7` to `5`.

**Reason:** The code uses k=6 with a 0-based label map (indices 0–5). The previous value of 7 allowed a 2-unit margin above the actual maximum, which would mask out-of-range bugs. `required_k: 6` was already consistent; the max field was not.

### Dashboard: segment_id and dbscan_noise_flag attached to feat frame

**Decision:** `_build_sample` in `streamlit_dashboard.py` now attaches `segment_id` and `dbscan_noise_flag` to the `feat` DataFrame alongside `segment_label`, mirroring the export pipeline merge.

**Reason:** The dashboard previously dropped two columns that the export pipeline attaches. Any code inspecting `_build_sample` output as a proxy for export-like data would see a different column set, creating a potential divergence point for downstream reasoning.

### Dashboard reliability chart: relabelled as national-rate reference diagnostic

**Decision:** Extracted `_make_national_reference_labels(n, national_rate, seed)` as a named, testable helper. Updated Tab 2 subheader and added a `st.caption` explaining that `y_true` comes from `Bernoulli(national_rate)` — not from the model's training target — so the chart is a reference baseline, not a calibration plot.

**Reason:** The original inline code generated labels from `Bernoulli(national_rate_only)` while presenting the chart under a "Propensity Calibration" heading. The model trains on labels that incorporate department, youth, and gender deviations; the national-only reference labels measure something different. Relabelling prevents a reviewer from incorrectly interpreting the chart as held-out calibration evidence.

### model_params.yaml: honesty annotation added

**Decision:** Updated the header comment in `model_params.yaml` to explicitly list the parameters that are declared in the YAML but not yet wired to runtime loading in `src/` (PCA, DBSCAN, KMeans defaults; CV grid; stratify_by; SHAP).

**Reason:** The previous header said "No values hardcoded in src/" which was incorrect. Code-level defaults exist and match the YAML, but the YAML is not actually read by model classes. The comment now reflects the true state and records the planned resolution (config-loading adapter in export.py).

---

## 2026-05-11 — Graphify resolved (Poetry dev dependency)

**Decision:** Add PyPI package **`graphifyy`** (`>=0.7,<0.8`) to `[tool.poetry.group.dev.dependencies]`. It provides the `graphify` console script (`poetry run graphify update .` or `make graphify`). Earlier attempts used distribution names `graphify` and `graphify-cli`, which are not published on PyPI; the maintained package is **`graphifyy`**.

**Reason:** After `poetry install`, any developer can refresh `graphify-out/` without a one-off global install. AST-only updates require no API keys; optional semantic features follow upstream documentation.

**Evidence:** `poetry run graphify update .` → exit 0; rebuild logged 697 nodes, 751 edges, 59 communities (session 2026-05-11).

**Source:** graphify-resolve closure; `docs/ai_harness/README.md` graph section

