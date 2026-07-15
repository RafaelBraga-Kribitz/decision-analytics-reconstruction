.PHONY: install lint format typecheck test coverage all clean module-a-export module-a-pipeline module-a-report-charts graphify \
	module-b-allocate module-b-allocate-sensitivity module-b-routing module-b-api \
	test-module-a test-module-b test-module-c pipeline-full \
	module-c-tracking module-c-exit module-c-mc module-c-all module-c-walk-forward module-c-ppc \
	precommit validate doc-path-verify doc-registry-verify doc-registry-schema-export portfolio-verify tier3-smoke e2e-smoke audit verify session-start session-end debt-scan debt-check

MODULE_A_SRC := module_a_population_segmentation/src
MODULE_A_TESTS := module_a_population_segmentation/tests
MODULE_A_APP := module_a_population_segmentation/app
MODULE_B_SRC := module_b_resource_allocation/src
MODULE_B_TESTS := module_b_resource_allocation/tests
MODULE_C_SRC := module_c_forecasting_scenarios/src
MODULE_C_TESTS := module_c_forecasting_scenarios/tests
ROOT_TESTS := tests
SCRIPTS := scripts
MODULE_TEST_ARGS := $(MODULE_A_TESTS) $(MODULE_B_TESTS) $(MODULE_C_TESTS) $(ROOT_TESTS)
COV_FLAGS := --cov=$(MODULE_A_SRC) --cov=$(MODULE_B_SRC) --cov=$(MODULE_C_SRC) --cov-report=term-missing --cov-report=xml --cov-fail-under=80

install:
	poetry install

format:
	poetry run black $(MODULE_A_SRC) $(MODULE_A_TESTS) $(MODULE_A_APP) $(MODULE_B_SRC) $(MODULE_B_TESTS) $(MODULE_C_SRC) $(MODULE_C_TESTS) $(ROOT_TESTS) $(SCRIPTS) --exclude 'tests/test_eda.py'

lint:
	poetry run ruff check $(MODULE_A_SRC) $(MODULE_A_TESTS) $(MODULE_A_APP) $(MODULE_B_SRC) $(MODULE_B_TESTS) $(MODULE_C_SRC) $(MODULE_C_TESTS) $(ROOT_TESTS) $(SCRIPTS) --extend-exclude tests/test_eda.py
	poetry run black --check $(MODULE_A_SRC) $(MODULE_A_TESTS) $(MODULE_A_APP) $(MODULE_B_SRC) $(MODULE_B_TESTS) $(MODULE_C_SRC) $(MODULE_C_TESTS) $(ROOT_TESTS) $(SCRIPTS) --exclude 'tests/test_eda.py'

typecheck:
	poetry run pyright $(MODULE_A_SRC) $(MODULE_B_SRC) $(MODULE_C_SRC)

test:
	poetry run pytest $(MODULE_TEST_ARGS) -v --tb=short -m "not slow" $(COV_FLAGS)

precommit:
	poetry run pre-commit install --hook-type pre-commit --hook-type commit-msg
	poetry run pre-commit run --all-files

validate: lint typecheck test doc-path-verify doc-registry-verify

doc-path-verify:
	poetry run python scripts/verify_doc_code_paths.py

doc-registry-verify:
	poetry run python scripts/build_docs_registry.py
	poetry run python scripts/generate_doc_index.py --write
	poetry run python scripts/verify_doc_registry.py
	poetry run python scripts/check_doc_frontmatter.py
	poetry run python scripts/check_doc_drift.py
	poetry run python scripts/generate_doc_index.py --check

doc-registry-schema-export:
	poetry run python scripts/export_doc_registry_schema.py

portfolio-verify:
	poetry run python scripts/portfolio_verify.py

tier3-smoke:
	poetry run python scripts/check_terminology.py
	poetry run python scripts/verify_doc_code_paths.py
	poetry run python -c "import mlflow; print('mlflow_ok', mlflow.__version__)"

e2e-smoke:
	poetry run pytest tests/test_portfolio_e2e_smoke.py -v --tb=short

test-module-a:
	poetry run pytest $(MODULE_A_TESTS) -v --tb=short

test-module-b:
	poetry run pytest $(MODULE_B_TESTS) -v --tb=short

test-module-c:
	MC_FAST=1 poetry run pytest $(MODULE_C_TESTS) -v --tb=short

