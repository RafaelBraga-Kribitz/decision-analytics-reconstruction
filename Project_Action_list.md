## ~~1. Business Framing (8.0 → 10.0)~~

~~**Current state:** Narrative is strong but untested against real operational questions.~~

~~**Actions to reach 10/10:**~~

~~- [ ] Add `reports/business_case.md` with: problem statement (not electoral, but resource allocation under uncertainty), cost structure (budget, time, channels), baseline scenario (naive allocation), expected improvements quantified (budget efficiency %, reach improvement %)~~
~~- [ ] Add executive summary section to README that can be read in 60 seconds by a non-technical VP and make business sense without domain knowledge~~
~~- [ ] Create `reports/stakeholder_scenario_table.md`: 3 decision-maker personas (field director, marketing head, CFO) × what they care about (reach, cost, confidence intervals); show how the system answers each question~~
~~- [ ] Implement actual allocation delta: show "naive allocation would spend X, optimized allocation spends Y, projected efficiency gain Z%" with dollar estimates~~
~~- [ ] Add risk/uncertainty section: what breaks if turnout drops 10%? If budget is cut 20%? If FX shifts? Document answers with numbers.~~
~~- [ ] Acceptance: A CFO reading the business case section can explain to a colleague why this system matters without opening code~~

---

## ~~2. Data Science Framing (5.5 → 10.0)~~

~~**Current state:** Conceptual framing is clear; actual modeling is ~30% done.~~

~~**Actions to reach 10/10:**~~

~~- [ ] Implement complete Module A pipeline end-to-end: generator → raw_injector → cleaner → features → segmentation model → propensity model → outputs all runnable via `poetry run python -m population_segmentation.pipeline --config config.yaml`~~
~~- [ ] Add `reports/model_hierarchy.md`: explicit map of which models feed which (e.g., propensity depends on clean population, which depends on cleaning rules, which depend on schema contracts)~~
~~- [ ] For each model, document: input schema (exact columns, dtypes, constraints) → transformations → model class → output schema (exact columns, dtypes). Use schema.py constants everywhere.~~
~~- [ ] Create `notebooks/01_end_to_end_walkthrough.ipynb` showing: raw data → one row traced through entire pipeline → final segment assignment + propensity score. Fully reproducible, deterministic RNG.~~
~~- [ ] Implement model versioning: each model artifact tags (model_type, version, train_date, git_commit). MLflow integration (even if just local file store).~~
~~- [ ] Add feature engineering justification doc: each feature → why it matters → how it's constructed → validation check~~
~~- [ ] Acceptance: A ML engineer can run `poetry run python -m population_segmentation.pipeline` once and get reproducible feature matrix, segmentation assignments, and propensity scores. No missing files, no manual steps, no silent failures.~~

---

## 3. Architecture Quality (5.0 → 10.0)

**Current state:** Well-documented but incomplete; key files and modules missing.

**Actions to reach 10/10:**

