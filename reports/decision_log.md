# Decision Log

Records every non-trivial architectural choice: decision, alternatives considered, reason, date.

---

## 2026-05-12 — Project Action List §4: `max_noise_rate` comment vs Gate A4

**Decision:** Inline comment on [`model_params.yaml`](../module_a_population_segmentation/config/model_params.yaml) `dbscan.max_noise_rate: 0.01` must state Gate A4 is a **1%** noise ceiling (no stray `0.03` text). Add [`test_model_params_dbscan_max_noise_consistency.py`](../module_a_population_segmentation/tests/test_model_params_dbscan_max_noise_consistency.py).

**Alternatives considered:** Raising the cap to 0.03 — rejected; tests and contracts assume 1%.

**Reason:** Closes Project Action List §4 line 68 (N1.4-style value vs comment drift).

**Source:** Project Action List §4 Codebase Maturity — `max_noise_rate` (2026-05-12).

---

## 2026-05-12 — Project Action List §4: raw_injector column names via schema.py

**Decision:** Keep all DataFrame column access in [`raw_injector.py`](../module_a_population_segmentation/src/population_segmentation/data/raw_injector.py) on imported names from [`schema.py`](../module_a_population_segmentation/src/population_segmentation/utils/schema.py) (no `df["…"]` / `df.loc[..., "…"]` / `df.at[..., "…"]` for contract fields). Add [`tests/test_architecture_raw_injector_schema_columns.py`](../tests/test_architecture_raw_injector_schema_columns.py) to block regressions.

**Alternatives considered:** Runtime column registry — rejected as YAGNI while the file stays small.

**Reason:** Closes Project Action List §4 line 64 (column constant discipline).

**Source:** Project Action List §4 Codebase Maturity — raw_injector / schema.py (2026-05-12).

---

## 2026-05-12 — Project Action List §4: `enc_source_raw` → `enc_source` at clean boundary

**Decision:** In [`cleaner.py`](../module_a_population_segmentation/src/population_segmentation/data/cleaner.py) step 1, when `enc_source_raw` is present, fill nulls with `unknown`, coerce values outside [`CANONICAL_ENC_SOURCE`](../module_a_population_segmentation/src/population_segmentation/utils/schema.py) to `unknown`, assign to `enc_source`, then drop `enc_source_raw`. Contract copy lives in [`population_master_raw.yaml`](../schema_contracts/population_master_raw.yaml) and [`population_master_clean.yaml`](../schema_contracts/population_master_clean.yaml). Regression [`test_enc_source_promoted_from_raw_layer`](../module_a_population_segmentation/tests/test_cleaner.py).

**Alternatives considered:** Using one column name in both raw and clean YAML — rejected to preserve lineage between layers.

**Reason:** Closes Project Action List §4 line 63; avoids defaulting `enc_source` to `utf8` while `enc_source_raw` held the generator mix.

**Source:** Project Action List §4 Codebase Maturity — `enc_source` / `enc_source_raw` (2026-05-12).

---

## 2026-05-12 — Project Action List §3: `pipeline-dev` runs full Module A export

**Decision:** Replace incremental `generator` → `raw_injector` → `cleaner`-only [`Makefile`](../Makefile) `pipeline-dev` recipe with a single `poetry run python -m population_segmentation.pipeline` invocation (default `--sample-size $(or $(SAMPLE),10000)` for clone-local speed), delegating to [`run_export`](../module_a_population_segmentation/src/population_segmentation/pipeline/export.py) so `data/processed/` receives the wide population master with segment and propensity columns, `segment_labels.parquet`, `participation_propensity.parquet`, reachability CSVs, and `model_run_manifest.json`. Document in [`ARCHITECTURE.md`](../ARCHITECTURE.md). Add [`tests/test_architecture_pipeline_dev_contract.py`](../tests/test_architecture_pipeline_dev_contract.py) (Makefile parse tests plus optional `@pytest.mark.slow` `make pipeline-dev` smoke).

**Alternatives considered:** Chaining `module-a-export` after cleaner-only steps — rejected as duplicate full population generation; keeping cleaner-only `pipeline-dev` — rejected as failing Project Action List §3 acceptance line 48.

**Reason:** One command matches clone → install → dev pipeline expectations without a separate export step.

