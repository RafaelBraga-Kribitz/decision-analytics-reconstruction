.PHONY: install lint format typecheck test coverage all clean

PYTHON := python3.11
MODULE_A_SRC := module_a_population_segmentation/src
MODULE_A_TESTS := module_a_population_segmentation/tests

install:
	poetry install

format:
	black $(MODULE_A_SRC) $(MODULE_A_TESTS)

lint:
	ruff check $(MODULE_A_SRC) $(MODULE_A_TESTS)
	black --check $(MODULE_A_SRC) $(MODULE_A_TESTS)

typecheck:
	pyright $(MODULE_A_SRC)

test:
	pytest $(MODULE_A_TESTS) -v --tb=short

coverage:
	pytest $(MODULE_A_TESTS) --cov=$(MODULE_A_SRC) --cov-report=term-missing --cov-report=xml

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
	streamlit run module_a_population_segmentation/app/streamlit_dashboard.py