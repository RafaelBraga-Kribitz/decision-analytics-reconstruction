# Project Evaluation:

## Initial Audit (2026-05-10)
| Dimension | GPT Score | Claude Score (Initial) | Why GPT Was Overconfident |
|---|---|---|---|
| Business framing | 9.5 | 8.0 | Strong on paper but contingent on implementation that didn't exist |
| Data science framing | 9.0 | 5.5 | Framing in docs; actual DS pipeline was ~30% implemented |
| Architecture quality | 8.5 | 5.0 | Module B/C dirs missing, CI broken, Makefile bypassed virtualenv |
| Codebase maturity signals | 8.0 | 4.5 | 6+ P0/P1 bugs in 500 lines; CI didn't actually run tests |
| Statistical rigor signaling | 7.5 | 5.0 | Propensity, segmentation, Bayesian forecaster: none implemented |
| Reproducibility | 8.0 | 2.5 | DVC uninitialized, MLflow never called, `make pipeline-dev` failed |
| Documentation quality | 9.0 | 6.5 | transformation_log.md false claim; ARCHITECTURE.md missing |
| Hiring signal | 8.5 | 6.0 | Strong docs; collapsed on `git clone` and run |
| Credibility consistency | 7.0 | 3.5 | Dead URLs, false claims, nonexistent modules |
| Portfolio differentiation | 9.5 | 8.5 | Genuinely differentiated; GPT's most accurate score |

**Honest average: GPT 8.5 vs reality 5.5** — specification was exceptional; execution was thin.

---

## Re-evaluation (2026-05-13)

### Four Dimensions Assessed (where user took action)

| Dimension | Initial | Now | Ceiling | Progress |
|---|---|---|---|---|
| **Business Framing** | 8.0 | **9.0** | 9.5 | +1.0 (92% → ceiling) |
| **Data Science Framing** | 5.5 | **8.5** | 9.0 | +3.0 (94% → ceiling) |
| **Architecture Quality** | 5.0 | **9.0** | 9.5 | +4.0 (95% → ceiling) |
| **Codebase Maturity** | 4.5 | **9.0** | 9.5 | +4.5 (95% → ceiling) |
| **Portfolio Average (4D)** | **5.75** | **8.625** | **9.125** | +2.875 |

The project underwent substantial systemic improvement. The initial 5.5 was genuinely accurate for January–April 2026; the current 8.625 reflects disciplined execution of the action plan. **The remaining gaps to ceiling are structural** — not bugs or missing files, but architectural immaturity of Module C and missing human validation.

---

# Prioritized Action Plan — Impact Matrix

**Rationale:** Ordered by compound impact on (1) **Austrian Data/Analytics hiring credibility** and (2) **project completeness**. Solving high-priority items early multiplies the benefit of lower-priority ones.

## Tier 1: Blockers (Ceiling → 9.5 + Foundation for 10.0)

These solve the most critical perception and functionality gaps that hiring managers and technical reviewers will notice first.

| # | Task | Dimension | Why Critical | Est. effort | Status |
|---|------|-----------|--------------|-------------|--------|
| **T1-1** | Module C: Add CI lint/typecheck job (Pyright strict Module C `src/`) | Architecture Quality | Module C is visibly unvetted by toolchain. Austrian tech culture values tooling discipline. **Single job addition unlocks 0.3 points on all 4 dimensions.** | 0.5h | ✓ DONE (2026-05-13) |
| **T1-2** | Module C: Confirm slow pipeline acceptance test (`test_architecture_pipeline_dev_contract.py` passes with full `make pipeline-dev`) | Architecture Quality | This is the final architecture gate in the action plan. It's struck but unconfirmed in CI. | 0.25h | ✓ DONE (2026-05-13) |
| **T1-3** | Data Science: Replace JSON manifest with actual MLflow local file store (runs, params, metrics, artifacts) | Data Science Framing | JSON manifest is a workaround. MLflow is the standard. A DS reviewer will ask "where's the MLflow?" immediately. | 2.0h | ✓ DONE (2026-05-13) |
| **T1-4** | Data Science: Create `notebooks/01_end_to_end_walkthrough.ipynb` — one entity row traced to segment + propensity score | Data Science Framing | The action plan explicitly called for this. It's missing. Reviewers will notice the gap between "we have model cards" and "here's how it works on real data." | 1.5h | ✓ DONE (2026-05-13) |
| **T1-5** | Business Framing: Add CFO-friendly executive summary to `reports/business_case.md` (no jargon preamble, explicit "what is preference proxy?" in first paragraph) | Business Framing | Current business case assumes domain knowledge. A real CFO will bounce off "entities" and "preference proxy" without context. | 1.0h | ✓ DONE (2026-05-13) |

**T1 effort: ~5.25h. Impact: +0.35–0.40 points per dimension (ceiling unlock). Status: ALL COMPLETE.**

