# Professional-grade output rubrics

Defines what "professional output" means for each module and for cross-module work. These rubrics are the **authoritative standard** for qa-gatekeeper verdicts and harness simulation pass/fail.

---

## What professional output is NOT

- Test coverage without TDD cycle evidence (watching tests fail first).
- Numeric results without source trace (model run that produced them).
- "Completed" tasks without verification commands run in the session.
- Gate rows answered "✓" without a command + result.
- Modules proceeding past a block condition.

---

## Module A — Professional output standard

### Code quality
- All `src/` functions have a corresponding test written and observed to fail before implementation.
- No magic numbers; all thresholds come from `calibration_anchors.yaml` or `generation.yaml`.
- Cleaning pipeline: 14 steps each independently testable and tested.
- Transformation log entry for every cleaning step that runs in production.

### Data quality
- DAMA-5 scorecard produced and attached to `reports/qa_report_YYYYMMDD.md`.
- All five dimensions scored; any score < 80% has documented remediation.
- `validator.py` runs without `QAGateFailure` on clean-layer output.

### Modeling quality
- Calibration: all 8 anchor values within defined tolerances (see `module-a-specialist.md` Phase 1).
- Segmentation: silhouette > 0.35 on held-out partition; bootstrap ARI > 0.80.
- Propensity: Brier < 0.22; reliability diagram max deviation < 3 pp per decile; AUC-ROC > 0.70.
- Model cards (`model_card_segmentation.md`, `model_card_propensity.md`) up to date.

### Deliverables
- `population_master_clean.parquet` with `entity_id`, `segment_label`, `participation_propensity`, `municipality_clean`, `department_clean` fields present and non-null.
- SHAP permutation importance plot attached to model card.
- Streamlit dashboard loads, all three tabs render, k-slider functional.

---

## Module B — Professional output standard

### Code quality
- All solver configurations and constraints read from `resource_config.yaml`; zero hard-coded literals.
- Every LP or MILP formulation has a unit test that verifies the expected constraint binds.
- FastAPI endpoint has integration test asserting schema conformance and p95 latency ≤ 2 s.

### Allocation quality
- Solver returns `OPTIMAL` or `FEASIBLE`; `INFEASIBLE` is always a bug, never an acceptable result.
- Coverage ≥ 80%; BCP corridor ≤ 10%; FX within ±0.5% of BCP.
- Sensitivity snapshot: 1% relaxation of top binding constraint results documented.
- Diminishing-returns curve validated against `sigmoid_inflection` and `sigmoid_slope` config values.

### Deliverables
- `allocation_output.parquet` (or equivalent) conforming to `schema_contracts/allocation_output.yaml`.
- `reports/allocation_run_YYYYMMDD.md` with solver status, objective value, binding constraints.
- FX rate provenance statement (BCP midpoint date + source).

---

## Module C — Professional output standard

### Bayesian workflow quality
All 8 steps of the PyMC canonical workflow completed and evidenced:
1. Data preparation with standardized predictors.
2. Model with weakly informative priors, non-centered hierarchical offsets.
3. Prior predictive check (1,000 samples; documented).
4. MCMC sampling (draws=2000, tune=1000, chains=4, target_accept=0.9).
5. Convergence diagnostics: R-hat < 1.01, ESS > 400, zero post-tuning divergences.
6. Posterior predictive check (visual + numeric, < 3 pp deviation).
7. Results analysis with HDI intervals (95%) reported everywhere.
8. Model comparison via LOO/WAIC if ≥ 2 candidates.

### DS-QA quality
All 6 layers of DS-QA completed (see `qa-gatekeeper.md`). Confidence verdict documented.

### Calibration quality
- National baseline scenario: 61.25% ±0.5 pp.
- Scenario fan-width within `calibration.yaml:mc_scenario_fan_tolerance`.
- Series gate declaration filed before sampling.
- Exit measurement HDI coverage ≥ 90% on holdout.

### Deliverables
- `idata` ArviZ InferenceData object saved and referenced in report.
- `reports/mcmc_diagnostics_YYYYMMDD.md` with full `az.summary()` table.
- `reports/series_gate_YYYYMMDD.yaml` with declared priors and justifications.
- Quarto report renders to HTML without error; all numeric values traced to `idata`.

---

## Cross-module — Professional output standard

### Contract adherence
- Every field name and type change in shared outputs goes through `integration-impact-auditor`.
- `schema_contracts/*.yaml` files updated before, not after, implementation.
- Downstream tests (`module_b/test_input_schema.py`, `module_c/test_input_schema.py`) pass.

### Impact documentation
- Cross-module impact map completed in plan before execution.
- `reports/integration_audit_YYYYMMDD.md` produced by `integration-impact-auditor`.

### Terminology
- Zero banned terms in all field names, string literals, config keys, report text, and comments.
- Consistent vocabulary: use "participation rate", "entity", "coordinator role", "area tier" (see scope §12 for full list).

---

## QA verdict mapping to rubric

| Rubric area | Failing it produces | Verdict |
|-------------|----------------------|---------|
| TDD cycle not evidenced | Missing red-green proof | FAIL — REVISE |
| Gate value outside threshold | Numeric gate FAIL | FAIL — REVISE |
| MCMC R-hat ≥ 1.01 | Convergence failure | BLOCK |
| MCMC divergences > 0 | Sampling pathology | BLOCK |
| Banned terminology found | Compliance violation | FAIL — REVISE |
| Schema contract broken | Integration risk | BLOCK (until auditor co-signs) |
| National scenario > ±0.5 pp | Calibration drift | BLOCK |
| Solver INFEASIBLE | Constraint bug | FAIL — REVISE |
| Quarto render failure | Report delivery blocked | BLOCK |
