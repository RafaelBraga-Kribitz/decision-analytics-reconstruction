.PHONY: install lint format typecheck test coverage all clean module-a-export graphify

PYTHON := python3.11
MODULE_A_SRC := module_a_population_segmentation/src
MODULE_A_TESTS := module_a_population_segmentation/tests
MODULE_A_APP := module_a_population_segmentation/app

install:
	poetry install

format:
	black $(MODULE_A_SRC) $(MODULE_A_TESTS) $(MODULE_A_APP)

lint:
	ruff check $(MODULE_A_SRC) $(MODULE_A_TESTS) $(MODULE_A_APP)
	black --check $(MODULE_A_SRC) $(MODULE_A_TESTS) $(MODULE_A_APP)

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

graphify:
	poetry run graphify update .

module-a-export:
	poetry run python -m population_segmentation.pipeline.export \
		--config module_a_population_segmentation/config/generation.yaml \
		--anchors module_a_population_segmentation/config/calibration_anchors.yaml \
		--out-dir data/processed \
		--sample-size $(or $(SAMPLE),50000)