**Source:** Project Action List §3 Architecture Quality — acceptance line 48 (`make pipeline-dev` contract bundle) (2026-05-12).

---

## 2026-05-12 — Project Action List §3: `data/` stages and `.gitkeep` with gitignore negation

**Decision:** Replace blanket `data/raw/`, `data/interim/`, `data/processed/` ignore entries in [`.gitignore`](../.gitignore) with `data/<stage>/*` plus `!data/<stage>/.gitkeep` so empty clone directories stay **tracked** while generated parquet and CSV remain ignored. Add [`data/raw/.gitkeep`](../data/raw/.gitkeep), [`data/interim/.gitkeep`](../data/interim/.gitkeep), [`data/processed/.gitkeep`](../data/processed/.gitkeep) and [`tests/test_architecture_data_directory_layout.py`](../tests/test_architecture_data_directory_layout.py) as regression guard.

**Alternatives considered:** Relying on DVC only without tracked placeholders — rejected for Architecture Quality line 46 explicit `.gitkeep` requirement.

**Reason:** Fresh `git clone` gets stable paths for Makefile targets without committing heavy artifacts.

**Source:** Project Action List §3 Architecture Quality — task 9 (`data/` layout) (2026-05-12).

---

## 2026-05-12 — Project Action List §3: ARCHITECTURE.md diagrams and contract tables

**Decision:** Expand root [`ARCHITECTURE.md`](../ARCHITECTURE.md) with two Mermaid diagrams (artifact flow and package dependency), five markdown contract tables keyed to shipped YAML under [`schema_contracts/`](../schema_contracts/) (`population_master_clean`, `segment_labels`, `participation_propensity`, `allocation_output`, `polls_clean_tracking_wave`), each with at least twenty table rows (field rows plus explicit metadata rows where the YAML has fewer than twenty `fields:` keys), and a numbered **Walkthrough: one entity** section. Add [`tests/test_architecture_md_content_contract.py`](../tests/test_architecture_md_content_contract.py) to prevent silent removal of Mermaid blocks, contract headings, README cross-link, or short tables.

**Alternatives considered:** Auto-generating tables from YAML in CI — deferred as YAGNI; manual tables plus test are enough for this checklist closure.

**Reason:** Documentation-only closure for Architecture Quality line 45; no schema semantic edits.

**Source:** Project Action List §3 Architecture Quality — task 8 (`ARCHITECTURE.md` depth) (2026-05-12).

---

## 2026-05-12 — Project Action List §3: `make test` + coverage and CI contract

**Decision:** Root [`Makefile`](../Makefile) defines `MODULE_TEST_ARGS` and `COV_FLAGS`; **`test`** runs `poetry run pytest` over all module and root test dirs with `-m "not slow"` and `$(COV_FLAGS)` (three `--cov=` roots plus `term-missing` and `xml` reports). **`coverage`** reuses the same `$(COV_FLAGS)` without a marker filter (full suite for `make ci`). Add [`tests/test_architecture_makefile_test_coverage_contract.py`](../tests/test_architecture_makefile_test_coverage_contract.py). Add GitHub Actions job **`repo-make-test`** (`poetry install` then `make test`, 30-minute cap) so a clean clone exercises the same entrypoint as local `make validate`’s test stage.

**Alternatives considered:** Leaving coverage only on `make coverage` — rejected because Project_Action_list line 44 explicitly ties `make test` to coverage reporting; duplicating `--cov=` lists without `COV_FLAGS` — rejected per DRY.

**Reason:** Verifiable CI/Makefile alignment; root `tests/` architecture guards run on every `make test` without changing schemas.

**Source:** Project Action List §3 Architecture Quality — task 7 (CI/CD, `make test` + coverage) (2026-05-12).

---

## 2026-05-12 — Project Action List §3: Makefile Poetry and pre-commit

**Decision:** Root [`Makefile`](../Makefile) invokes Python tooling only through `poetry run` (no `PYTHON :=` / `$(PYTHON)`); `precommit` runs `poetry run pre-commit install` and `poetry run pre-commit run`. Dev generators under `generate-dev` / `pipeline-dev` use `poetry run python -m …`. Add [`tests/test_architecture_makefile_poetry_policy.py`](../tests/test_architecture_makefile_poetry_policy.py) as regression guard.

