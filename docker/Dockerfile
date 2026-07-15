FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set INSTALL_DEV=1 at build time to include dev/test deps (for CI smoke)
ARG INSTALL_DEV=0
# Production images bake Module A export artifacts (data/processed/ is gitignored).
ARG MODULE_A_SAMPLE_SIZE=15000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends make gcc g++ git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry==2.4.0

COPY pyproject.toml poetry.lock* README.md .pre-commit-config.yaml /app/
COPY .streamlit /app/.streamlit
COPY Makefile /app/
COPY shared /app/shared
COPY module_a_population_segmentation /app/module_a_population_segmentation
COPY module_b_resource_allocation /app/module_b_resource_allocation
COPY module_c_forecasting_scenarios /app/module_c_forecasting_scenarios
COPY schema_contracts /app/schema_contracts
COPY reports /app/reports
COPY scripts /app/scripts
COPY tests /app/tests
COPY .git /app/.git

RUN poetry config virtualenvs.create false && \
    if [ "$INSTALL_DEV" = "1" ]; then \
        poetry install --extras all; \
    else \
        poetry install --only main --extras dashboard --extras explainability && \
        poetry run python -m population_segmentation.pipeline \
            --out-dir data/processed \
            --sample-size ${MODULE_A_SAMPLE_SIZE} && \
        rm -rf .git; \
    fi

EXPOSE 8501

# Render injects PORT (default 10000); local compose keeps 8501 when PORT is unset.
CMD ["sh", "-c", "streamlit run module_a_population_segmentation/app/streamlit_dashboard.py --server.port=${PORT:-8501} --server.address=0.0.0.0"]
