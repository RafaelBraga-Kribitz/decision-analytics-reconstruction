---
doc_id: DOC-EVID-014
doc_type: evidence
doc_role: evidence
visibility: internal
status: archived
owner: harness
last_reviewed: '2026-05-20'
canonical_source: null
derived_from: null
supersedes: null
tags: []
---

# Task verify — Data Science Framing (Project_Action_list §2)

**Session:** 2026-05-12 (Mac Pro workspace). Commands run from repo root after fixing export artifact key test for `model_run_manifest`.

| Gate | Command | Expected | Evidence |
|------|-----------|----------|----------|
| Lint / format / pyright / pytest | `make validate` | Exit 0 | `ruff` All checks passed; `black` 168 files unchanged; `pyright` 0 errors; `pytest` **475 passed**, 2 skipped, 5 deselected; wall ~201s |
| Terminology + doc paths + mlflow import | `make tier3-smoke` | Exit 0 | `Terminology check OK (sample patterns).`; `verify_doc_code_paths OK (39 markdown files, 22 path-like inline codes).`; `mlflow_ok 3.12.0` |
| Doc paths (standalone) | `make doc-path-verify` | Exit 0 | Same `verify_doc_code_paths OK` as above when run alone |
| Terminology (standalone) | `poetry run python scripts/check_terminology.py` | Exit 0 | `Terminology check OK (sample patterns).` |
| Graph refresh after `src/` edits | `poetry run python -m graphify update .` | Completes | `Rebuilt: 2492 nodes, 3054 edges, 278 communities`; `GRAPH_REPORT.md updated in graphify-out` |
| New / touched Module A tests | Bundled in `make validate` | Pass | Includes `test_pipeline_cli.py`, `test_model_run_manifest.py`, `test_export_artifacts.py::test_all_export_artifact_keys_exist`, manifest payload test |

**QA (medium-risk sidecar):** `model_run_manifest.json` is additive metadata beside validated parquet/CSV exports; downstream consumers that ignore unknown keys remain safe. Optional formal qa-gatekeeper artifact not attached; closure uses harness proof table only.

## Deliverables

| Item | Path |
|------|------|
| Pipeline module CLI | `module_a_population_segmentation/src/population_segmentation/pipeline/__main__.py` |
| Manifest helper | `module_a_population_segmentation/src/population_segmentation/pipeline/model_run_manifest.py` |
| Manifest emission | `run_export` → `data/processed/.../model_run_manifest.json` (when using export) |
| Model hierarchy | `reports/model_hierarchy.md` |
| Model I/O spec | `reports/module_a_model_io_spec.md` |
| Feature justification | `reports/feature_engineering_justification.md` |
| Walkthrough notebook | `module_a_population_segmentation/notebooks/01_end_to_end_walkthrough.ipynb` |
| Makefile target | `make module-a-pipeline` |
| README | Setup section + DS framing links |
