.PHONY: install lint format typecheck test coverage all clean module-a-export module-a-pipeline graphify \
	module-b-allocate module-b-allocate-sensitivity module-b-routing module-b-api \
	test-module-a test-module-b test-module-c \
	module-c-tracking module-c-exit module-c-mc module-c-all \
	precommit validate doc-path-verify portfolio-verify tier3-smoke e2e-smoke

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
COV_FLAGS := --cov=$(MODULE_A_SRC) --cov=$(MODULE_B_SRC) --cov=$(MODULE_C_SRC) --cov-report=term-missing --cov-report=xml

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
	poetry run pre-commit install
	poetry run pre-commit run --all-files

validate: lint typecheck test doc-path-verify

doc-path-verify:
	poetry run python scripts/verify_doc_code_paths.py

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
	poetry run python -m module_c_forecasting_scenarios.pipeline.run_tracking \
		--raw-csv module_c_forecasting_scenarios/tests/fixtures/polls_raw_fixture.csv \
		--out-dir data/processed/module_c/tracking

module-c-exit:
	poetry run python -m module_c_forecasting_scenarios.pipeline.run_exit \
		--raw-csv module_c_forecasting_scenarios/tests/fixtures/polls_raw_fixture.csv \
		--out-dir data/processed/module_c/exit

module-c-mc:
	poetry run python -m module_c_forecasting_scenarios.pipeline.run_monte_carlo \
		--raw-csv module_c_forecasting_scenarios/tests/fixtures/polls_raw_fixture.csv \
		--out-dir data/processed/module_c/mc

module-c-all:
	poetry run python -m module_c_forecasting_scenarios.pipeline.run_all \
		--raw-csv module_c_forecasting_scenarios/tests/fixtures/polls_raw_fixture.csv \
		--out-dir data/processed/module_c/run_all

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
	poetry run python -m population_segmentation.pipeline.export \
		--config module_a_population_segmentation/config/generation.yaml \
		--anchors module_a_population_segmentation/config/calibration_anchors.yaml \
		--out-dir data/processed \
		--sample-size $(or $(SAMPLE),50000)

module-a-pipeline:
	poetry run python -m population_segmentation.pipeline \
		--config module_a_population_segmentation/config/generation.yaml \
		--anchors module_a_population_segmentation/config/calibration_anchors.yaml \
		--out-dir data/processed \
		--sample-size $(or $(SAMPLE),50000)

module-b-allocate:
	poetry run python -m module_b_resource_allocation.pipeline.run_allocation \
		--scenario $(or $(SCENARIO),baseline) \
		--out-dir data/processed/module_b \
		--seed $(or $(SEED),20180422)

module-b-allocate-sensitivity:
	poetry run python -m module_b_resource_allocation.pipeline.run_allocation \
		--scenario $(or $(SCENARIO),baseline) \
		--out-dir data/processed/module_b \
		--seed $(or $(SEED),20180422) \
		--sensitivity

module-b-routing:
	poetry run python -c "from pathlib import Path; from module_b_resource_allocation.routing.cost_matrix import build_cost_matrix; rs='$(or $(ROUTING_SCENARIO),dry_standard)'; seed=$(or $(SEED),20180422); p=Path('data/processed/module_b'); p.mkdir(parents=True, exist_ok=True); build_cost_matrix(scenario=rs, seed=seed).to_csv(p / f'routing_cost_matrix_{rs}.csv', index=False); print('wrote', p / f'routing_cost_matrix_{rs}.csv')"

module-b-api:
	poetry run uvicorn module_b_resource_allocation.api.app:app --host 127.0.0.1 --port 8088