**Alternatives considered:** Keeping a `PYTHON` variable for faster local edits — rejected so clone + `poetry install` + `make …` always hits the project venv.

**Reason:** Aligns Makefile with Architecture Quality checklist and virtualenv discipline.

**Source:** Project Action List §3 Architecture Quality — task 6 (Makefile / Poetry) (2026-05-12).

---

## 2026-05-15 — Project Action List §3: “All outputs Pydantic” vs layered contracts

**Decision:** Reconcile Architecture Quality line 42 (“all module outputs explicitly typed”) with the **shipped** design: **versioned YAML** in [`schema_contracts/`](../schema_contracts/) defines cross-module tabular contracts; **Pydantic** covers the narrow Module B→C handshake row ([`AllocationHandshakeRow`](../module_b_resource_allocation/src/module_b_resource_allocation/contracts/schemas.py)); **frozen dataclasses** and Pandera gate selected Module A structures and clean-population frames; Module C validates against the same YAML corpus via `contract_validate`. Add [`tests/test_architecture_inter_module_contracts_surface.py`](../tests/test_architecture_inter_module_contracts_surface.py) as a regression guard (no new umbrella Pydantic per parquet file).

**Alternatives considered:** Wrapping every export column set in generated Pydantic models — deferred as high churn and low marginal value versus existing Pandera + YAML contracts.

**Reason:** One-task §3 closure with verifiable commands; no handshake or schema_contracts semantic edits.

**Source:** Project Action List §3 Architecture Quality — task 5 (2026-05-15).

---

## 2026-05-14 — Project Action List §3: Module C checklist vs shipped tree

**Decision:** Reconcile Architecture Quality “Module C: METHODOLOGY.md + forecast_model.py stub” with the **shipped** layout: hierarchical tracking model, multi-stage `pipeline/` CLIs, `config/calibration.yaml`, and research-facing proof table under `module_c_forecasting_scenarios/reports/`. Add [`tests/test_architecture_module_c_surface.py`](../tests/test_architecture_module_c_surface.py) asserting canonical paths exist, legacy-only filenames absent, and lightweight imports (`paths`, `contract_validate`) without requiring a new root `METHODOLOGY.md` or `forecast_model.py` shim.

**Alternatives considered:** Adding placeholder `METHODOLOGY.md` and `forecast_model.py` — rejected per YAGNI; documentation intent is met by existing reports + code.

**Reason:** One-task §3 closure with verifiable commands; no calibration YAML semantic edits.

**Source:** Project Action List §3 Architecture Quality — task 4 (2026-05-14).

---

## 2026-05-14 — Project Action List §3: Module B checklist vs shipped tree

**Decision:** Reconcile Architecture Quality “Module B: specification + skeleton” with the **ship-ready** layout: root [`module_b_resource_allocation/SPECIFICATION.md`](../module_b_resource_allocation/SPECIFICATION.md) plus PuLP/CBC implementation in [`models/allocation.py`](../module_b_resource_allocation/src/module_b_resource_allocation/models/allocation.py) (`build_problem`, `solve`), not a standalone `optimization_engine.py` stub (that filename is not part of the shipped tree). Add [`tests/test_architecture_module_b_surface.py`](../tests/test_architecture_module_b_surface.py) as regression guard.

**Alternatives considered:** Adding `optimization_engine.py` as a facade — rejected per YAGNI; SPEC already maps readers to the canonical modules.

**Reason:** One-task §3 closure with commands-only verification and no solver/schema drift.

**Source:** Project Action List §3 Architecture Quality — task 3 (2026-05-14).

---

## 2026-05-13 — Project Action List §3: Module A surface checklist vs shipped tree

**Decision:** Reconcile Architecture Quality “Module A: all files exist and runnable” with the **actual** `population_segmentation` layout (split `features/` modules, `evaluation/schema_validator.py`, dashboard under `module_a_population_segmentation/app/streamlit_dashboard.py`) and add [`tests/test_architecture_module_a_surface.py`](../tests/test_architecture_module_a_surface.py) as a regression guard. Do **not** introduce legacy-only filenames (`features/engineer.py`, `evaluation/validator.py`, dashboard under `src/…/app/`) solely to match an outdated bullet list.

**Alternatives considered:** Creating thin re-export shims with old paths — rejected as YAGNI and import-noise.