module-c-tracking:
	MLFLOW_TRACKING_URI=$(or $(MLFLOW_TRACKING_URI),file:./mlruns) \
	poetry run python -m module_c_forecasting_scenarios.pipeline.run_tracking \
		--raw-csv module_c_forecasting_scenarios/tests/fixtures/polls_raw_fixture.csv \
		--out-dir data/processed/module_c/tracking

module-c-exit:
	MLFLOW_TRACKING_URI=$(or $(MLFLOW_TRACKING_URI),file:./mlruns) \
	poetry run python -m module_c_forecasting_scenarios.pipeline.run_exit \
		--raw-csv module_c_forecasting_scenarios/tests/fixtures/polls_raw_fixture.csv \
		--out-dir data/processed/module_c/exit

module-c-mc:
	MLFLOW_TRACKING_URI=$(or $(MLFLOW_TRACKING_URI),file:./mlruns) \
	poetry run python -m module_c_forecasting_scenarios.pipeline.run_monte_carlo \
		--raw-csv module_c_forecasting_scenarios/tests/fixtures/polls_raw_fixture.csv \
		--out-dir data/processed/module_c/mc

# B→C handshake: pass the Module B allocation parquet when it exists so the
# Monte Carlo draws carry real persuasion contacts (silent-zero is an error).
MODULE_B_ALLOC := data/processed/module_b/allocation_baseline.parquet
module-c-all:
	MLFLOW_TRACKING_URI=$(or $(MLFLOW_TRACKING_URI),file:./mlruns) \
	poetry run python -m module_c_forecasting_scenarios.pipeline.run_all \
		--raw-csv module_c_forecasting_scenarios/tests/fixtures/polls_raw_fixture.csv \
		--out-dir data/processed/module_c/run_all \
		$(if $(wildcard $(MODULE_B_ALLOC)),--allocation-parquet $(MODULE_B_ALLOC),)

module-c-walk-forward:
	MLFLOW_TRACKING_URI=$(or $(MLFLOW_TRACKING_URI),file:./mlruns) \
	poetry run python -m module_c_forecasting_scenarios.pipeline.run_walk_forward \
		--raw-csv module_c_forecasting_scenarios/tests/fixtures/polls_raw_fixture.csv \
		--out-dir data/processed/module_c/walk_forward

# Sampler config matches the committed reports/module_c_lowo_metrics.json artifact:
# reduced-draw base (MC_FAST) widened to 4 chains x 300 draws / 300 tune (seed 42).
# Disclosed in reports/VALIDATION.md § Module C — full-NUTS v0.4 gates are the
# preferred config where a C compiler is available (drop MC_FAST and the flags).
module-c-lowo:
	MC_FAST=1 MLFLOW_TRACKING_URI=$(or $(MLFLOW_TRACKING_URI),file:./mlruns) \
	poetry run python -m module_c_forecasting_scenarios.pipeline.run_lowo \
		--raw-csv module_c_forecasting_scenarios/tests/fixtures/polls_raw_fixture.csv \
		--out-dir data/processed/module_c/lowo \
		--summary-json reports/module_c_lowo_metrics.json \
		--chains 4 --draws 300 --tune 300

module-c-ppc:
	MLFLOW_TRACKING_URI=$(or $(MLFLOW_TRACKING_URI),file:./mlruns) \
	poetry run python -m module_c_forecasting_scenarios.pipeline.run_ppc \
		--raw-csv module_c_forecasting_scenarios/tests/fixtures/polls_raw_fixture.csv \
		--out-dir data/processed/module_c/ppc

coverage:
	poetry run pytest $(MODULE_TEST_ARGS) $(COV_FLAGS)

ci: lint typecheck coverage

all: install ci

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov coverage.xml .coverage

generate-dev:
	poetry run python -m population_segmentation.data.generator --config module_a_population_segmentation/config/generation.yaml

# Dev default SAMPLE=10000 keeps ``make pipeline-dev`` minutes, not hours (override: ``make pipeline-dev SAMPLE=50000``).
pipeline-dev:
	poetry run python -m population_segmentation.pipeline \
		--config module_a_population_segmentation/config/generation.yaml \
		--anchors module_a_population_segmentation/config/calibration_anchors.yaml \
		--out-dir data/processed \
		--sample-size $(or $(SAMPLE),10000)