~~- [ ] Canonical three-module repository roots with implementation (not stubs): `module_a_population_segmentation/`, `module_b_resource_allocation/`, `module_c_forecasting_scenarios/` — declared in root `pyproject.toml` `[tool.poetry]` `packages` and regression-checked in [`tests/test_architecture_three_module_layout.py`](tests/test_architecture_three_module_layout.py).~~
~~- [ ] Module A (`module_a_population_segmentation/`): production surface exists and runnable — data `generator.py` / `raw_injector.py` / `cleaner.py` / `validator.py`; feature stack `demographic.py`, `behavioral.py`, `reachability.py`; models `segmentation.py`, `propensity.py`; evaluation `schema_validator.py`; pipeline `export.py`, `__main__.py`; app `module_a_population_segmentation/app/streamlit_dashboard.py`; regression in [`tests/test_architecture_module_a_surface.py`](tests/test_architecture_module_a_surface.py); pipeline CLI/help covered by `module_a_population_segmentation/tests/test_pipeline_cli.py`.~~
~~- [ ] Module B (`module_b_resource_allocation/`): [`SPECIFICATION.md`](module_b_resource_allocation/SPECIFICATION.md) documents the MILP; canonical code `src/module_b_resource_allocation/models/allocation.py` (`build_problem`, `solve`), legacy dict API `models/allocation_lp.py`, pipeline CLI `pipeline/run_allocation.py`; regression [`tests/test_architecture_module_b_surface.py`](tests/test_architecture_module_b_surface.py); allocator coverage in `module_b_resource_allocation/tests/test_allocation.py`.~~
~~- [ ] Module C (`module_c_forecasting_scenarios/`): Bayesian tracking in `src/module_c_forecasting_scenarios/models/tracking/hierarchical.py`; pipelines `pipeline/run_all.py`, `run_tracking.py`, `run_monte_carlo.py`, `run_exit.py`; YAML contracts under `config/` (e.g. `calibration.yaml`); methodology and proof narrative under [`module_c_forecasting_scenarios/reports/C_research_proof_table.md`](module_c_forecasting_scenarios/reports/C_research_proof_table.md) (no root `METHODOLOGY.md` / no `src/forecast_model.py` in shipped tree); regression [`tests/test_architecture_module_c_surface.py`](tests/test_architecture_module_c_surface.py); heavy inference covered by `module_c_forecasting_scenarios/tests/`.~~
~~- [ ] Inter-module contracts are **layered and versioned**: declarative YAML under [`schema_contracts/`](schema_contracts/) for tabular artifacts; Pydantic [`AllocationHandshakeRow`](module_b_resource_allocation/src/module_b_resource_allocation/contracts/schemas.py) for Module B→C handshake rows; frozen dataclasses (e.g. [`AnchorCheck`](module_a_population_segmentation/src/population_segmentation/data/validator.py)) plus Pandera / DataFrame validators for wide Module A outputs; Module C uses YAML-driven [`contract_validate`](module_c_forecasting_scenarios/src/module_c_forecasting_scenarios/data/contract_validate.py). Regression [`tests/test_architecture_inter_module_contracts_surface.py`](tests/test_architecture_inter_module_contracts_surface.py).~~
~~- [ ] Makefile: every target uses `poetry run`, respects virtualenv, no direct `python` calls — regression [`tests/test_architecture_makefile_poetry_policy.py`](tests/test_architecture_makefile_poetry_policy.py).~~
~~- [ ] CI/CD: `make test` actually runs pytest and reports coverage; passes on fresh clone — regression [`tests/test_architecture_makefile_test_coverage_contract.py`](tests/test_architecture_makefile_test_coverage_contract.py); GitHub Actions job `repo-make-test` runs `poetry install` then `make test`.~~
~~- [ ] Create `ARCHITECTURE.md` with: data flow Mermaid diagram, module dependency graph, schema contract table (5 contracts × 20 fields each), step-by-step walkthrough of one record — delivered in [`ARCHITECTURE.md`](ARCHITECTURE.md); regression [`tests/test_architecture_md_content_contract.py`](tests/test_architecture_md_content_contract.py).~~
~~- [ ] Create `data/` directory structure: `data/{raw,interim,processed}/.gitkeep` files present — tracked placeholders and `.gitignore` negations; regression [`tests/test_architecture_data_directory_layout.py`](tests/test_architecture_data_directory_layout.py).~~
~~- [ ] Docker: `docker-compose.yml` version correct, `docker/Dockerfile` exists and builds without error, `docker/mlflow.Dockerfile` exists~~
~~- [ ] Acceptance: `git clone` → `poetry install` → `make pipeline-dev` produces clean population dataset, segmentations, propensity scores, and dashboard artifacts in `data/processed/` without manual intervention — [`Makefile`](Makefile) `pipeline-dev` runs `population_segmentation.pipeline` → `run_export`; regression [`tests/test_architecture_pipeline_dev_contract.py`](tests/test_architecture_pipeline_dev_contract.py) (slow test runs `make pipeline-dev`).~~

---

## 4. Codebase Maturity Signals (4.5 → 10.0)

**Current state:** Good intent, broken execution; bugs in live code.

**Actions to reach 10/10:**