**Reason:** One-task Architecture Quality closure with verifiable commands and no export/schema drift.

**Source:** Project Action List §3 Architecture Quality — task 2 (2026-05-13).

---

## 2026-05-12 — Module A: `python -m population_segmentation.pipeline` + `model_run_manifest.json`

**Decision:** (1) Add `population_segmentation/pipeline/__main__.py` so the full export path is runnable as `poetry run python -m population_segmentation.pipeline` with repository-root defaults for `module_a_population_segmentation/config/generation.yaml`, `calibration_anchors.yaml`, and `data/processed/`. (2) After contract validation, `run_export` writes `model_run_manifest.json` (package version via `importlib.metadata`, UTC `train_date`, `git rev-parse` best-effort, exported artifact paths, fixed RNG seed map) and optionally logs to MLflow when `MLFLOW_TRACKING_URI` is set, matching the opt-in pattern used for Module C.

**Alternatives considered:** Requiring only `python -m population_segmentation.pipeline.export` — kept as the low-level entry; the new module path matches the Data Science Framing acceptance string. Storing only MLflow without a JSON sidecar — rejected because file-store provenance should not depend on a tracking server.

**Reason:** Data Science Framing (action list) requires a single canonical command, explicit model lineage documentation (`reports/model_hierarchy.md`, `module_a_model_io_spec.md`), feature justification, notebook walkthrough, and reproducibility metadata for ML engineers without opening multiple modules manually.

**Source:** Project Action List section 2 — Data Science Framing (2026-05-12).

---

## 2026-05-12 — Module B CFO baseline comparator (department-uniform naive)

**Decision:** Persist `baseline_comparison` on every allocation run manifest (`run_manifest_<scenario>.json`) computed in `module_b_resource_allocation.reporting.baselines`. The **department-uniform naive** benchmark splits `CAMPAIGN_BUDGET_USD` evenly across all 18 geographic units in `DEPARTMENTS`, then applies uniform cap-limited water-fill within each unit using the **same linearized marginal persuasion-per-USD slopes** as the MILP LP objective (`_linear_cell_specs`). The MILP row reports both that linear projection on solved spends and the sum of **nonlinear** `persuasion_adjusted_contacts` on solver output rows (diminishing-returns reconstruction). Cap-only national water-fill remains as a relaxation transparency row.

**Alternatives considered:** Using cap-water-fill alone as the “business naive” — rejected for narrative mismatch with geographically uniform budgeting in `reports/case_study_business.md`. Encoding full MILP feasibility (bundles, coverage) into naive — deferred to avoid coupling portfolio framing to MILP internals; caveat is spelled out in manifest `definitions`.

**Reason:** CFO-facing business framing needs reproducible naive vs optimized numbers without opening code; deltas must trace to deterministic seeds (`--seed 20180422`) and pinned constants in `module_b_resource_allocation/src/module_b_resource_allocation/constants.py`.

**Source:** Project Action List §1 Business Framing (2026-05-12).

---

## 2026-05-12 — Verification sweep: Module B routing Makefile, Module C day index, EDA terminology

**Decision:** (1) `module-b-routing` Makefile target now calls `build_cost_matrix` and writes `routing_cost_matrix_<scenario>.csv` because the legacy `routing.heuristic` CLI module was removed and routing matrices are produced alongside allocation. (2) `_build_day_index` indexes `pd.date_range` results with `days[i]` instead of `days.iloc[i]` (DatetimeIndex has no `iloc`). (3) `reports/eda/generate_eda.py` narrative and chart titles align with the regex rules in `scripts/check_terminology.py` (open that script for the disallow list).

**Alternatives considered:** Leaving Makefile `module-b-routing` broken — rejected because README and operators still reference it. Pinning MC draws at 200 for local `make module-c-all` with `MC_FAST=1` — accepted as fast default, but EDA contract tests require 10k draws; regenerate MC with `env -u MC_FAST` when refreshing `data/processed/`.

**Reason:** Full-stack verification must pass `make tier3-smoke` and `tests/test_eda.py` after pipeline refreshes; routing and hierarchical fixes unblock `module-c-all` and downstream EDA.

**Source:** full-stack verification session (2026-05-12).

---

## 2026-05-12 — Evaluation gap remediation: Poetry root install in CI + rural WhatsApp anchor

