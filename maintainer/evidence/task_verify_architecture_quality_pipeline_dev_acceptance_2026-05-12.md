# Task verify — Architecture Quality (Project_Action_list §3, `make pipeline-dev` acceptance)

**Task ID:** TASK-20260512-ARCH-Q-PIPELINE-DEV  
**Date:** 2026-05-12

## Success criteria evidence

| Makefile contract | `poetry run pytest tests/test_architecture_pipeline_dev_contract.py -v --tb=short -m "not slow"` | `2 passed`, 1 deselected |
| Slow smoke | `poetry run pytest tests/test_architecture_pipeline_dev_contract.py::test_make_pipeline_dev_writes_contract_artifacts -v --tb=short` | `1 passed` (~8s with `SAMPLE=3000`) |
| Full gate | `make validate` | Exit 0; `504 passed, 2 skipped, 6 deselected`; `verify_doc_code_paths OK` |
| Terminology | `poetry run python scripts/check_terminology.py` (before validate) | `Terminology check OK (sample patterns).` |

## Deliverables

| Item | Path |
|------|------|
| Makefile `pipeline-dev` | [`Makefile`](../Makefile) |
| Module A entry | [`module_a_population_segmentation/src/population_segmentation/pipeline/__main__.py`](../module_a_population_segmentation/src/population_segmentation/pipeline/__main__.py) |
| Export implementation | [`module_a_population_segmentation/src/population_segmentation/pipeline/export.py`](../module_a_population_segmentation/src/population_segmentation/pipeline/export.py) |
| Regression tests | [`tests/test_architecture_pipeline_dev_contract.py`](../tests/test_architecture_pipeline_dev_contract.py) |
| Architecture note | [`ARCHITECTURE.md`](../ARCHITECTURE.md) |
| Action list | [`Project_Action_list.md`](../Project_Action_list.md) |
| Decision log | [`reports/decision_log.md`](../reports/decision_log.md) |
| Pre-public manifest | [`maintainer/pre_public_cleanup_manifest.md`](../maintainer/pre_public_cleanup_manifest.md) M29 |
