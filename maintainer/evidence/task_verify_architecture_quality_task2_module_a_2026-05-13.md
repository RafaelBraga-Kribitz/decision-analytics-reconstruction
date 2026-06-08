# Task verify — Architecture Quality (Project_Action_list §3, Module A surface)

**Task ID:** TASK-20260513-ARCH-Q2-MODULE-A-SURFACE  
**Date:** 2026-05-13

## Success criteria evidence

| Criterion | Command | Result |
|-----------|---------|--------|
| New guard tests | `poetry run pytest tests/test_architecture_module_a_surface.py -v --tb=short` | `2 passed` |
| Lint / format / typecheck / full pytest | `make validate` | Exit **0**; `pytest` **478 passed**, 2 skipped, 5 deselected (~209s); `verify_doc_code_paths OK (40 markdown files, 27 path-like inline codes)` |
| Terminology | `poetry run python scripts/check_terminology.py` | `Terminology check OK (sample patterns).` exit 0 |
| Doc inline paths | `make doc-path-verify` | Bundled in `make validate`; OK |
| Checklist | `Project_Action_list.md` §3 | Module A bullet block reconciled and struck (`~~…~~`); Module B bullet at line 48+ unchanged |
| Graphify | `poetry run python -m graphify update .` | Exit **0**; `Rebuilt: 2511 nodes, 3070 edges, 277 communities`; `GRAPH_REPORT.md updated in graphify-out` (follow-up 2026-05-13: graphify always on session close) |

## Secondary “runnable” evidence (existing tests)

Pipeline CLI/help is covered by `module_a_population_segmentation/tests/test_pipeline_cli.py` (`test_pipeline_module_help_exits_zero`, etc.), cited from the reconciled Action List line.

## Deliverables

| Item | Path |
|------|------|
| Surface regression test | [`tests/test_architecture_module_a_surface.py`](../tests/test_architecture_module_a_surface.py) |
| Action list | [`Project_Action_list.md`](../Project_Action_list.md) |
| Architecture cross-link | [`ARCHITECTURE.md`](../ARCHITECTURE.md) |
| Decision log | [`reports/decision_log.md`](decision_log.md) |
| Pre-public manifest | [`maintainer/pre_public_cleanup_manifest.md`](../maintainer/pre_public_cleanup_manifest.md) M20 |