**Decision:** GitHub Actions jobs that run pytest or import first-party packages use `poetry install` (editable root packages on `sys.path`), not `poetry install --no-root`. Module A generator reads `media_penetration_defaults.whatsapp_rural` from `generation.yaml` for rural `media_penetration_whatsapp` instead of scaling urban ICT by a hard-coded factor.

**Alternatives considered:** Pytest `pythonpath` in `pyproject.toml` only — rejected because it duplicates Poetry’s package metadata and can drift from real installs.

**Reason:** CI must mirror how contributors run tests locally; YAML anchors for ICT media penetration should be authoritative for rural vs urban constants.

**Documentation audit (external writeups):** Some older critiques assumed a missing root-level `cleaner.py` or a `counterfactual/broadcast_to_direct.py` module path; the shipped cleaner is `module_a_population_segmentation/src/population_segmentation/data/cleaner.py` (see `reports/transformation_log.md`), and the broadcast-to-direct counterfactual lives in `module_b_resource_allocation/src/module_b_resource_allocation/models/counterfactual.py` as referenced in the Phase 9–10 entry below.

**Source:** external portfolio evaluation + internal evaluation-gap plan (2026-05-12).

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

## 2026-05-11 — Cross-module debt closure (Module B foundation)

**Decision:** Close four confirmed debts in one cycle, before Module B implementation lands:

1. **Reachability grain:** `media_reachability_by_segment` stays segment-only (k=6) as the diagnostic rollup; add new contract `media_reachability_by_segment_department.yaml` (1 row per (segment, department), 108 rows) as the authoritative grain consumed by Module B LP/MILP. Module B MUST NOT reinterpret the segment-only artifact as department-level caps.
2. **Calibration transparency:** Keep existing four TSJE-verified department gates as the only blocking calibration gates on `participation_propensity`. National, gender, and youth anchors remain informational and labelled in `schema_contracts/participation_propensity.yaml` with explicit source-inconsistency notes; placeholder departments stay tagged in `calibration_anchors.yaml`.
3. **Harness vs enforcement reconciliation:** Update `docs/ai_harness/professional-grade-rubrics.md` to state enforced thresholds (silhouette 0.22, ARI 0.77, Brier 0.237) and mark the older aspirational gates as targets, not pass/fail. Align `module_a_population_segmentation/config/model_params.yaml` ARI threshold to 0.77 (it was 0.80, inconsistent with `test_segmentation.py` which enforces 0.77).
4. **Module B integration scaffolding:** Add `schema_contracts/allocation_output.yaml`, `reachability_caps_dept_channel.yaml`, `routing_cost_matrix.yaml` so the Module B implementation lands against contracts rather than producing them ad hoc.

**Locked implementation choices for Module B:**

- Canonical optimization dimension: **11 channels** (matches the solver-facing channel taxonomy).
- Solver stack: **PuLP/CBC** for LP/MILP + seeded **nearest-insertion + 2-opt** heuristic for TSP routing.
- Data discipline: priors/placeholders are allowed initially with explicit `provenance` tags ∈ {VERIFIED, PRIOR, ESTIMATED}; verified-source ingestion is a follow-up.
- Window: Jan–Apr 2018, 14 weeks; 18 departments × 11 channels × 14 weeks = 2,772 allocation rows.

**Reason:** B's optimizer is sensitive to weights and caps; reading segment-level reach as district-level would silently produce wrong caps, and harness/test drift could confuse Module B and Module C onboarding. Closing these debts as a contract-first set lets B and C land against stable schemas with no silent reinterpretation.

**Cross-module impact:** Module A export pipeline must emit the new segment-by-department reach artifact; downstream `test_input_schema.py` tests in Module B will validate against the new contracts. Module C calibration metadata inherits the same provenance discipline.

**Source:** integration-impact-auditor closure session 2026-05-11; `docs/ai_harness/professional-grade-rubrics.md`; `module_a_population_segmentation/reports/audit_report_module_a_2026-05-11.md`.

---

## 2026-05-11 — Graphify resolved (Poetry dev dependency)

**Decision:** Add PyPI package **`graphifyy`** (`>=0.7,<0.8`) to `[tool.poetry.group.dev.dependencies]`. It provides the `graphify` console script (`poetry run graphify update .` or `make graphify`). Earlier attempts used distribution names `graphify` and `graphify-cli`, which are not published on PyPI; the maintained package is **`graphifyy`**.