**Fix all P0/P1 bugs:**
~~- [ ] `_ENCODING_GARBLES` NameError: define dict, remove unused list, add type hints~~
~~- [ ] `department_weights` sum: correct to 1.0000 exactly, add assertion in generator~~
~~- [ ] `docker-compose.yml` version: "3.9"~~
~~- [ ] No `__main__` entry points: add argparse blocks to generator.py and raw_injector.py~~
~~- [ ] `enc_source` vs `enc_source_raw`: standardize field names, update schema, add comment explaining raw vs clean layer naming~~
~~- [ ] Column name constants: import from schema.py everywhere in raw_injector.py, not bare strings~~ — enforced by [`tests/test_architecture_raw_injector_schema_columns.py`](tests/test_architecture_raw_injector_schema_columns.py); implementation uses [`population_segmentation.utils.schema`](module_a_population_segmentation/src/population_segmentation/utils/schema.py) in [`raw_injector.py`](module_a_population_segmentation/src/population_segmentation/data/raw_injector.py). *(already uses `schema` constants; verified 2026-05-12)*
~~- [ ] `KMeans n_jobs` parameter: remove from model_params.yaml, document `OMP_NUM_THREADS` alternative~~ *(done 2026-05-12: `kmeans.n_jobs` removed + `test_model_params_kmeans_no_n_jobs.py`.)*
~~- [ ] CI `--no-root`: change to `poetry install`, add module importability test~~ *(CI already `poetry install`; regression `tests/test_ci_poetry_install_contract.py`, 2026-05-12)*
~~- [ ] `rural_inet` unused + magic `0.42`: replace with config variable, move internet penetration to generation.yaml~~ *(internet_access rural/urban Bernoulli rates in `media_penetration_defaults` in `generation.yaml`; `generator.py` and `cleaner.py` read `internet_access_rural_rate` / `internet_access_urban_rate`; tests `TestInternetAccessRatesFromConfig`, `test_cleaner_synthetic_internet_flag_uses_config_rates`, 2026-05-12)*
~~- [ ] `max_noise_rate` contradiction: fix comment to match value (0.01) — [`model_params.yaml`](module_a_population_segmentation/config/model_params.yaml) Gate A4 comment; regression [`module_a_population_segmentation/tests/test_model_params_dbscan_max_noise_consistency.py`](module_a_population_segmentation/tests/test_model_params_dbscan_max_noise_consistency.py).~~

