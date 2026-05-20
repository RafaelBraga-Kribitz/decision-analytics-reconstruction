---
doc_id: DOC-EVID-011
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

# Task verify — Architecture Quality (Project_Action_list §3, `ARCHITECTURE.md` depth)

**Task ID:** TASK-20260512-ARCH-Q8-ARCHITECTURE-MD  
**Date:** 2026-05-12

## Success criteria evidence

| Criterion | Command | Result |
|-----------|---------|--------|
| ARCHITECTURE structure tests | `poetry run pytest tests/test_architecture_md_content_contract.py -v --tb=short` | `4 passed` |
| Terminology | `poetry run python scripts/check_terminology.py` | `Terminology check OK (sample patterns).` exit 0 |
| Doc inline paths | `make doc-path-verify` (via `make validate`) | `verify_doc_code_paths OK` |
| Lint / format / typecheck / full pytest | `make validate` | Exit **0**; pytest **494 passed**, 2 skipped, 5 deselected (~352s); `verify_doc_code_paths OK (47 markdown files, 48 path-like inline codes).` |
| Graphify | `poetry run python -m graphify update .` | Exit **0**; `Rebuilt: 2587 nodes, 3150 edges, 296 communities`; `GRAPH_REPORT.md updated in graphify-out` |
| Checklist | `Project_Action_list.md` §3 | Former line 45 struck (`~~…~~`); link to [`tests/test_architecture_md_content_contract.py`](../tests/test_architecture_md_content_contract.py) |

## Deliverables

| Item | Path |
|------|------|
| Architecture narrative | [`ARCHITECTURE.md`](../ARCHITECTURE.md) |
| Regression tests | [`tests/test_architecture_md_content_contract.py`](../tests/test_architecture_md_content_contract.py) |
| Action list | [`Project_Action_list.md`](../Project_Action_list.md) |
| Decision log | [`reports/decision_log.md`](decision_log.md) |
| Pre-public manifest | [`maintainer/pre_public_cleanup_manifest.md`](../maintainer/pre_public_cleanup_manifest.md) M26 |