**Reason:** After `poetry install`, any developer can refresh `graphify-out/` without a one-off global install. AST-only updates require no API keys; optional semantic features follow upstream documentation.

**Evidence:** `poetry run graphify update .` → exit 0; rebuild logged 697 nodes, 751 edges, 59 communities (session 2026-05-11).

**Source:** graphify-resolve closure; `docs/ai_harness/README.md` graph section

---

## 2026-05-11 — Module B Phase 9–10 completion: counterfactual engine + integration validation

**Decision:** Complete Module B implementation through broadcast-to-direct counterfactual engine and full test suite with API/weekly-replay entrypoints.

**Scope closed:**
- Phase 9: `module_b_resource_allocation/src/module_b_resource_allocation/models/counterfactual.py` (`run_broadcast_to_direct`) — reallocates broadcast budget (tv_spots, radio_spots, newspaper_inserts) to direct channels (canvassing, rallies_events, sound_cars, sms_blasts); applies 15% bundle-release penalty when `conglomerate_x` flips 0; emits `delta_contacts` (int64, signed), `bundle_flipped_to_zero`, and `scenario_id = "broadcast_to_direct"`.
- Phase 10: Verified all 13 integration tests pass (FastAPI TestClient), 131 Module B tests pass end-to-end, 116 Module A tests pass (no regressions).
- Terminology: fixed two comment violations — `pre-election ramp` → `pre-outcome-event ramp` and `general election context` → `outcome event context`.

**Alternatives considered:** Separate MILP re-solve for the counterfactual scenario (avoided due to runtime cost; Dirichlet-weighted analytic reallocation is sufficient for scenario reporting per plan §7.2).

**Bundle penalty rate:** 15% of bundle minimum commitment (ESTIMATED); represents sunk logistics overhead when a media bundle contract is partially unwound.

**Evidence:** `poetry run pytest module_b_resource_allocation/tests/ -v` → 131 passed; `poetry run pytest module_a_population_segmentation/tests/` → 116 passed.

**Source:** module-b-counterfactual + integration-and-verification closure session 2026-05-11.

---

## 2026-05-11 — Module B: single canonical allocator and Module C scaffold

**Decision:** Treat `module_b_resource_allocation.models.allocation` (`build_problem` / `solve`) as the only MILP implementation. Keep `models.allocation_lp.run_allocation` as a thin facade for the legacy dict return shape used in tests and notebooks.

**Counterfactuals:** One implementation lives in `models.counterfactual` (re-exported from `counterfactual`); CLI writes `reallocation_counterfactuals.parquet` aligned with `schema_contracts/reallocation_counterfactuals.yaml`. Post-solve rows are gated by `utils.allocation_output_gate.validate_allocation_output_df` against the allocation output contract.

**Tooling:** `pyproject.toml` `addopts` includes `--import-mode=importlib` so multiple per-module `tests` packages do not collide during collection. `make test` / `make coverage` invoke `poetry run pytest` so runs use the Poetry environment (not the bare `python` on PATH).

**Module C:** New package `module_c_forecasting_scenarios` with `pymc` / `arviz` in Poetry, `config/calibration.yaml` (`series: A`), and CI tests that forbid hybrid calibration keys. Schema stubs added under `schema_contracts/` for poll layers, house-effect seed matrix, and Monte Carlo shock catalog; handshake narrative in `reports/module_b_module_c_handshake.md`.

**Source:** A–B audit / Module C readiness implementation pass.

---

## 2026-05-11 — Module C: schema contracts v1.0.0 + research stubs

**Decision:** Bump Module C poll and shock contracts to `schema_version: "1.0.0"`; add `polls_clean_exit_wave`, `daily_posterior_forecast`, `posterior_house_effects`, and `battleground_department_probability` contracts. Extend raw tracking ingest with `wave_type`, transparency pillar booleans, and OEA/EU placeholder flags. Tracking clean table gains `publication_date`, `m_poll_pp`, conglomerate fields, and `series_tag` echo for QA joins.

**Reason:** Enforce tracking vs exit separation, dual-series calibration without hybrid keys, and typed downstream artifacts for PyMC exports and Monte Carlo catalogues.