**Code quality:**
~~- [ ] Run Ruff on all source files: zero warnings~~ — [`pyproject.toml`](pyproject.toml) `[tool.ruff] exclude` / `extend-exclude` for `reports/`, `**/*.ipynb`, `graphify-out/`, Module A `notebooks/`; `poetry run ruff check .` clean; regression [`tests/test_architecture_ruff_configuration.py`](tests/test_architecture_ruff_configuration.py), [`tests/test_architecture_ruff_black_contract.py`](tests/test_architecture_ruff_black_contract.py) (2026-05-12).
~~- [ ] Run Black: all source files formatted~~ — `reports/eda/*.py` Black-formatted; `poetry run black --check .` clean; regression [`tests/test_architecture_ruff_black_contract.py`](tests/test_architecture_ruff_black_contract.py) (2026-05-12).
~~- [ ] Run Pyright `basic` mode: zero errors (stretch goal: migrate to `strict` mode incrementally)~~ — [`pyproject.toml`](pyproject.toml) `[tool.pyright]` `typeCheckingMode = basic`; Makefile `typecheck` runs `pyright` on Module A and B `src/`; regression [`tests/test_architecture_pyright_basic_contract.py`](tests/test_architecture_pyright_basic_contract.py) (2026-05-12).
~~- [ ] All public functions have docstrings (Google or NumPy format) with: description, Args, Returns, Raises, Example~~ — Module A `population_segmentation` + Module B `module_b_resource_allocation` `src/` trees; regression [`tests/test_architecture_public_google_docstrings_contract.py`](tests/test_architecture_public_google_docstrings_contract.py) (complements narrower [`tests/test_docstrings_module_a_architecture_surface.py`](tests/test_docstrings_module_a_architecture_surface.py)); `poetry run pytest tests/test_architecture_public_google_docstrings_contract.py -q` (2026-05-12).
~~- [ ] All functions with random behavior: seed parameter documented, deterministic with fixed seed~~ — Module A: [`tests/test_stochastic_determinism_module_a_surface.py`](tests/test_stochastic_determinism_module_a_surface.py). Module B: routing + dirty generator + legacy allocator seed docs tightened; regression [`tests/test_stochastic_determinism_module_b_surface.py`](tests/test_stochastic_determinism_module_b_surface.py); `poetry run pytest tests/test_stochastic_determinism_module_{a,b}_surface.py -q` (2026-05-12). Module C / remaining helpers: extend when you widen scope.
~~- [ ] No magic numbers: all constants in `schema.py` or `config/*.yaml`~~ — Module A `clean_population` + `generator.py` draw rates from [`generation.yaml`](module_a_population_segmentation/config/generation.yaml): `language_priors`, `cleaner_synthetic_defaults`, `generator_structural_dependency`, `generator_ballot_blank_rates`, `generator_enc_source_raw_distribution`, **`generator_dept_media_nbi`** (dept TV/radio/NBI + urban-from-rural formula); national TV/radio unknown-dept fallbacks from `media_penetration_defaults`. Contracts: `test_architecture_cleaner_no_magic_priors_contract`, `test_architecture_generator_rural_anchor_contract`, `test_architecture_generator_synthetic_rates_contract`, `test_architecture_generator_dept_media_yaml_contract`. Behavioural tests in `test_generator.py` / `test_cleaner.py`. Module-level defaults in `generator.py` only back missing optional keys. *Optional follow-up: marginal language tuning and `rng.beta(2,2)` in `generator.py` → YAML if you want zero literals in src.*
~~- [ ] No unused imports, no suppressed warnings without justification comment~~ — Ruff `F` + `RUF100` in [`pyproject.toml`](pyproject.toml); [`tests/test_architecture_noqa_justification_contract.py`](tests/test_architecture_noqa_justification_contract.py) (codes + justification tail on every `noqa`); obsolete `noqa` removed from Module C scaffold test; `QAGateFailure` carries documented `N818` waiver. *Optional follow-up: add short comments on Pyright `type: ignore` tails in tests and Module B/C sources.*
~~- [ ] Pre-commit hooks configured: Ruff, Black, Pyright, pytest smoke test~~ — [`.pre-commit-config.yaml`](.pre-commit-config.yaml): Black **26.3.1**, Ruff **v0.15.12** (matches `poetry.lock`), check-only Ruff + `test_eda.py` exclude (parity with `make lint`); Pyright on Module A+B `src/`; `pytest-smoke` runs architecture contract tests + [`tests/test_portfolio_e2e_smoke.py`](tests/test_portfolio_e2e_smoke.py); `nbstripout` scoped to module trees only (not `reports/`). Regression [`tests/test_architecture_pre_commit_contract.py`](tests/test_architecture_pre_commit_contract.py); `poetry run pre-commit run --all-files` (2026-05-12).
~~- [ ] Tests: unit tests for all `_*` helpers, integration tests for major functions, parametrized tests for edge cases~~ — *(done 2026-05-13: Module A — `test_generator_helpers_unit.py`, `test_cleaner_helpers_unit.py`, `test_cleaner_io_helpers_unit.py`, `test_generator_io_helpers_unit.py`, `test_reachability_helpers_unit.py`, `test_demographic_helpers_unit.py`, `test_raw_injector_helpers_unit.py`, `test_segmentation_helpers_unit.py`, `test_pipeline_main_helpers_unit.py`, `test_export_helpers_unit.py`; Module B — `test_private_helpers_unit.py`, `test_feature_join_helpers_unit.py`, `test_run_allocation_helpers_unit.py`, `test_baselines_linear_specs_unit.py`; Module C — `test_private_helpers_unit.py`. Major flows: `test_generator.py`, allocation/integration tests under `module_b_resource_allocation/tests/`. Evidence: `poetry run pytest -q` — **731 passed**, **2 skipped**, 2026-05-13.)*
~~- [ ] Test coverage: minimum 80% on src/, with gaps documented in `tests/README.md`~~ — [`tests/README.md`](tests/README.md): baseline **83%** combined Module A+B+C `src/` (`pytest -m "not slow"` + `--cov` trees, 2026-05-13); gaps table for CLI/MLflow/viz/low-coverage modules.
~~- [ ] Performance: `_rake_categorical` optimized to O(n) single-pass (not per-label `np.where`), benchmark <1s at N=500k~~ — [`generator.py`](module_a_population_segmentation/src/population_segmentation/data/generator.py) `_rake_categorical`: single scan to bucket row indices per label, donor pools updated in place; no per-iteration `np.where` over *n*. Regression: [`test_rake_categorical_benchmark_500k_under_one_second`](module_a_population_segmentation/tests/test_generator_helpers_unit.py) (`@pytest.mark.slow`) asserts wall time **&lt;1s** for *n*=500k; maintainer run **~0.63s** total pytest session for that test (2026-05-13). `make test` stays `pytest -m "not slow"`.
~~- [ ] Type hints: all public functions fully typed, no `Any` without justification comment~~ — AST contract [`tests/test_architecture_public_type_hints_contract.py`](tests/test_architecture_public_type_hints_contract.py): every public function/method in Module A/B/C `src/` has param + return annotations; `Any` in the **signature** requires an inline `#` comment in the same `def` block (or replace `Any` with `object` / precise unions). Heterogeneous YAML: narrow public signatures to `dict[str, object]` plus `typing.cast` at boundaries (e.g. [`validator.py`](module_a_population_segmentation/src/population_segmentation/data/validator.py), [`propensity.py`](module_a_population_segmentation/src/population_segmentation/pipeline/models/propensity.py), [`export.py`](module_a_population_segmentation/src/population_segmentation/pipeline/export.py)). `write_scenario_benchmark_csv` exposes explicit keyword parameters. [`pyproject.toml`](pyproject.toml) per-file Ruff ignores B023/SIM for the walker. **`make typecheck`** remains Module A+B `src/` only (`pyproject` `[tool.pyright] include`). Evidence: `pytest tests/test_architecture_public_type_hints_contract.py -q`, `make lint`, `make typecheck` (2026-05-13).
- [ ] Acceptance: `ruff check . && black --check . && pyright . && pytest --cov=src` all pass; linting output is zero warnings; code review checklist clear

