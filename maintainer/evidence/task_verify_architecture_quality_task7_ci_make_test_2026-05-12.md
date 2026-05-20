---
doc_id: DOC-EVID-010
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

# Task verify — Architecture Quality (Project_Action_list §3, `make test` + coverage + CI)

**Task ID:** TASK-20260512-ARCH-Q7-MAKE-TEST-COVERAGE-CI  
**Date:** 2026-05-12

## Success criteria evidence

| Criterion | Command | Result |
|-----------|---------|--------|
| Makefile contract tests | `poetry run pytest tests/test_architecture_makefile_test_coverage_contract.py -v --tb=short` | `2 passed` |
| Terminology | `poetry run python scripts/check_terminology.py` | `Terminology check OK (sample patterns).` exit 0 |
| Doc inline paths | `make doc-path-verify` (via `make validate`) | `verify_doc_code_paths OK (45 markdown files, 43 path-like inline codes).` |
| Lint / format / typecheck / full pytest | `make validate` | Exit **0**; pytest **490 passed**, 2 skipped, 5 deselected (~388s); coverage summary and `coverage.xml` written during `test` stage |
| Graphify | `poetry run python -m graphify update .` | Exit **0**; `Rebuilt: 2558 nodes, 3116 edges, 287 communities`; `GRAPH_REPORT.md updated in graphify-out` |
| Checklist | `Project_Action_list.md` §3 | Former line 44 struck (`~~…~~`); links to regression test and CI job name |
| GitHub Actions | Post-merge | Workflow [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) job **`repo-make-test`**: `poetry install` then `make test` with `MC_FAST=1`; confirm green on `main` / PR after push |

## Deliverables

| Item | Path |
|------|------|
| Makefile contract test | [`tests/test_architecture_makefile_test_coverage_contract.py`](../tests/test_architecture_makefile_test_coverage_contract.py) |
| Root Makefile (`MODULE_TEST_ARGS`, `COV_FLAGS`, `test`, `coverage`) | [`Makefile`](../Makefile) |
| CI job `repo-make-test` | [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) |
| Action list | [`Project_Action_list.md`](../Project_Action_list.md) |
| Architecture cross-link | [`ARCHITECTURE.md`](../ARCHITECTURE.md) |
| Decision log | [`reports/decision_log.md`](decision_log.md) |
| Pre-public manifest | [`maintainer/pre_public_cleanup_manifest.md`](../maintainer/pre_public_cleanup_manifest.md) M25 |
