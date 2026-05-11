# Module A — Population Modeling and Segmentation

Flagship module of the decision analytics reconstruction project.

## What decision this supports
- How to segment a large population into operational groups.
- How to estimate calibrated participation propensity for downstream allocation.

## Quick run
```bash
poetry install
streamlit run module_a_population_segmentation/app/streamlit_dashboard.py
```

Optional container flow (see repo root [`docker-compose.yml`](../docker-compose.yml)): Colima plus `docker compose up module_a` locally; prefer Colima instead of Docker Desktop on legacy GPUs.

## Key outputs
- `population_master_clean.parquet`
- `segment_labels.parquet`
- `participation_propensity.parquet`
- `media_reachability_by_segment.csv`

## Quality gates (implemented)
- A1/A3 via cleaner + validator pipeline and QA report.
- A4/A5/A6/A11 via segmentation tests.
- A7/A8/A9/A10 via propensity tests.