---

## 5. Statistical Rigor Signaling (5.0 → 10.0)

**Current state:** Methodological framing is solid; actual statistical outputs missing.

**Actions to reach 10/10:**

**Propensity model (module A):**
- [ ] Fit logistic regression end-to-end with reproducible results
- [ ] Generate calibration curve (reliability diagram): actual vs predicted, with confidence bands
- [ ] Report Brier score, ROC-AUC, log loss, with comparison to naive baseline (0.6125)
- [ ] Platt calibration: report pre/post calibration Brier scores
- [ ] Department-level rake: report weights per department, validate sum to 1.0 ± 0.01
- [ ] SHAP values: top 10 features by mean absolute SHAP, save summary plot
- [ ] Document: "propensity model is logistic regression trained on synthetic outcome derived from calibration anchors; Platt-calibrated; validated on held-out 20%; Brier score [X]; ROC-AUC [Y]; per-department calibration [Z]"

**Segmentation model (module A):**
- [ ] K-Means with k=6, deterministic initialization
- [ ] Silhouette score: report mean ± std, require ≥0.35
- [ ] Davies-Bouldin index: report value
- [ ] Calinski-Harabasz index: report value
- [ ] Bootstrap stability: 100 resamples, adjusted Rand index ≥0.80, report distribution
- [ ] Segment profiles: cluster centers as feature values, interpretation narrative per segment
- [ ] Document: "segmentation is K-Means k=6, bootstrap ARI ≥0.80, silhouette ≥0.35, deterministic with seed [X]"

**Forecasting model (module C):**
- [ ] Bayesian posterior trace plots: show burn-in, convergence (R-hat <1.01)
- [ ] Effective sample size (ESS) per parameter: report min ESS
- [ ] Posterior predictive checks: compare observed outcomes to posterior predictive distribution, visually show calibration
- [ ] Forecast interval coverage: report 80% and 95% interval coverage rates (should be ≈80% and ≈95%)
- [ ] Walk-forward validation: hold back final week, forecast, report Brier score, log loss, interval coverage
- [ ] Document: "Bayesian model spec: [LaTeX], MCMC: 2000 iterations, 1000 burn-in, R-hat [X], min ESS [Y], posterior predictive calibration [Z], walk-forward Brier [W]"

