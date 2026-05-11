# Roadmap

Honest status of each module and the next concrete milestones.

---

## Module A — Population Modeling and Segmentation

**Status: production-grade**

- 140 tests passing, CI-gated at 80% coverage
- Full 14-step cleaning pipeline with documented flaw injection and QA gates
- Logistic regression + Platt calibration + department rake; all acceptance criteria met
- DBSCAN pre-pass + K-Means (k=6); silhouette > 0.35, bootstrap ARI > 0.80
- Streamlit dashboard deployed on Render
- Model cards, transformation log, QA reports in `reports/`
- Schema contracts published for downstream modules

**Next milestones:**

| Item | Priority |
|---|---|
| Ingest full TSJE departmental participation table (all 18 departments verified, not estimated) | High |
| Add SHAP feature importance chart to Streamlit dashboard | Medium |
| Parameterize flaw injection rates via CLI for sensitivity testing | Low |

---

## Module B — Resource Allocation Engine

**Status: analytically complete, not packaged to Module A engineering standard**

- PuLP CBC solver with OPTIMAL-status enforcement
- Budget envelope, reach cap, FX corridor, and municipality coverage constraints
- Weekly time-series allocation over 18 weeks, 18 departments, 11 channels
- FX modeling: BCP PYG/USD reference rate with scenario bands (5,500–5,700 corridor)
- FastAPI re-optimization endpoint; P95 latency target ≤ 2 sec under 10 concurrent requests
- Counterfactual analysis (uniform vs. optimized spend comparison)

**What is missing vs. Module A standard:**

- Test coverage below 80% threshold
- No CI enforcement for Module B
- FastAPI endpoint not containerized for one-command deployment
- `alloc_mean_persuasion_contacts` not yet linked to Module C (known integration gap)

**Next milestones:**

| Item | Priority |
|---|---|
| Lift test coverage to 80% with CI enforcement | High |
| Wire `alloc_mean_persuasion_contacts` output to Module C scenario engine | High |
| Containerize FastAPI endpoint with Docker Compose | Medium |
| Publish `budget_allocation_weekly_v1.yaml` schema contract | Medium |

---

## Module C — Probabilistic Forecasting

**Status: analytically complete, not packaged to Module A engineering standard**

- PyMC Bayesian hierarchical tracker with house-effect shrinkage priors
- Four polling sources modeled with estimated house effects (−5.1 pp to +3.8 pp)
- 10,000-draw Monte Carlo scenario engine (baseline / moderate / extreme shock profiles)
- MCMC diagnostics: R-hat < 1.01, ESS > 400, zero divergences
- Quarto post-mortem document (`portfolio/quarto/post_mortem.qmd`; `quarto render` exit 0 required)

**What is missing vs. Module A standard:**

- Module B integration gap: `alloc_mean_persuasion_contacts` is unlinked (win-probability cannot yet reflect budget reallocation decisions)
- Test coverage below 80% threshold
- No CI enforcement for Module C

**Next milestones:**

| Item | Priority |
|---|---|
| Complete Module B integration (budget reallocation → win probability delta) | High |
| Lift test coverage to 80% with CI enforcement | High |
| Add posterior predictive check plots to Quarto deliverable | Medium |
| Geographic win-probability heatmap from `battleground_probability_heatmap.geojson` | Low |

---

## Cross-module

| Item | Status |
|---|---|
| Schema contracts (Module A → B) | Published |
| Schema contracts (Module B → C) | Stub; pending Module B finalization |
| End-to-end pipeline smoke test | Not yet implemented |
| DVC artifact tracking | Config present; not yet enforced in CI |
| Docker Compose full-stack | Partial (Module A only) |
| `01_synthetic_data_validation.ipynb` (marginal + joint correlation audit, nbval) | **Deferred** — marginal and contract checks are covered by pandera gates, CI config integrity, and exploratory notebooks under `module_a_population_segmentation/notebooks/` (e.g. segmentation analysis). A dedicated validation notebook remains optional follow-up. |

### Full 360 audit — reconciliation status (2026-05)

This section aligns the **original portfolio audit** with what the repository actually ships after the **reconciliation plan** (lighter Module A layout, split features, Pandera gates). It replaces informal “minus generator …” notes with the current truth.

**Delivered vs audit (aligned or superseded)**

