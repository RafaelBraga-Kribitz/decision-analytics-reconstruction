
# Module A — Population Modeling and Segmentation

Flagship module of the decision analytics reconstruction project.


**QA markdown:** dated pipeline summaries are emitted as `reports/qa_report_*.md` (gitignored filenames). Do **not** mirror them into `data/processed/`; use the canonical `module_a_population_segmentation/reports/` location only.

---

## What decision this supports

- How to segment a large heterogeneous population into operationally distinct behavioral groups.
- How to estimate calibrated participation propensity for downstream resource allocation.
- How to enforce data quality contractually at each pipeline step exit.

---

## Quick run

```bash
poetry install
streamlit run module_a_population_segmentation/app/streamlit_dashboard.py
```

Optional container flow (see repo root `docker-compose.yml`): Colima + `docker compose up module_a` locally.

---

## Key outputs

| Artifact | Description | Consumer |
|----------|-------------|---------|
| `population_master_clean.parquet` | 50,000 voters (default run; 4.26M design scale), cleaned by the 10 steps in `data/cleaner.py:clean_population` | Module B, Module C |
| `segment_labels.parquet` | 6 behavioral segments (DBSCAN + K-Means) | Module B |
| `participation_propensity.parquet` | Calibrated propensity scores per voter | Module B, Module C |
| `media_reachability_by_segment.csv` | Channel reach proportions per segment | Module B |

---

## Reports and artifacts

| Document | Description |
|----------|-------------|
| [`reports/model_card_segmentation.md`](reports/model_card_segmentation.md) | Segmentation model: intended use, limits, metrics |
| [`reports/model_card_propensity.md`](reports/model_card_propensity.md) | Propensity model: methodology, calibration, acceptance criteria |
| [`../reports/module_a/k_sweep_2026-07-09.md`](../reports/module_a/k_sweep_2026-07-09.md) | Pre-registered k-selection sweep and the k = 6 taxonomy decision |
| [`config/model_params.yaml`](config/model_params.yaml) | Every runtime hyperparameter and acceptance gate (values recorded per run in `model_run_manifest.json`) |

For synthetic-data assumptions and limitations, see [`../reports/epistemic_boundaries.md`](../reports/epistemic_boundaries.md).

---

## Quality gates (implemented)

- **Pandera runtime schema contracts** (`evaluation/schema_validator.py`) — enforced at cleaner exit and feature frame exit; raises `SchemaError` on any column-level violation.
- **Custom QA gates** (`data/validator.py`) — 13 calibration anchor checks; `QAGateFailure` halts pipeline.
- A4/A5/A6/A11 via segmentation tests (silhouette > 0.22, bootstrap ARI ≥ 0.40 at the 50k production run / 0.50 test floor — canonical `compute_bootstrap_ari`, IMP-A03/#55; the earlier 0.77 gate was the retired two-subsample metric).
- A7/A8/A9/A10 via propensity tests (ablated AUC-ROC > 0.85 with `department_logit_offset` excluded — the unablated AUC ≈ 0.89 is circular, see model card §Limitations; Brier < 0.237; reliability deviation < 3 pp).