---

## Tier 2: Credibility & Coverage (Ceiling → 10.0)

High-impact items that move the project from 9.5 (credible, well-engineered) to 10.0 (defensible, complete, peer-reviewed).

| # | Task | Dimension | Why Important | Est. effort | Status |
|---|------|-----------|--------------|-------------|--------|
| **T2-1** | Codebase Maturity: Peer code review — have a senior engineer (or hiring manager) review src/population_segmentation/models/propensity.py and module_b_resource_allocation/models/allocation.py. Document feedback as testimonial or code review comment link. | Codebase Maturity | "No human code review" is the only remaining gap preventing 10.0 on codebase maturity. Hiring managers see this as lack of external validation. | 3.0h (async) | ⏳ PENDING (human-only) |
| **T2-2** | Architecture: Fix CI badge URL case (`rafaelbk` → `RafaelBraga-Kribitz`) and verify it resolves | Architecture Quality | Signals attention to detail. Broken badge = first impression of sloppiness. | 0.25h | ✓ DONE (2026-05-13) |
| **T2-3** | Module C: Achieve 80%+ coverage on Module C `src/` (currently ~60% estimated from overall 83%) | Codebase Maturity | Module C is thinner than A/B. Coverage signals completeness to reviewers. | 2.0h | ✓ DONE (2026-05-13, 81%) |
| **T2-4** | Type hints: Add justification tails to all `type: ignore` comments in Module B/C `src/` (policy parity with `noqa`) | Codebase Maturity | Current action says "optional follow-up." It's the last polish item for 10.0 strict. | 1.0h | ✓ DONE (2026-05-13) |
| **T2-5** | Business Framing: Add quantified comparison to typical DS portfolio (churn model, rec engine) in `reports/competitive_positioning.md` | Business Framing | Rare but high-value artifact. Shows you understand your market position. | 1.0h | ✓ DONE (2026-05-13) |

**T2 effort: ~7.25h. Impact: +0.20–0.25 points per dimension (10.0 unlock). Status: 4/5 COMPLETE (T2-1 pending human review).**

---

## Tier 3: Fit-and-Polish (Optional for 10.0, Required for Lasting Signal)

These do not block 10.0 but prevent regression and ensure the project ages well.

| # | Task | Dimension | Why Valuable | Est. effort | Status |
|---|------|-----------|--------------|-------------|--------|
| **T3-1** | Data Science: Add Module C methodology writeup (`METHODOLOGY.md` or equivalent bundling Bayesian spec, MCMC diagnostics, validation) | Data Science Framing | Module C exists but methodological prose is scattered. A coherent METHODOLOGY.md is the bridge between code and peer credibility. | 1.5h | ✓ DONE (2026-05-13) |
| **T3-2** | Data Science: Add SHAP feature importance chart to Streamlit dashboard (stretch: post-mortem plot to reports/) | Data Science Framing | ROADMAP lists this as "Medium priority." It's genuine value-add for reviewers. | 1.5h | ✓ DONE (2026-05-13) |
| **T3-3** | Reproducibility: Validate hash-reproducibility on fresh clone — document reference hashes and verify on second machine | Reproducibility | DVC would be full solution; this is a pragmatic checkpoint for now. | 1.0h | ✓ DONE (2026-05-13) |
| **T3-4** | Documentation: Create `HIRING_CONTEXT.md` section in README mapping project to 3 actual open roles at DACH companies (Knapp AG, TGW, Roche, etc.) | Hiring Signal | This project is for a specific job market. Making that explicit is powerful. | 1.0h | ✓ DONE (2026-05-13) |

**T3 effort: ~5.0h. Impact: Polish and market positioning. Status: ALL COMPLETE.**

---

# Full Action Plan (Organized by Dimension)

---

## 1. Business Framing (8.0 → 9.0 → 9.5 → 10.0)

---

# Procject Improvement and Action Plan List:
## 1. Business Framing (8.0 → 9.0)

**Current state (2026-05-13):** Executive problem statement, cost structure, and stakeholder routing are complete. Business case is technically rigorous. Remaining gap: domain obfuscation ("entities", "preference proxy") creates cognitive friction for CFO readers without prior domain knowledge.

**Completed actions (✓):**
- ✓ `reports/business_case.md` with cost structure, department-uniform naive baseline, MILP comparison, FX/budget shock scenarios
- ✓ Executive summary in README (60-second readable, references specific artifacts)
- ✓ `reports/stakeholder_scenario_table.md` (3 personas × 3 concerns, mapped to commands)
- ✓ Quantified allocation delta: naive vs MILP via `make module-b-allocate` and JSON manifest
- ✓ Risk/shock section: budget truncation, FX band sensitivity, documented with numbers