- **P0 encoding:** Raw injector encoding flaw path fixed; injection runs at configured rates without `NameError`.
- **Weights + checks:** `generation.yaml` department weights sum to 1.0; CI runs a config-integrity assert on that sum.
- **MLflow pin + Compose network:** `docker/mlflow.Dockerfile` pins `mlflow==2.12.2`; `docker-compose.yml` attaches `module_a` and `mlflow` to `analytics_net`; CI validates `docker compose config` and builds both images.
- **CLIs:** `python -m population_segmentation.data.generator` (`--config`, `--output`, `--seed`, `load_dotenv()`, optional `--sample-size`), `raw_injector`, and `cleaner` entry points; Makefile / `pipeline-dev` targets invoke them.
- **Raw vs clean ENC naming:** Generator emits `enc_source_raw` per raw contract; clean contract and cleaner use `enc_source` (see `schema_contracts/` + `cleaner.py`).
- **Propensity `stratify_by`:** `module_a_population_segmentation/config/model_params.yaml` matches `PropensityModel` stratification behavior.
- **Decision log:** `reports/decision_log.md` records major modeling and pipeline choices.
- **Model cards:** `module_a_population_segmentation/reports/model_card_segmentation.md`, `model_card_propensity.md`.
- **Segment → action bridge:** `module_a_population_segmentation/reports/segment_action_matrix.md`.
- **README + CI hardening:** Module A workflow includes Black/Ruff/Pyright, coverage floor, department-weights gate, job timeouts, Docker smoke (`compose config`, image build, import smoke).
- **Module B specification:** `module_b_resource_allocation/SPECIFICATION.md`.
- **Appendix FX narrative:** `appendix/verified_calibration_anchors_full.md` Module B FX row documents the Q1 2018 BCP band and corrects the older 5,800–6,000 wording.

**Intentionally different from the early “textbook audit” stack**

The audit described a **monolithic** teaching layout; the reconciled repo standardizes on what the rest of the code actually uses:

- **Cleaner:** Fourteen *logical* steps in `reports/transformation_log.md`, implemented as a single focused `cleaner.py` pipeline (not a literal one-function-per-row textbook layout).
- **Features:** No `engineer.py`; feature work lives in `population_segmentation/features/{demographic,behavioral,reachability}.py`.
- **Validation:** No standalone `evaluation/validator.py` as the sole QA surface. **Pandera** contracts live in `evaluation/schema_validator.py` (e.g. `validate_clean_population` at cleaner exit). **`data/validator.py`** supplies `validate_schema`, `validate_calibration_anchors`, and `QAGateFailure` for programmatic checks where callers wire them.
- **Architecture copy:** `ARCHITECTURE.md` documents `schema_validator.py` and `data/validator.py`, not a fictional `evaluation/validator.py`.

**Strict optional parity (only if you want audit-number-for-number completeness)**

| Ref | Gap |
| --- | --- |
| 1.3 | Streamlit / deploy **healthcheck** in CI or image (curl in Dockerfile or Python HTTP probe). |
| 5.1 | **Exact** set-equality assertion on injector `df.attrs["flaw_types_injected"]` vs canonical flaw-type catalog. |
| 5.2 | Richer shared **`conftest`** fixtures for cross-module / cross-scenario tests. |
| 6.1 | Dedicated **`fx_context.yaml`** (or equivalent) split from calibration anchors. |
| 6.2–6.3 | Fuller **contract / anchor** YAML restructuring and automated cross-file gates. |
| 9.3–9.4 | Optional **yamllint**, **nbval** / notebook smoke in CI, explicit **`sample_size`** override in smoke jobs. |
| 10.1 | **`METHODOLOGY.md`** (or equivalent) bundling Module C methodology for external readers. |

**Recently closed (formerly “still open”)**

- **1.6** — `raw_injector.py` column access aligned with `population_segmentation/utils/schema.py` constants for injected raw fields (names, DOB, phone, qualitative columns, schema drift flag).
- **1.4** — Generator CLI loads `.env` and supports `--sample-size` (see `test_generator_module_cli_sample_size_override`).
- **ARCHITECTURE.md** — Validator references updated to real modules (`evaluation/schema_validator.py`, `data/validator.py`).
- **`make graphify`** — Makefile invokes `poetry run python -m graphify update .` so the target works when the console script is not on `PATH`.