**General:**
- [ ] Create `reports/epistemic_boundaries.md` with table: Component | Status (Verified / Calibrated / Simulated / Illustrative) | Evidence | Assumptions | Inference claim
- [ ] For every metric reported: include uncertainty (confidence interval, posterior credible interval, bootstrap std)
- [ ] Add `reports/baseline_comparison.md`: compare all models to naive baseline; report improvement delta
- [ ] Acceptance: A statistician can read model specifications, inspect generated plots, and verify that all statistical claims are defended with evidence

---

## 6. Reproducibility (2.5 → 10.0)

**Current state:** Intent is present; execution is broken.

**Actions to reach 10/10:**

- [ ] DVC fully initialized: `dvc init`, remote configured (even if local path), `.dvc/config` present, `dvc.yaml` pipeline defined
- [ ] `dvc.yaml`: defines generate → raw_inject → clean → features stages, with deps, outs, metrics for each
- [ ] All random behavior seeded: RNG seed recorded in config or `seeds.py`, used consistently, documented
- [ ] Makefile: all targets use `poetry run`, no direct python calls, `make setup` initializes venv + dirs + DVC + pre-commit
- [ ] Fresh clone checklist: `git clone` → `make setup` → `make pipeline-dev` → outputs present in `data/processed/` and `reports/` with identical hash to reference run
- [ ] Data immutability: `data/raw/` marked read-only in CI, `data/interim/` and `data/processed/` regenerated from code every run
- [ ] CI reproducibility: GitHub Actions workflow runs full pipeline on every commit, pins all dependency versions (Poetry lockfile), reports artifact hashes
- [ ] Docker reproducibility: `docker build . && docker run` produces identical outputs as local run (same random seeds, same environment)
- [ ] Notebooks: all Jupyter notebooks marked with `jupytext-compatible` format, `--no-output` on commit via pre-commit, can be executed from clean state and produce identical figures
- [ ] Artifact hashing: save outputs of each stage with MD5 hash in metadata, document expected hashes for reference run
- [ ] Acceptance: A colleague on a different machine runs `git clone` → `poetry install` → `make pipeline-dev` and gets byte-for-byte identical outputs as your run 6 months ago

---

## 7. Documentation Quality (6.5 → 10.0)

**Current state:** Narrative is strong; technical completeness has gaps; one false claim.

**Actions to reach 10/10:**

- [ ] Fix `transformation_log.md`: replace false "cleaner.py is implemented" claim with "Specification: 14-step pipeline defined; implementation status: [link to ROADMAP]"
- [ ] Create `ARCHITECTURE.md`: 8 sections (overview, module dependency graph Mermaid, Module A pipeline Mermaid, data lineage table, schema contract registry, engineering standards, how to run, known limitations). Every diagram renders correctly.
- [ ] Create `IMPLEMENTATION_PLAN.md`: phases 1-10 with status (COMPLETE / IN PROGRESS / PLANNED), expected duration, dependencies, quality gates per phase
- [ ] Create `ROADMAP.md`: honest status table (Module A: 85% complete, Module B: 20%, Module C: 5%), blockers, next priorities, timeline
- [ ] Create `reports/epistemic_boundaries.md`: table of verified vs calibrated vs simulated vs illustrative components with source/evidence for each claim
- [ ] README: remove dead URL (Render deployment link), remove or update all "production-ready" claims without evidence, add "Current status" section pointing to ROADMAP
- [ ] Model cards: `reports/model_card_segmentation.md` and `reports/model_card_propensity.md` (Google Card format) with: intended use, training data, model architecture, performance metrics, limitations, ethical considerations, deployment instructions
- [ ] Data dictionary: every column in raw, interim, processed layers documented (type, nullable, example values, derivation if engineered)
- [ ] Schema contracts: README with explanation of each of 5 contract files, field specification keys table, validation behavior per status
- [ ] Decision log: 8 entries with: decision, alternatives considered, trade-offs, evidence, outcome (or null if not yet tried)
- [ ] Code comments: complex logic explained (e.g., "why IPF and not Bayesian?" in cleaner), magic thresholds justified (e.g., "silhouette ≥0.35 chosen because...")
- [ ] Jupyter notebooks: clear objective at top, section headers, markdown explanations between cells, no hidden state, restart/run-all produces identical output
- [ ] Acceptance: A new hire clones the repo, reads ARCHITECTURE.md + ROADMAP.md, can navigate the codebase and understand what's implemented, what's planned, and why each decision was made