### **Ceiling (9.0 → 9.5)** — Bridge Domain Obfuscation

**1.a) [T1-5] Rewrite `reports/business_case.md` executive summary**
- [ ] **Goal:** First 200 words define every domain term ("entities" = registered voters, "preference proxy" = poll-derived support metric, etc.) with no jargon
- [ ] **Why:** CFO readers can now parse the document without domain knowledge. This is the missing piece preventing 10 points.
- [ ] **Acceptance:** A reader unfamiliar with the 2018 Paraguay election can understand the cost structure and MILP motivation from first screen alone
- **Effort: 1h** | Points: +0.3 to Business Framing

**1.b) Add glossary section to README or business_case.md**
- [ ] **Goal:** Table: term → definition → where term is used in code/artifacts
- [ ] **Why:** Creates a reference point for jargon. Hiring managers and CFO reviewers appreciate this.
- [ ] **Acceptance:** Glossary covers 10+ domain terms; links to code/test files
- **Effort: 0.5h** | Points: +0.2

### **Beyond Ceiling (9.5 → 10.0)** — Market Positioning

**1.c) Create `reports/competitive_positioning.md`** [T2-5]
- [ ] **Goal:** Explicitly compare this project to typical DS portfolios (churn models, recommendation engines) on decision science, MILP framing, and uncertainty quantification
- [ ] **Why:** Unique signal. Most portfolios don't think in terms of constrained optimization + propensity + probabilistic measurement. Making this explicit is a hiring differentiator.
- [ ] **Content:**
  - Typical DS portfolio: single-model (churn or recommendation) + confusion matrix + "deployed to production"
  - This portfolio: three-module system with inter-module contracts, uncertainty quantification, constrained resource allocation, reproducibility gates
  - Why this is rarer and more valuable for DACH market (Austria/Germany/Switzerland): decision science is applied at scale in manufacturing, logistics, pharma; simpler models don't scale to operational complexity
- [ ] **Acceptance:** Competitive positioning doc is 500+ words, specific, and backed by job market data (e.g., "JD from Knapp AG: 'optimize supply chain routing'")
- **Effort: 1.5h** | Points: +0.25

**1.d) Add case study summary for DACH hiring context**
- [ ] **Goal:** In README or separate `HIRING_CONTEXT.md`, explicitly position project for 3 target roles at Austrian/Swiss companies
- [ ] **Why:** Shows you understand your hiring target. Signals business acumen.
- [ ] **Content:** Example roles:
  - Analytics Engineer at Knapp AG (supply chain optimization)
  - Decision Scientist at TGW Logistics (route optimization)
  - Optimization Specialist at Roche (clinical trial resource allocation)
- Mapping: which project components demonstrate skills for each role
- [ ] **Acceptance:** 3 real job postings referenced; clear skill mappings
- **Effort: 1h** | Points: +0.25

**1.e) Add financial impact narrative (stretch)**
- [ ] **Goal:** Quantify hypothetical AUM or budget impact if this system were redeployed
- [ ] **Why:** CFOs and boards think in financial terms. A statement like "System optimized allocation for 6M USD budget; efficiency delta of 7-12% suggests 420K–720K USD in improved ROI if scaled" is powerful
- [ ] **Acceptance:** Impact narrative is present, footnoted with caveats (synthetic data, post-hoc calibration)
- **Effort: 1h** | Points: +0.15

---

## 2. Data Science Framing (5.5 → 8.5)

**Current state (2026-05-13):** Module A pipeline runs end-to-end with 5 output artifacts. Model hierarchy, feature engineering justification, and model cards are documented. Remaining gaps: MLflow is JSON manifest (not actual MLflow); Module C Bayesian inference is fixture-backed in CI; end-to-end walkthrough notebook is missing.

**Completed actions (✓):**
- ✓ Module A pipeline: `make pipeline-dev` runs and produces population_master_clean.parquet, segment_labels.parquet, participation_propensity.parquet, reachability CSVs, model_run_manifest.json
- ✓ `reports/model_hierarchy.md` (dependencies documented)
- ✓ `reports/module_a_model_io_spec.md` (input/output schemas)
- ✓ Feature engineering justification: `reports/feature_engineering_justification.md`
- ✓ Model cards: `module_a_population_segmentation/reports/model_card_{propensity,segmentation}.md`
- ✓ Model versioning: model_run_manifest.json includes model_type, train_date, git_commit

### **Ceiling (8.5 → 9.0)** — MLflow + End-to-End Notebook

**2.a) [T1-3] Replace JSON manifest with MLflow local file store**
- [ ] **Goal:** Initialize MLflow (default: `mlruns/` directory), log Module A pipeline outputs as runs with:
  - **Params:** seed, segmentation k, propensity threshold, department weights
  - **Metrics:** silhouette score, propensity ROC-AUC, Brier score, bootstrap ARI
  - **Artifacts:** model pickle files, propensity calibration curve PNG, segment centers CSV
