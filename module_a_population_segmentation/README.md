
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
| `population_master_clean.parquet` | 4.26M entities, 14-step cleaned | Module B, Module C |
| `segment_labels.parquet` | 6 behavioral segments (DBSCAN + K-Means) | Module B |
| `participation_propensity.parquet` | Calibrated propensity scores per entity | Module B, Module C |
| `media_reachability_by_segment.csv` | Channel reach proportions per segment | Module B |

---

## Reports and artifacts

| Document | Description |
|----------|-------------|
| [`reports/model_card_segmentation.md`](reports/model_card_segmentation.md) | Segmentation model: intended use, limits, metrics |
| [`reports/model_card_propensity.md`](reports/model_card_propensity.md) | Propensity model: methodology, calibration, acceptance criteria |
| [`reports/segment_action_matrix.md`](reports/segment_action_matrix.md) | Segment → channel / priority / policy bridge (stakeholder-facing) |
| [`reports/transformation_log.md`](../reports/transformation_log.md) | 14-step cleaning log with implementation status |
| [`reports/decision_log.md`](../reports/decision_log.md) | All non-trivial modeling decisions with alternatives considered |

For synthetic data independence assumptions and limitations, see [`reports/statistical_independence_note.md`](../reports/statistical_independence_note.md).

---

## Quality gates (implemented)

- **Pandera runtime schema contracts** (`evaluation/schema_validator.py`) — enforced at cleaner exit and feature frame exit; raises `SchemaError` on any column-level violation.
- **Custom QA gates** (`data/validator.py`) — 13 calibration anchor checks; `QAGateFailure` halts pipeline.
- A4/A5/A6/A11 via segmentation tests (silhouette > 0.22, bootstrap ARI ≥ 0.40 at the 50k production run / 0.50 test floor — canonical `compute_bootstrap_ari`, IMP-A03/#55; the earlier 0.77 gate was the retired two-subsample metric).
- A7/A8/A9/A10 via propensity tests (ablated AUC-ROC > 0.85 with `department_logit_offset` excluded — the unablated AUC ≈ 0.89 is circular, see model card §Limitations; Brier < 0.237; reliability deviation < 3 pp).