---

## 8. Hiring Signal (6.0 → 10.0)

**Current state:** Strong conceptual positioning; broken execution undermines signal.

**Actions to reach 10/10:**

- [ ] **Make it actually runnable:** Fresh clone → `poetry install` → `make test` passes, `make pipeline-dev` runs, no manual steps. This is non-negotiable.
- [ ] **Add quantitative results:** Segmentation silhouette score, propensity ROC-AUC, allocation efficiency delta vs baseline, forecast calibration curve — all visible in README or `reports/` directory
- [ ] **Target specific job descriptions:** Find 3 actual open roles at DACH companies (Knapp AG, TGW Logistics, Roche, Siemens, etc.) that match this skillset. Add `HIRING_CONTEXT.md` section in README that maps project to each role's requirements
- [ ] **Add skills demonstration:** Explicitly call out which technical skills are demonstrated: "Python + pandas + scikit-learn for modeling," "SQL + schema contracts for data validation," "Bayesian reasoning with synthetic calibration," "optimization framing," "statistical inference"
- [ ] **Reduce ambiguity about what's implemented:** Make ROADMAP clear so a reviewer knows "Module A is production-ready, Module B/C are structural demonstrations"
- [ ] **Add a "skills checklist" section:** List 10-15 technical and professional competencies you claim to have demonstrated by this project; check each one off with a link to evidence (file, test, notebook, metric)
- [ ] **Performance at scale:** Show that pipeline runs at N=4.26M without crashing (or document the scale at which it breaks), with timing benchmarks
- [ ] **Error handling:** Pipeline gracefully handles: missing config, invalid data, schema drift, out-of-memory scenarios. Document recovery steps.
- [ ] **Production readiness features:** Implement at least one of: logging (structured, not print), monitoring hooks (metrics exposure), alerts on data quality gates, explicit error messages
- [ ] **Peer feedback:** Have a senior DS/DE review the code and add their feedback as testimonial (or link to code review conversation)
- [ ] Acceptance: A hiring manager at a target company can (1) clone and run it without errors, (2) understand the business problem immediately, (3) identify which technical skills are demonstrated, (4) see measurable results, (5) assess how this maps to their job requirements

---

## 9. Credibility Consistency (3.5 → 10.0)

**Current state:** Multiple false/inconsistent claims erode trust.

**Actions to reach 10/10:**

- [ ] Fix all false claims in documentation:
  - [ ] `transformation_log.md` claim that cleaner.py is implemented → replace with honest status
  - [ ] IMPLEMENTATION_PLAN.md missing → create it
  - [ ] Module B/C directories missing → create them (with READMEs)
  - [ ] Render dashboard URL dead → remove or update with actual deployment URL
  - [ ] README references ARCHITECTURE.md → create it
- [ ] Fix all broken automation:
  - [ ] CI should not silently fail to run tests
  - [ ] `make test` must actually run pytest
  - [ ] `make pipeline-dev` must not call non-existent files
  - [ ] Makefile must not bypass virtualenv
- [ ] Version all major components:
  - [ ] Config versions in `*.yaml` files
  - [ ] Model artifact versions (model_type, version, train_date, git_commit)
  - [ ] Schema contract versions (if changes, increment and document migration)
- [ ] Explicit limitation statements:
  - [ ] "This is a synthetic reconstruction, not inference on real outcomes" (in epistemic_boundaries.md and README)
  - [ ] "Module B/C are specification + skeleton, not production implementations"
  - [ ] "Forecasting is illustrative Bayesian reasoning, not calibrated on real historical forecast error"
- [ ] Audit matrix: claim × evidence × false/true
  - [ ] Go through README and every major claim
  - [ ] Map each claim to a file, test, or metric that proves it
  - [ ] If no evidence exists, remove the claim or move it to "design" or "roadmap"
- [ ] Git hygiene:
  - [ ] Remove `.obsidian`, `.claude`, `.cursor`, `graphify-out` from repo (or gitignore properly and verify)
  - [ ] No paths with `/Users/rbk/` or machine-specific strings
  - [ ] No secrets or credentials in any commit
