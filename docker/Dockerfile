FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set INSTALL_DEV=1 at build time to include dev/test deps (for CI smoke)
ARG INSTALL_DEV=0

WORKDIR /app

RUN pip install --no-cache-dir poetry==2.4.0

COPY pyproject.toml poetry.lock* README.md /app/
COPY Makefile /app/
COPY module_a_population_segmentation /app/module_a_population_segmentation
COPY module_b_resource_allocation /app/module_b_resource_allocation
COPY module_c_forecasting_scenarios /app/module_c_forecasting_scenarios
COPY schema_contracts /app/schema_contracts
COPY reports /app/reports
COPY appendix /app/appendix
COPY scripts /app/scripts
COPY tests /app/tests

RUN poetry config virtualenvs.create false && \
    if [ "$INSTALL_DEV" = "1" ]; then \
        poetry install; \
    else \
        poetry install --only main; \
    fi

EXPOSE 8501

CMD ["streamlit", "run", "module_a_population_segmentation/app/streamlit_dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]
