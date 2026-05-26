FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set INSTALL_DEV=1 at build time to include dev/test deps (for CI smoke)
ARG INSTALL_DEV=0

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends make git && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry==2.4.0

# Core config and tooling
COPY pyproject.toml poetry.lock* .pre-commit-config.yaml /app/
COPY Makefile /app/
COPY conftest.py /app/
COPY docker-compose.yml /app/

# Root-level markdown files (tracked in docs registry)
COPY README.md ARCHITECTURE.md CHANGELOG.md IMPLEMENTATION_PLAN.md /app/
COPY Project_Action_list.md ROADMAP.md TASK_REFERENCE.md /app/

# Module source, tests, and reports
COPY module_a_population_segmentation /app/module_a_population_segmentation
COPY module_b_resource_allocation /app/module_b_resource_allocation
COPY module_c_forecasting_scenarios /app/module_c_forecasting_scenarios

# Supporting files
COPY schema_contracts /app/schema_contracts
COPY reports /app/reports
COPY appendix /app/appendix
COPY scripts /app/scripts
COPY tests /app/tests

# Documentation governance and harness
COPY docs /app/docs
COPY maintainer /app/maintainer
COPY docker /app/docker
COPY notebooklm-sources-2026-05-14 /app/notebooklm-sources-2026-05-14

# Cursor/Claude harness files (needed by transaction and doc governance tests)
COPY .cursor /app/.cursor
COPY .claude /app/.claude

RUN poetry config virtualenvs.create false && \
    if [ "$INSTALL_DEV" = "1" ]; then \
        poetry install --all-extras; \
    else \
        poetry install --only main; \
    fi

# Initialize a minimal git repo so git ls-files works inside the container
# (needed by verify_doc_registry.py and similar governance scripts)
RUN if [ "$INSTALL_DEV" = "1" ]; then \
        git config --global user.email "ci@example.com" && \
        git config --global user.name "CI" && \
        git init && \
        git add -A && \
        git commit -m "ci" --allow-empty; \
    fi

EXPOSE 8501

CMD ["streamlit", "run", "module_a_population_segmentation/app/streamlit_dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]