dashboard:
	poetry run streamlit run module_a_population_segmentation/app/streamlit_dashboard.py

graphify:
	poetry run python -m graphify update .

module-a-export:
	MLFLOW_TRACKING_URI=$(or $(MLFLOW_TRACKING_URI),file:./mlruns) \
	poetry run python -m population_segmentation.pipeline.export \
		--config module_a_population_segmentation/config/generation.yaml \
		--anchors module_a_population_segmentation/config/calibration_anchors.yaml \
		--out-dir data/processed \
		--sample-size $(or $(SAMPLE),50000)

module-a-pipeline:
	MLFLOW_TRACKING_URI=$(or $(MLFLOW_TRACKING_URI),file:./mlruns) \
	poetry run python -m population_segmentation.pipeline \
		--config module_a_population_segmentation/config/generation.yaml \
		--anchors module_a_population_segmentation/config/calibration_anchors.yaml \
		--out-dir data/processed \
		--sample-size $(or $(SAMPLE),50000)

module-a-report-charts:
	poetry run python scripts/generate_module_a_report_charts.py

module-b-allocate:
	poetry run python -m module_b_resource_allocation.pipeline.run_allocation \
		--scenario $(or $(SCENARIO),baseline) \
		--out-dir data/processed/module_b \
		--seed $(or $(SEED),20180422) \
		--counterfactual

# Full A→B→C pipeline + EDA regeneration, on the canonical dev scale.
# Order matters: B ingests A's reachability export; C ingests B's allocation.
pipeline-full:
	$(MAKE) module-a-pipeline SAMPLE=$(or $(SAMPLE),50000)
	$(MAKE) module-b-allocate
	$(MAKE) module-b-routing-schedules
	$(MAKE) module-c-all
	$(MAKE) module-a-report-charts
	poetry run python reports/eda/generate_eda.py
	poetry run python scripts/generate_golden_metrics.py
	poetry run python scripts/generate_figure_manifest.py

module-b-allocate-sensitivity:
	poetry run python -m module_b_resource_allocation.pipeline.run_allocation \
		--scenario $(or $(SCENARIO),baseline) \
		--out-dir data/processed/module_b \
		--seed $(or $(SEED),20180422) \
		--sensitivity

module-b-routing:
	poetry run python -c "from pathlib import Path; from module_b_resource_allocation.routing.cost_matrix import build_cost_matrix; rs='$(or $(ROUTING_SCENARIO),dry_standard)'; seed=$(or $(SEED),20180422); p=Path('data/processed/module_b'); p.mkdir(parents=True, exist_ok=True); build_cost_matrix(scenario=rs, seed=seed).to_csv(p / f'routing_cost_matrix_{rs}.csv', index=False); print('wrote', p / f'routing_cost_matrix_{rs}.csv')"

module-b-routing-schedules:
	poetry run python -c "from pathlib import Path; from module_b_resource_allocation.routing.tsp_router import write_routing_schedules; out=write_routing_schedules(Path('data/processed/module_b'), seed=$(or $(SEED),20180422)); print('wrote', out)"

module-b-api:
	poetry run uvicorn module_b_resource_allocation.api.app:app --host 127.0.0.1 --port 8088
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Cloud Run Deployment (T4)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

.PHONY: setup-artifact-registry deploy-module-a deploy-module-b smoke-test rollback-module-a rollback-module-b

setup-artifact-registry:
	@if [ -z "$(GCP_PROJECT)" ]; then \
		echo "❌ GCP_PROJECT required. Usage: make setup-artifact-registry GCP_PROJECT=<project-id>"; \
		exit 1; \
	fi
	@chmod +x scripts/setup_artifact_registry.sh
	@./scripts/setup_artifact_registry.sh "$(GCP_PROJECT)" "$(or $(REGION),europe-west3)"

deploy-module-a:
	@if [ -z "$(GCP_PROJECT)" ]; then \
		echo "❌ GCP_PROJECT required. Usage: make deploy-module-a GCP_PROJECT=<project-id>"; \
		exit 1; \
	fi
	@chmod +x scripts/deploy_module_a_cloudrun.sh
	@./scripts/deploy_module_a_cloudrun.sh "$(GCP_PROJECT)" "$(or $(REGION),europe-west3)" "$(or $(IMAGE_TAG),latest)"

