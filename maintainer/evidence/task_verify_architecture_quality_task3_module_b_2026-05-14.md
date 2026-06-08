# Task verify — Architecture Quality (Project_Action_list §3, Module B surface)

**Task ID:** TASK-20260514-ARCH-Q3-MODULE-B-SURFACE  
**Date:** 2026-05-14

## Success criteria evidence

| Criterion | Command | Result |
|-----------|---------|--------|
| New guard tests | `poetry run pytest tests/test_architecture_module_b_surface.py -v --tb=short` | `2 passed` |
| Lint / format / typecheck / full pytest | `make validate` | Exit **0**; `pytest` **480 passed**, 2 skipped, 5 deselected (~226s); `verify_doc_code_paths OK (41 markdown files, 31 path-like inline codes)` |
| Terminology | `poetry run python scripts/check_terminology.py` | `Terminology check OK (sample patterns).` exit 0 (same session as validate) |
| Doc inline paths | `make doc-path-verify` | Same gate as validate tail output above |
| Graphify | `poetry run python -m graphify update .` | Exit **0**; `Rebuilt: 2516 nodes, 3074 edges, 274 communities`; `GRAPH_REPORT.md updated in graphify-out` |
| Checklist | `Project_Action_list.md` §3 | Module B block reconciled and struck (`~~…~~`); Module C lines unchanged |

## Deliverables

| Item | Path |
|------|------|
| Surface regression test | [`tests/test_architecture_module_b_surface.py`](../tests/test_architecture_module_b_surface.py) |
| Action list | [`Project_Action_list.md`](../Project_Action_list.md) |
| Architecture cross-link | [`ARCHITECTURE.md`](../ARCHITECTURE.md) |
| Decision log | [`reports/decision_log.md`](decision_log.md) |
| Pre-public manifest | [`maintainer/pre_public_cleanup_manifest.md`](../maintainer/pre_public_cleanup_manifest.md) M21 |