- [ ] **Why:** MLflow is the DS standard. Reviewers expect it. JSON manifest is a workaround.
- [ ] **Code change:** In `pipeline/export.py`, add `mlflow.start_run()`, `mlflow.log_params()`, `mlflow.log_metrics()`, `mlflow.log_artifact()`
- [ ] **Acceptance:** `mlruns/` is gitignored; `poetry run mlflow ui` shows one or more runs with params, metrics, artifacts
- **Effort: 2h** | Points: +0.3 to Data Science Framing

**2.b) Verify `mlruns/` is properly gitignored and documented**
- [ ] **Goal:** Ensure `.gitignore` has `mlruns/` and `mlflow.db` entries; add a note to README on how to view runs
- [ ] **Why:** Prevents large artifacts from being committed; clarifies that MLflow is local, not shared
- [ ] **Acceptance:** `.gitignore` updated, README has 1-sentence guide: "Run `poetry run mlflow ui` to inspect logged models and metrics"
- **Effort: 0.25h** | Points: +0.1

**2.c) [T1-4] Create `notebooks/01_end_to_end_walkthrough.ipynb`**
- [ ] **Goal:** Jupyter notebook showing one row of synthetic data traced through entire pipeline:
  - **Cell 1:** Load raw synthetic data (1 entity row)
  - **Cell 2:** Show raw → after injection
  - **Cell 3:** Show cleaned version (all 14 steps annotated)
  - **Cell 4:** Features engineered
  - **Cell 5:** Segment assignment (k-means prediction)
  - **Cell 6:** Propensity score (logistic regression)
  - **Cell 7:** Summary: "Entity X ended in segment Y with propensity Z"
- [ ] **Why:** Reviewers want to see "this is how it works" at human scale. Model cards and tests show theory; notebook shows practice.
- [ ] **Acceptance:** Notebook is fully executable from clean clone; restart + run-all produces identical output
- **Effort: 1.5h** | Points: +0.3 to Data Science Framing

**2.d) Add determinism note to notebook**
- [ ] **Goal:** First cell of notebook documents the seed and guarantees reproducibility
- [ ] **Why:** Signals rigor. Reviewers will run the notebook and expect identical outputs.
- [ ] **Acceptance:** "With SEED=42 (set in cell 1), this notebook produces byte-identical outputs across runs"
- **Effort: 0.25h** | Points: +0.05

### **Beyond Ceiling (9.0 → 10.0)** — Methodological Depth

**2.e) [T3-2] Add SHAP feature importance chart to Streamlit dashboard (and/or reports/)**
- [ ] **Goal:** Compute TreeSHAP or LinearSHAP for propensity model; generate summary plot (mean absolute SHAP per feature)
- [ ] **Why:** High-value DS signal. Shows you understand model interpretability. ROADMAP lists this as medium priority.
- [ ] **Code:** In `segment_profiles.py` or new `shap_analysis.py`, compute SHAP values and plot
- [ ] **Acceptance:** Dashboard has a "Feature Importance (SHAP)" tab; plot shows top 10 features; values are saved to `reports/propensity_shap_summary.png`
- **Effort: 1.5h** | Points: +0.2 to Data Science Framing

**2.f) [T3-1] Create `METHODOLOGY.md` for Module C**
- [ ] **Goal:** Write a coherent methodological narrative for Module C (Bayesian hierarchical tracking) bundling:
  - Model specification in clear prose (not LaTeX, but readable) with structure
  - MCMC diagnostics interpretation (R-hat, ESS, divergences)
  - Posterior predictive checks: what they show, how to interpret calibration
  - Walk-forward validation approach and results
- [ ] **Why:** Module C has code and a Quarto post-mortem but lacks a bridge document for reviewers. This solves that.
- [ ] **Source:** Distill `module_c_forecasting_scenarios/reports/C_research_proof_table.md` and Quarto `post_mortem.qmd` into narrative
- [ ] **Acceptance:** METHODOLOGY.md is 1000+ words; covers all key statistical concepts; references code/test files
- **Effort: 2h** | Points: +0.2 to Data Science Framing

---

## 3. Architecture Quality (5.0 → 9.0)

**Current state (2026-05-13):** All three modules exist with complete surfaces, inter-module contracts at multiple layers (YAML, Pydantic, Pandera), ARCHITECTURE.md (348 lines), CI running with lint + typecheck, `make pipeline-dev` produces clean outputs. Remaining gaps: CI badge URL case mismatch; Module C excluded from Pyright typecheck; slow pipeline test unconfirmed in CI.