deploy-module-b:
	@if [ -z "$(GCP_PROJECT)" ]; then \
		echo "❌ GCP_PROJECT required. Usage: make deploy-module-b GCP_PROJECT=<project-id>"; \
		exit 1; \
	fi
	@chmod +x scripts/deploy_module_b_cloudrun.sh
	@./scripts/deploy_module_b_cloudrun.sh "$(GCP_PROJECT)" "$(or $(REGION),europe-west3)" "$(or $(IMAGE_TAG),latest)"

smoke-test:
	@if [ -z "$(MODULE_A_URL)" ] || [ -z "$(MODULE_B_URL)" ]; then \
		echo "❌ MODULE_A_URL and MODULE_B_URL required."; \
		echo "Usage: make smoke-test MODULE_A_URL=<url> MODULE_B_URL=<url>"; \
		exit 1; \
	fi
	@chmod +x scripts/smoke_test_cloudrun.sh
	@./scripts/smoke_test_cloudrun.sh "$(MODULE_A_URL)" "$(MODULE_B_URL)"

rollback-module-a:
	@if [ -z "$(GCP_PROJECT)" ]; then \
		echo "❌ GCP_PROJECT required. Usage: make rollback-module-a GCP_PROJECT=<project-id>"; \
		exit 1; \
	fi
	@chmod +x scripts/rollback_cloudrun.sh
	@./scripts/rollback_cloudrun.sh "$(GCP_PROJECT)" "module-a-streamlit" "$(or $(REGION),europe-west3)"

rollback-module-b:
	@if [ -z "$(GCP_PROJECT)" ]; then \
		echo "❌ GCP_PROJECT required. Usage: make rollback-module-b GCP_PROJECT=<project-id>"; \
		exit 1; \
	fi
	@chmod +x scripts/rollback_cloudrun.sh
	@./scripts/rollback_cloudrun.sh "$(GCP_PROJECT)" "module-b-fastapi" "$(or $(REGION),europe-west3)"

# ── Governance — see governance/AUDIT_PROCEDURE.md ───────────────────────────
#
# Append (or merge) the targets below into your project's Makefile.
# Only the governance-specific targets are defined here; your project's
# build/test/lint targets stay separate.

.PHONY: audit verify session-start session-end debt-scan debt-check

audit:
	@echo "── make audit ─────────────────────────────────────────────"
	@poetry run python scripts/check_claude_md.py
	@poetry run python scripts/check_charter_size.py
	@poetry run python scripts/check_finding_coverage.py
	@poetry run python scripts/write_audit_state.py
	@echo "✓ audit complete — see governance/AUDIT_STATE.json"

# verify = audit + tests + closed-finding re-verification + debt ratchet
verify: audit
	@echo "── make verify ────────────────────────────────────────────"
	@$(MAKE) doc-registry-verify
	@poetry run python scripts/check_terminology.py
	@poetry run python scripts/check_eda_segment_claims.py
	@poetry run python scripts/check_palette_cvd_contrast.py
	@poetry run python scripts/check_no_local_color_literals.py
	@poetry run python scripts/check_allocation_parameter_provenance.py
	@if ls tests/governance/test_*.py >/dev/null 2>&1; then \
		poetry run pytest tests/governance/ -q; \
	else \
		echo "(no governance tests yet — skipping pytest)"; \
	fi
	@poetry run python scripts/check_closed_findings.py
	@poetry run python scripts/check_debt_ratchet.py
	@echo "✓ verify complete"

# Rewrite governance/DEBT_BASELINE.json from a fresh scan. Run this after you
# have *reduced* debt, to lock the gain so the ratchet can't slide back.
# Committing a baseline that moves UP requires a dedicated PR that says why.
debt-scan:
	@poetry run python scripts/debt_scan.py

# Ratchet gate: re-scan and fail if any measured debt metric grew past the
# baseline. This is the "remediate before it grows" enforcement. Runs in
# `verify` and in CI; cheap enough to run locally before pushing.
debt-check:
	@poetry run python scripts/check_debt_ratchet.py

session-start: audit
	@poetry run python scripts/session_start.py
	@echo ""
	@echo "→ Read governance/SESSION_HANDOUT.md before choosing work."

session-end:
	@poetry run python scripts/write_audit_state.py
	@poetry run python scripts/session_end.py
	@echo ""
	@echo "→ Edit free-text fields in governance/SESSION_END.md, then commit."

