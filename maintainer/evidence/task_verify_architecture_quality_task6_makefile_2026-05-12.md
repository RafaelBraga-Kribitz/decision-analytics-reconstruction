---
doc_id: DOC-EVID-009
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

# Task verify — Architecture Quality (Project_Action_list §3, Makefile Poetry)

**Task ID:** TASK-20260512-ARCH-Q6-MAKEFILE-POETRY  
**Date:** 2026-05-12

## Success criteria evidence

| Criterion | Command | Result |
|-----------|---------|--------|
| Makefile policy tests | `poetry run pytest tests/test_architecture_makefile_poetry_policy.py -v --tb=short` | `3 passed` |
| Terminology | `poetry run python scripts/check_terminology.py` | `Terminology check OK (sample patterns).` exit 0 |
| Doc inline paths | `make doc-path-verify` (via `make validate`) | `verify_doc_code_paths OK (44 markdown files, 40 path-like inline codes).` |
| Lint / format / typecheck / full pytest | `make validate` | Exit **0**; `pytest` **488 passed**, 2 skipped, 5 deselected (~232s); doc-path tail matches above |
| Graphify | `poetry run python -m graphify update .` | Exit **0**; `Rebuilt: 2546 nodes, 3102 edges, 290 communities`; `GRAPH_REPORT.md updated in graphify-out` |
| Checklist | `Project_Action_list.md` §3 | Former line 43 reconciled and struck (`~~…~~`); link to regression test |

## Deliverables

| Item | Path |
|------|------|
| Makefile Poetry regression test | [`tests/test_architecture_makefile_poetry_policy.py`](../tests/test_architecture_makefile_poetry_policy.py) |
| Root Makefile | [`Makefile`](../Makefile) |
| Action list | [`Project_Action_list.md`](../Project_Action_list.md) |
| Architecture cross-link | [`ARCHITECTURE.md`](../ARCHITECTURE.md) |
| Decision log | [`reports/decision_log.md`](decision_log.md) |
| Pre-public manifest | [`maintainer/pre_public_cleanup_manifest.md`](../maintainer/pre_public_cleanup_manifest.md) M24 |
