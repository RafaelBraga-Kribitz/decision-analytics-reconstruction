# Task verify — Architecture Quality (Project_Action_list §3, Module C surface)

**Task ID:** TASK-20260514-ARCH-Q4-MODULE-C-SURFACE  
**Date:** 2026-05-14

## Success criteria evidence

| Criterion | Command | Result |
|-----------|---------|--------|
| New guard tests | `poetry run pytest tests/test_architecture_module_c_surface.py -v --tb=short` | `2 passed` |
| Lint / format / typecheck / full pytest | `make validate` | Exit **0**; `pytest` **482 passed**, 2 skipped, 5 deselected (~228s) |
| Terminology | `poetry run python scripts/check_terminology.py` | `Terminology check OK (sample patterns).` exit 0 (same session) |
| Doc inline paths | `make doc-path-verify` | `verify_doc_code_paths OK (42 markdown files, 34 path-like inline codes).` (tail of `make validate`) |
| Graphify | `poetry run python -m graphify update .` | Exit **0**; `Rebuilt: 2525 nodes, 3082 edges, 292 communities`; `GRAPH_REPORT.md updated in graphify-out` |
| Checklist | `Project_Action_list.md` §3 | Module C block reconciled and struck (`~~…~~`); “All inter-module…” line unchanged |

**Import strategy:** `pipeline.run_all` not imported in the guard test (pulls tracking stack / PyMC); surface uses `module_c_forecasting_scenarios.paths` and `data.contract_validate` only.

## Deliverables

| Item | Path |
|------|------|
| Surface regression test | [`tests/test_architecture_module_c_surface.py`](../tests/test_architecture_module_c_surface.py) |
| Action list | [`Project_Action_list.md`](../Project_Action_list.md) |
| Architecture cross-link | [`ARCHITECTURE.md`](../ARCHITECTURE.md) |
| Decision log | [`reports/decision_log.md`](decision_log.md) |
| Pre-public manifest | [`maintainer/pre_public_cleanup_manifest.md`](../maintainer/pre_public_cleanup_manifest.md) M22 |