**Completed actions (✓):**
- ✓ Three modules: `module_a_population_segmentation/`, `module_b_resource_allocation/`, `module_c_forecasting_scenarios/` with proper `src/` layout
- ✓ Module A full surface: generator, injector, cleaner, validator, features, models, evaluation, pipeline, dashboard
- ✓ Module B: SPECIFICATION.md, allocation.py, run_allocation.py, regression tests
- ✓ Module C: hierarchical.py, pipelines, YAML configs, regression test
- ✓ Inter-module contracts: YAML (schema_contracts/), Pydantic (AllocationHandshakeRow), Pandera (DataFrame validators)
- ✓ Makefile: all poetry run, no bare python, regression test
- ✓ CI/CD: repo-make-test job, module-a lint+typecheck job, fresh clone passes
- ✓ ARCHITECTURE.md: 348 lines with Mermaid diagrams, schema contract table, walkthrough
- ✓ data/ directory structure: raw/interim/processed with .gitkeep
- ✓ Docker: compose version 3.9, Dockerfiles present
- ✓ Acceptance criterion: `make pipeline-dev` produces clean outputs without manual steps

### **Ceiling (9.0 → 9.5)** — Module C Parity + CI Polish

**3.a) [T1-1] Add Module C CI job (Pyright lint/typecheck)**
- [ ] **Goal:** Create new GitHub Actions job `module-c` with:
  - Black format check on `module_c_forecasting_scenarios/src`
  - Ruff check (zero warnings)
  - **Pyright STRICT mode** on `module_c_forecasting_scenarios/src/` (stretch; at minimum BASIC mode)
- [ ] **Why:** Module C is visibly unvetted by the toolchain. This is a glaring gap for Austrian tech culture, which values CI discipline.
- [ ] **Code change:** `.github/workflows/ci.yml` — duplicate `module-a` job, rename to `module-c`, change paths
- [ ] **Acceptance:** GitHub Actions shows green checkmark for `module-c` on main branch
- **Effort: 0.5h** | Points: +0.15 to Architecture Quality

**3.b) Update `pyproject.toml` to include Module C in Pyright**
- [ ] **Goal:** Change `[tool.pyright] include` to add `module_c_forecasting_scenarios/src`
- [ ] **Why:** Makes typecheck apply to all three modules, not just A+B
- [ ] **Current state:** `make typecheck` only covers Module A+B
- [ ] **Acceptance:** `make typecheck` now scans Module C with zero errors
- **Effort: 0.25h** | Points: +0.1

**3.c) [T1-2] Confirm `test_architecture_pipeline_dev_contract.py` passes in CI**
- [ ] **Goal:** Verify that the slow test (`@pytest.mark.slow`) runs and passes in a scheduled or manual CI job
- [ ] **Why:** This is the final architecture acceptance gate. It's in the action plan but never confirmed to run in CI.
- [ ] **Current state:** Test exists but is marked slow, so `make test` excludes it
- [ ] **Option 1:** Add a `repo-slow-tests` GitHub Actions job that runs `pytest -m slow` on a schedule (e.g., nightly)
- [ ] **Option 2:** Document in CI section of README that slow tests require manual `poetry run pytest -m slow`
- [ ] **Acceptance:** Either slow tests run in CI (green check) OR are documented as manual
- **Effort: 0.5h** | Points: +0.1

**3.d) [T2-2] Fix CI badge URL case in README**
- [ ] **Goal:** Change README CI badge URL from `rafaelbk/decision-analytics-reconstruction` to `RafaelBraga-Kribitz/decision-analytics-reconstruction`
- [ ] **Why:** Badge may fail to load if case is wrong. Signals sloppiness.
- [ ] **Verification:** Click badge in README; confirm it loads and shows current build status
- **Effort: 0.25h** | Points: +0.05

### **Beyond Ceiling (9.5 → 10.0)** — End-to-End Robustness

**3.e) Add Docker smoke test to CI**
- [ ] **Goal:** GitHub Actions job that runs `docker build . && docker run --rm <image> make test` to verify Docker-based execution matches host
- [ ] **Why:** Ensures reproducibility across environments. Signals production readiness.
- [ ] **Acceptance:** CI job `repo-docker-smoke` runs and passes
- **Effort: 1.5h** | Points: +0.2 to Architecture Quality

**3.f) Document `make pipeline-dev` expected runtime**
- [ ] **Goal:** Add a section to README: "Pipeline Runtime Expectations"
- [ ] **Content:** Expected wall time on reference hardware (e.g., "~2 minutes on M2 MacBook Pro with 16GB RAM"), with breakdown by stage
- [ ] **Why:** Reviewers will run it and want to know if it's hanging or progressing. Transparency here builds confidence.
- [ ] **Acceptance:** README section documents expected duration and breakdown
- **Effort: 0.5h** | Points: +0.1

---

**Old action list (all struck — kept for reference):**

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

## 4. Codebase Maturity Signals (4.5 → 9.0)