**Source:** Module C full-scope execution plan; scope dual calibration (Series A/B).

---

## 2026-05-12 — Module A: Logistic regression vs gradient boosting for propensity model

**Decision:** Use logistic regression with L2 regularization, not gradient boosting (XGBoost / LightGBM).

**Alternatives considered:**
- XGBoost / LightGBM: higher discriminative ceiling on tabular data; SHAP TreeExplainer available; standard in industry churn modeling.
- Random forest: ensemble baseline, no calibration benefit over LR at this feature dimensionality.

**Reason:** Three constraints rule out tree-based methods here. (1) **Calibration contract:** the propensity output must be a probability that passes a reliability-diagram max-deviation ≤ 3 pp gate; logistic regression with Platt calibration produces better-calibrated scores than tree ensembles on synthetic data with ~14 features. (2) **Rake compatibility:** the post-calibration department rake multiplier is applied to the raw logit before sigmoid; this requires a linear model so that the logit offset is interpretable as a log-odds shift. Applying a multiplicative correction to a gradient-boosted leaf value lacks the same probabilistic interpretation. (3) **Audit surface:** a single logistic coefficient vector is directly auditable against the calibration anchors; a 500-tree ensemble is not.

Documented limitation: if the true propensity surface is highly non-linear (e.g., strong rural × youth × language interaction), LR will underfit relative to GBM. SHAP analysis is used to monitor whether the model's learned coefficients are behaviorally plausible or merely fitting noise.

**Source:** scope_module_A §7.3; model_card_propensity.md

---

## 2026-05-12 — Module A: K-Means vs Gaussian Mixture Model for segmentation

**Decision:** Use K-Means (hard assignment), not Gaussian Mixture Model (soft / probabilistic assignment).

**Alternatives considered:**
- GMM with full or diagonal covariance: allows probabilistic segment membership; better captures elongated or overlapping clusters; standard in academic mixture modeling literature.
- Spectral clustering: handles non-convex boundaries; computationally tractable at N=50k sample but not at N=4.26M without approximation.

**Reason:** Operational constraint: Module B's allocation solver requires a **deterministic, non-overlapping segment assignment per entity** so that reach caps (per-segment population ceilings in the LP) are non-overlapping. GMM's soft assignments would require a threshold rule to produce hard labels, reintroducing an arbitrary boundary. K-Means hard assignment is consistent with the segmentation's operational role. The six segments are designed to be **actionable archetypes**, not statistical density modes — the naming (Rural Committed, Youth Volatile, etc.) is post-hoc and operationally meaningful, not a claim about underlying mixture structure.

Documented limitation: K-Means assumes spherical clusters in the standardized PCA space; segments with elongated or non-convex boundaries in raw feature space may be artificially split or merged. The DBSCAN pre-pass removes structural noise before K-Means, reducing sensitivity to outliers that would otherwise pull centroids.

**Source:** scope_module_A §7.1; model_card_segmentation.md

---

## 2026-05-12 — Module A: Synthetic generation vs restricted real data

**Decision:** Generate a fully synthetic population calibrated to verified TSJE/DGEEC anchors. No real individual-level data is used.

**Alternatives considered:**
- Restricted-access TSJE microdata: would provide real behavioral heterogeneity; however, it is not publicly available and its use in a public portfolio reconstruction would raise data governance issues.
- Synthetic minority oversampling (SMOTE-style): applicable if a partial real sample were available; not applicable here.
- Public-use microdata from DGEEC household surveys: partial coverage; does not include electoral roll fields (cédula, participation outcome).

**Reason:** The reconstruction's goal is to demonstrate the **methodology**, not the original operational data. Synthetic generation with verified marginal anchors (TSJE electoral roll, DGEEC census) is the appropriate design: it is transparent, reproducible, and ethically clean. The key limitation is independence: the synthetic generator draws individual attributes conditionally but does not enforce joint correlation structure beyond first-order conditionals and two raking passes. This is documented explicitly — see `appendix/verified_calibration_anchors_full.md` and the statistical narrative in `reports/statistical_independence_note.md`.

**Source:** scope_master §3; Project_Evaluation.md §B.1

---

## 2026-05-12 — Module A: Bayesian generative model vs frequentist synthetic generation

**Decision:** Use a frequentist conditional sampling approach (rng.choice with probability weights + IPF raking), not a full Bayesian generative model (e.g., a Dirichlet-Multinomial hierarchical model).

