.PHONY: install lint format typecheck test coverage all clean module-a-export graphify \
	module-b-allocate module-b-routing module-b-api test-module-a test-module-b test-module-c \
	module-c-tracking module-c-exit module-c-mc module-c-all

PYTHON := python3.11
MODULE_A_SRC := module_a_population_segmentation/src
MODULE_A_TESTS := module_a_population_segmentation/tests
MODULE_A_APP := module_a_population_segmentation/app
MODULE_B_SRC := module_b_resource_allocation/src
MODULE_B_TESTS := module_b_resource_allocation/tests
MODULE_C_SRC := module_c_forecasting_scenarios/src
MODULE_C_TESTS := module_c_forecasting_scenarios/tests

install:
	poetry install

format:
	poetry run black $(MODULE_A_SRC) $(MODULE_A_TESTS) $(MODULE_A_APP) $(MODULE_B_SRC) $(MODULE_B_TESTS) $(MODULE_C_SRC) $(MODULE_C_TESTS)

lint:
	ruff check $(MODULE_A_SRC) $(MODULE_A_TESTS) $(MODULE_A_APP) $(MODULE_B_SRC) $(MODULE_B_TESTS) $(MODULE_C_SRC) $(MODULE_C_TESTS)
	poetry run black --check $(MODULE_A_SRC) $(MODULE_A_TESTS) $(MODULE_A_APP) $(MODULE_B_SRC) $(MODULE_B_TESTS) $(MODULE_C_SRC) $(MODULE_C_TESTS)

typecheck:
	poetry run pyright $(MODULE_A_SRC) $(MODULE_B_SRC) $(MODULE_C_SRC)

test:
	poetry run pytest $(MODULE_A_TESTS) $(MODULE_B_TESTS) $(MODULE_C_TESTS) -v --tb=short -m "not slow"

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
	poetry run pytest $(MODULE_A_TESTS) $(MODULE_B_TESTS) $(MODULE_C_TESTS) \
		--cov=$(MODULE_A_SRC) --cov=$(MODULE_B_SRC) --cov=$(MODULE_C_SRC) \
		--cov-report=term-missing --cov-report=xml

ci: lint typecheck coverage

all: install ci

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov coverage.xml .coverage

generate-dev:
	$(PYTHON) -m population_segmentation.data.generator --config module_a_population_segmentation/config/generation.yaml

pipeline-dev:
	$(PYTHON) -m population_segmentation.data.generator \
		--config module_a_population_segmentation/config/generation.yaml \
		--output data/interim/population_master_raw.parquet
	$(PYTHON) -m population_segmentation.data.cleaner \
		--input data/interim/population_master_raw.parquet \
		--output data/processed/population_master_clean.parquet \
		--config module_a_population_segmentation/config/generation.yaml

dashboard:
	poetry run streamlit run module_a_population_segmentation/app/streamlit_dashboard.py

graphify:
	poetry run graphify update .

module-a-export:
	poetry run python -m population_segmentation.pipeline.export \
		--config module_a_population_segmentation/config/generation.yaml \
		--anchors module_a_population_segmentation/config/calibration_anchors.yaml \
		--out-dir data/processed \
		--sample-size $(or $(SAMPLE),50000)

module-b-allocate:
	poetry run python -m module_b_resource_allocation.pipeline.run_allocation \
		--scenario $(or $(SCENARIO),baseline) \
		--out-dir data/processed/module_b \
		--seed $(or $(SEED),20180422)

module-b-routing:
	poetry run python -m module_b_resource_allocation.routing.heuristic \
		--scenario $(or $(SCENARIO),dry_standard) \
		--out-dir data/processed/module_b \
		--seed $(or $(SEED),20180422)

module-b-api:
	poetry run uvicorn module_b_resource_allocation.api.app:app --host 127.0.0.1 --port 8088