**Current state (2026-05-13):** 735 tests, 83% coverage, all P0/P1 bugs fixed, Ruff ✓, Black ✓, Pyright (A+B) ✓, pre-commit configured, Google docstrings, full type hints, deterministic RNG, O(n) rake benchmark. Remaining gap: no human code review of production surfaces.

**Completed actions (✓):**
- ✓ All 10 P0/P1 bugs fixed: _ENCODING_GARBLES, department_weights sum, docker-compose, __main__ blocks, enc_source/raw naming, column constants, KMeans n_jobs, CI --no-root, magic 0.42, max_noise_rate comment
- ✓ **735 tests collected** (731 passed, 2 skipped as of 2026-05-13)
- ✓ **83% combined coverage** (Module A+B+C src/) documented in `tests/README.md`
- ✓ Ruff: all checks passed, zero warnings
- ✓ Black: 103 files unchanged (fully formatted)
- ✓ Pyright basic: 0 errors, 0 warnings (Module A+B src/)
- ✓ Pre-commit hooks: Black, Ruff, Pyright, pytest-smoke, nbstripout
- ✓ Google docstrings: all public functions, regression test
- ✓ Type hints: full annotations, Any requires justification, regression test
- ✓ Deterministic RNG: seed contracts Module A+B, regression tests
- ✓ `_rake_categorical`: O(n) with <1s benchmark at N=500k

### **Ceiling (9.0 → 9.5)** — Module C Coverage + Type Safety

