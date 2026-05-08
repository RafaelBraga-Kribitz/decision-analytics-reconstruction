FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir poetry==2.4.0

COPY pyproject.toml poetry.lock* /app/
COPY module_a_population_segmentation /app/module_a_population_segmentation
COPY schema_contracts /app/schema_contracts
COPY reports /app/reports
COPY appendix /app/appendix

RUN poetry config virtualenvs.create false && poetry install --no-root --only main

EXPOSE 8501

CMD ["streamlit", "run", "module_a_population_segmentation/app/streamlit_dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]