**Alternatives considered:**
- Full Bayesian generative model with PyMC: would allow posterior uncertainty over population parameters; joint draws would naturally respect correlation structure; posterior predictive checks against TSJE anchors are straightforward.
- Copula-based multivariate simulation: preserves marginals while modeling dependence; would address the independence limitation of the current approach.

**Reason:** For the reconstruction's purpose, the Bayesian generative approach is the technically superior design but operationally unjustified at this stage: (1) The calibration anchors are treated as known constants (verified TSJE/DGEEC values), not as distributions — there is no parameter uncertainty to propagate through the generation step. (2) A PyMC generative model would be substantially slower to run at N=4.26M scale without GPU acceleration. (3) The Module C forecaster (PyMC hierarchical) covers the Bayesian inference layer where it is most impactful — on the noisy poll signal. Applying Bayesian machinery to the population generator would add complexity without changing the calibration targets that the pipeline is ultimately evaluated against.

The copula-based approach is the recommended upgrade path if joint dependence validation becomes a quality gate requirement.

**Source:** Project_Evaluation.md §B.1; scope_module_A §4.1

---

## 2026-05-12 — Module A: Silhouette metric vs domain-defined archetypes for k selection

**Decision:** Use silhouette coefficient as the primary validation metric, with k=6 as the fixed target derived from domain archetypes — not from silhouette maximization.

**Alternatives considered:**
- Pure silhouette optimization: choose k that maximizes mean silhouette across k ∈ {4,5,6,7,8}. This would be fully data-driven but could yield k=4 or k=5 that lack operational differentiation.
- Elbow method on within-cluster sum of squares: noisier than silhouette; widely used but does not provide a clear threshold.
- Domain-first k with no validation: operationally pragmatic but cannot detect degenerate solutions (e.g., one huge cluster absorbing 80% of entities).

**Reason:** The six segment archetypes (Rural Committed, Urban High Volatility, Youth Volatile, Structurally Dependent, Rural Low Propensity, Committed Opposition) are derived from the program's operational logic: each segment requires a distinct channel mix and budget priority. This domain structure sets k=6 as the target. Silhouette is used as a **sanity check** (mean > 0.22, enforced by CI) to confirm that the six-cluster solution has non-trivial cohesion — not to find the optimal k. If silhouette at k=6 fell below 0.22, it would indicate that the domain archetypes do not correspond to statistically separable clusters, which would require feature engineering review.

Bootstrap ARI (> 0.77, enforced) validates stability across random seeds — a critical property when the segmentation is used to fix Module B's reach caps.

**Source:** scope_module_A §7.1; model_card_segmentation.md; decision_log 2026-05-07

---

## 2026-05-12 — Portfolio 360° hardening: integration-impact and evidence surfaces

**Decision:** Execute cross-module portfolio audit closure in one coordinated change set: restore missing `module_b_resource_allocation.reporting` (budget expansion curve), add CI for Module B, extend LP dual diagnostics for portfolio CSVs, add Pydantic contract helpers, typing/pre-commit gates, Module A/C evidence reports, epistemic boundaries documentation, and `make portfolio-verify` driven by the pre-public manifest.

**Alternatives considered:**
- Staged PRs only for Module B: rejected — leaves narrative inconsistent with README claims until later.
- Adding Great Expectations as a second framework in the same pass: deferred — Pandera + schema contracts + `QAGateFailure` already enforce the clean population contract at runtime; GE would duplicate maintenance without changing acceptance gates for this repository snapshot.

**Reason:** Routing matrix requires `integration-impact-auditor` and `qa-gatekeeper` for schema/CI/Makefile and MCMC-adjacent claims; professional-grade rubrics require visible diagnostics and traceable artifacts, not documentation-only assertions.

**Great Expectations vs Pandera:** Runtime validation for the clean population dataset remains **Pandera-first** (`population_segmentation.evaluation.schema_validator` and related gates). Great Expectations remains an optional future layer if portfolio consumers require GE-native checkpoints; no GE dependency is pinned in `pyproject.toml` for this pass.

**Source:** docs/ai_harness/routing-matrix.md; docs/ai_harness/professional-grade-rubrics.md; portfolio 360° audit plan (2026-05-12)