**4.a) Achieve 80%+ coverage on Module C src/**
- [ ] **Goal:** Current combined coverage is 83%, but Module C is thinner. Bring Module C to ≥80% standalone
- [ ] **Why:** Coverage signals completeness. Reviewers check individual module coverage to spot weak areas.
- [ ] **Current state:** Module C is likely ~60–70% due to fixture-backed slow tests
- [ ] **Actions:**
  - Add tests for helper functions in `module_c_forecasting_scenarios/src/`
  - Add calibration logic tests
  - Add run_* pipeline tests (fast smoke, not full NUTS)
- [ ] **Acceptance:** `poetry run pytest module_c_forecasting_scenarios/tests/ --cov=module_c_forecasting_scenarios/src` shows ≥80%
- **Effort: 2h** | Points: +0.2 to Codebase Maturity

**4.b) Add Pyright typecheck to Module C src/**
- [ ] **Goal:** Extend `make typecheck` to include `module_c_forecasting_scenarios/src`
- [ ] **Why:** Type safety is a maturity signal. Module C being excluded looks unfinished.
- [ ] **Current state:** `make typecheck` only checks Module A+B
- [ ] **Actions:** Update `pyproject.toml` `[tool.pyright] include` list
- [ ] **Acceptance:** `make typecheck` scans Module C with zero errors
- **Effort: 0.5h** | Points: +0.1

**4.c) Add type: ignore justification tails in Module B/C**
- [ ] **Goal:** Policy parity: every `type: ignore` comment gets a short tail explaining why
- [ ] **Why:** Current action plan notes this as "optional follow-up." It's the polish detail for 10.0 strict.
- [ ] **Example:** `result = func(x)  # type: ignore  # func has untyped return in external lib`
- [ ] **Actions:** Grep `type: ignore` in `module_b_resource_allocation/src` and `module_c_forecasting_scenarios/src`; add comment tails
- [ ] **Acceptance:** All `type: ignore` comments have justification tails
- **Effort: 1h** | Points: +0.1

### **Beyond Ceiling (9.5 → 10.0)** — Human Validation

**4.d) [T2-1] Peer code review — Have a senior engineer review production surfaces**
- [ ] **Goal:** Solicit review of:
  - `module_a_population_segmentation/src/population_segmentation/models/propensity.py` (propensity model)
  - `module_b_resource_allocation/src/module_b_resource_allocation/models/allocation.py` (MILP solver wrapper)
  - `module_c_forecasting_scenarios/src/module_c_forecasting_scenarios/models/tracking/hierarchical.py` (Bayesian model)
- [ ] **Who:** External reviewer (senior engineer, hiring manager, or academic collaborator)
- [ ] **What:** Code review comment thread with specific feedback on:
  - Correctness of algorithms
  - Clarity of implementation
  - Test coverage quality
  - Documentation completeness
- [ ] **Why:** "No human code review" is the only thing preventing 10.0 on codebase maturity. It's the hardest signal to fake.
- [ ] **Artifact:** Add link to code review in README (e.g., GitHub issue or external testimonial)
- [ ] **Acceptance:** Code review is documented and linked in README
- **Effort: 3h (async)** | Points: +0.3 to Codebase Maturity, +0.2 to Hiring Signal

**Old action list (all struck — kept for reference):**

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

---

## Master Summary (4 Dimensions Under Review)

### Scoring Evolution

| Dimension | Original | Now | Ceiling | 10.0 | % to Ceiling | Effort (Total) |
|---|---|---|---|---|---|---|
| **Business Framing** | 8.0 | 9.0 | 9.5 | 10.0 | 100% → 100% | 5.5h |
| **Data Science Framing** | 5.5 | 8.5 | 9.0 | 10.0 | 94% → 100% | 7.5h |
| **Architecture Quality** | 5.0 | 9.0 | 9.5 | 10.0 | 95% → 100% | 5.5h |
| **Codebase Maturity** | 4.5 | 9.0 | 9.5 | 10.0 | 95% → 100% | 6.5h |
| **Portfolio Average** | 5.75 | 8.625 | 9.125 | 10.0 | 95% → 100% | 25h |

**Key insight:** The four dimensions under review show massive systemic improvement (+2.875 average, +50% relative). The remaining 0.5-point gaps to ceiling are **structural**, not bugs. The final 0.75–1.0 point to 10.0 requires human validation (code review) and specialized Domain work (Module C).

### Prioritized Quick Wins (Tier 1 + Tier 2 Accelerators)

**Target:** Reach 9.5 ceiling on all 4 dimensions in ~10 hours (Tier 1 + critical Tier 2).

| Priority | Task | Dimension | Effort | Impact | Owner | Status |
|---|---|---|---|---|---|---|
| **P0** | [T1-1] Add Module C CI job (Pyright) | Arch + Codebase | 0.5h | Unlocks ~0.3 points across all 4D | [@user] | Pending |
| **P0** | [T1-3] Implement MLflow logging | Data Science | 2.0h | DS credibility signal | [@user] | Pending |
| **P0** | [T1-4] Create end-to-end notebook | Data Science | 1.5h | DS methodology proof | [@user] | Pending |
| **P0** | [T1-5] Rewrite business_case.md glossary | Business | 1.0h | CFO accessibility | [@user] | Pending |
| **P1** | [T2-1] Peer code review | Codebase | 3.0h (async) | Unlocks 10.0 ceiling | [@external] | Pending |
| **P1** | [T1-2] Confirm pipeline acceptance test | Arch | 0.25h | Architecture closure | [@user] | Pending |
| **P2** | [T3-2] Add SHAP to dashboard | Data Science | 1.5h | DS interpretability | [@user] | Pending |
| **P2** | [T2-2] Fix CI badge URL | Arch | 0.25h | Signals attention to detail | [@user] | Pending |

**Tier 1 subtotal:** 5.25h → +0.35–0.40 ceiling points
**Tier 1 + Key Tier 2:** ~10h → +0.45–0.55 ceiling points (near-ceiling on all 4D)

### Beyond Ceiling (10.0 Stretch Goals)

These are the 0.75–1.0 point deltas to reach 10.0 on all four dimensions:

| Goal | Dimension | Effort | Why It Matters | Interdependencies |
|---|---|---|---|---|
| **Human code review of src/** | Codebase | 3h (async) | Ends the "no external validation" gap | None |
| **Module C methodological writeup** | Data Science | 1.5h | Bridges code → peer credibility for Bayesian model | T1-3 (MLflow) |
| **Module C 80%+ coverage** | Codebase | 2h | Signals completeness; Module C parity with A/B | T1-1 (CI job) |
| **Competitive positioning doc** | Business | 1.5h | Unique market signal (rare for portfolios) | None |
| **Docker smoke test in CI** | Architecture | 1.5h | Environment reproducibility guarantee | None |
| **DACH hiring context mapping** | Business + Hiring | 1h | Explicit targeting for Austrian market | None |

**Total beyond ceiling: ~10.5h** to reach solid 10.0 on all four dimensions.

---

## Full Action Plan Reference (Organized by Dimension)

**This document contains:**
- **§1 Business Framing (8.0 → 9.0 → 9.5 → 10.0):** Glossary, competitive positioning, DACH hiring context, financial impact narrative
- **§2 Data Science Framing (5.5 → 8.5 → 9.0 → 10.0):** MLflow, end-to-end notebook, SHAP, Module C methodology
- **§3 Architecture Quality (5.0 → 9.0 → 9.5 → 10.0):** Module C CI job, Pyright parity, slow test confirmation, badge fix, Docker smoke test
- **§4 Codebase Maturity (4.5 → 9.0 → 9.5 → 10.0):** Module C coverage, type safety, peer code review

**For older sections (§5–§10):**
- These were marked as "not under review" in this session (user took action on only 4 of 10 dimensions)
- Original action lists remain struck in place below for reference
- If you need to pursue §5–§10, the original prompts are preserved in this document

---

## Original Summary Table (All 10 Dimensions)

| Dimension | Actions to reach 10/10 | Key Acceptance Criterion |
|---|---|---|
| **1. Business Framing** | Business case doc + CFO scenario table + cost/benefit delta | CFO understands why without opening code |
| **2. Data Science Framing** | Implement complete Module A pipeline end-to-end, all models runnable | `poetry run python -m population_segmentation.pipeline` produces outputs |
| **3. Architecture Quality** | All 3 modules exist, all files present, CI works | Fresh clone → `make pipeline-dev` works |
| **4. Codebase Maturity** | Fix all P0/P1 bugs, pass Ruff/Black/Pyright, 80%+ test coverage | `ruff check . && black --check . && pyright . && pytest` all pass |
| **5. Statistical Rigor** | Generate calibration curves, silhouette plots, ROC-AUC, posterior traces | Statistician can verify all claims with evidence |
| **6. Reproducibility** | DVC initialized, lockfile present, hash-verified outputs, Docker works | Colleague gets byte-for-byte identical outputs as reference run |
| **7. Documentation** | ARCHITECTURE.md + ROADMAP.md + model cards + epistemic boundaries, no false claims | New hire can navigate codebase and understand every decision |
| **8. Hiring Signal** | Runnable code + quantified results + skills checklist + job mapping | Hiring manager clones, runs, sees results in 10 minutes |
| **9. Credibility Consistency** | All claims verified or removed, broken automation fixed, transparency on what's implemented | Skeptical reviewer finds evidence for every major claim |
| **10. Portfolio Differentiation** | Systems thinking visible + operational discipline + quantified results + decision framing | Manager thinks "I've never seen a portfolio like this" |
---

## Model Routing (LLM Strategy)

**Applied heuristic from `llm_use_strategy.md`:**
- Fast/boilerplate → GPT-5 Mini / Sonnet
- Mid-complexity engineering → GPT-5 / Sonnet
- Statistical/optimization rigor → GPT-5.5 / Opus 4.7
- Architecture/strategy/positioning → Opus 4.7 / GPT-5.5

### Tier 1 Tasks

| Task | Type | Recommended Model | Rationale |
|---|---|---|---|
| T1-1: Module C CI job | CI/CD setup | **GPT-5 / Sonnet** | Standard .yml template, no rigor escalation |
| T1-2: Confirm pipeline test | Testing + verification | **GPT-5 Mini / Sonnet** | Shallow check, boilerplate verification |
| T1-3: MLflow logging | Mid-complexity engineering | **GPT-5 / Sonnet** | API integration, typed Python, standard pattern |
| T1-4: End-to-end notebook | EDA + documentation | **GPT-5 / Sonnet** | Pandas pipeline, reproducible seed, no rigor |
| T1-5: Business case glossary | Strategic documentation | **Opus 4.7 / GPT-5.5** | Positioning matters; CFO credibility signal escalates |

### Tier 2 Tasks

| Task | Type | Recommended Model | Rationale |
|---|---|---|---|
| T2-1: Peer code review | Human/async (no LLM) | **N/A** | External validation; use hiring manager or peer |
| T2-2: Fix CI badge URL | Repository cleanup | **GPT-5 Mini / Sonnet** | Regex + string replacement, boilerplate |
| T2-3: Module C 80% coverage | Testing + refactoring | **GPT-5 / Sonnet** | Unit test writing, parametrization, no rigor |
| T2-4: Type ignore tails | Code cleanup | **GPT-5 Mini / Sonnet** | Grep + comment insertion, boilerplate |
| T2-5: Competitive positioning | Portfolio strategy | **Opus 4.7 / GPT-5.5** | High-stakes differentiation; hiring signal; escalate |

### Tier 3 Tasks

| Task | Type | Recommended Model | Rationale |
|---|---|---|---|
| T3-1: Module C methodology | Statistical docs + rigor | **GPT-5.5 / Opus 4.7** | Bayesian reasoning, diagnostics, uncertainty; rigor matters |
| T3-2: SHAP on dashboard | Feature engineering + viz | **GPT-5 / Sonnet** | Mid-complexity; standard sklearn pattern |
| T3-3: Hash reproducibility | Documentation + verification | **GPT-5 Mini / Sonnet** | Boilerplate test harness |
| T3-4: DACH hiring context | Hiring signal + strategy | **Opus 4.7 / GPT-5.5** | Market positioning for Austria; strategic escalation |

### Summary

**Commodity tier (Sonnet/Mini, ~8h):** T1-1, T1-2, T1-3, T1-4, T2-2, T2-3, T2-4, T3-2, T3-3  
**Premium tier (GPT-5.5/Opus, ~4h):** T1-5, T2-5, T3-1, T3-4  
**Human-only:** T2-1 (peer code review)

**Key:** 4 of 18 tasks justify premium models; all positioning/rigor-critical. Remainder are engineering commodity.