- [ ] Code walkthrough: Pick one end-to-end scenario (e.g., "one person from raw to segment assignment"), trace through code, verify it executes without errors, document the walkthrough in `notebooks/01_end_to_end_walkthrough.ipynb`
- [ ] Acceptance: A skeptical senior reviewer clones the repo, reads README + ROADMAP, runs the code, inspects one claim in detail, and finds evidence supporting it (or explicit caveat in ROADMAP). No surprises, no inconsistencies, no dead URLs.

---

## 10. Portfolio Differentiation (8.5 → 10.0)

**Current state:** Conceptually highly differentiated; execution incompleteness slightly undermines uniqueness.

**Actions to reach 10/10:**

- [ ] **Explicitly position the core differentiator:** Add a 2-paragraph section early in README: "Why this is different from typical DS portfolios" — focus on decision analytics framing, not electoral domain
- [ ] **Claim the decision science angle clearly:** Position as "resource allocation + propensity + probabilistic forecasting under imperfect data," not as "election analytics"
- [ ] **Show that you think in systems, not just models:** ARCHITECTURE.md + data lineage + schema contracts + QA gates must all be visibly present and functional
- [ ] **Demonstrate operational thinking:** Makefile, CI/CD, DVC, reproducibility, versioning — these must be *working*, not aspirational
- [ ] **Add competitive comparison:** Create `reports/competitive_positioning.md`: compare this project to typical DS portfolios (churn model, recommendation engine, etc.) and explain why decision science + optimization is rarer and more valuable
- [ ] **Operational artifacts that others don't have:** Most portfolios have notebooks. This should have: schema contracts, QA gates, model cards, epistemic boundaries doc, decision log, allocation action matrix. Highlight these explicitly.
- [ ] **Quantified differentiation:** Show metrics that typical portfolios don't have — calibration curves, constraint satisfaction, allocation efficiency deltas, forecast interval coverage. Make these visually prominent.
- [ ] **Business realism:** Document constraints, tradeoffs, operational limitations. Most portfolios ignore this. Your project should show: "here's what would actually be needed in production"
- [ ] **Target audience clarity:** Make explicit: "This project is designed for hiring managers evaluating: analytics engineering, marketing science, decision science, optimization-focused data science roles"
- [ ] **Unique technical depth:** Pick one technical decision that others won't have made — e.g., "Pandera schema validation for every stage," "Bayesian inference for forecasting instead of simple regression," "IPF for demographic calibration instead of random sampling" — and make this prominent
- [ ] Acceptance: A DS hiring manager reads this project and thinks "I've never seen a portfolio like this" because of systems thinking + quantified results + decision framing + operational discipline, not just because of the electoral domain

---

## Summary Table

| Dimension | Actions to reach 10/10 | Key Acceptance Criterion |
|---|---|---|
| Business Framing | Business case doc + CFO scenario table + cost/benefit delta | CFO understands why without opening code |
| Data Science Framing | Implement complete Module A pipeline end-to-end, all models runnable | `poetry run python -m population_segmentation.pipeline` produces outputs |
| Architecture Quality | All 3 modules exist, all files present, CI works | Fresh clone → `make pipeline-dev` works |
| Codebase Maturity | Fix all P0/P1 bugs, pass Ruff/Black/Pyright, 80%+ test coverage | `ruff check . && black --check . && pyright . && pytest` all pass |
| Statistical Rigor | Generate calibration curves, silhouette plots, ROC-AUC, posterior traces | Statistician can verify all claims with evidence |
| Reproducibility | DVC initialized, lockfile present, hash-verified outputs, Docker works | Colleague gets byte-for-byte identical outputs as reference run |
| Documentation | ARCHITECTURE.md + ROADMAP.md + model cards + epistemic boundaries, no false claims | New hire can navigate codebase and understand every decision |
| Hiring Signal | Runnable code + quantified results + skills checklist + job mapping | Hiring manager clones, runs, sees results in 10 minutes |
| Credibility Consistency | All claims verified or removed, broken automation fixed, transparency on what's implemented | Skeptical reviewer finds evidence for every major claim |
| Portfolio Differentiation | Systems thinking visible + operational discipline + quantified results + decision framing | Manager thinks "I've never seen a portfolio like this" |