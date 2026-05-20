# Task verify — Architecture Quality (Project_Action_list §3, `data/` `.gitkeep`)

**Task ID:** TASK-20260512-ARCH-Q9-DATA-GITKEEP  
**Date:** 2026-05-12

## Success criteria evidence

| Criterion | Command | Result |
|-----------|---------|--------|
| Data layout tests | `poetry run pytest tests/test_architecture_data_directory_layout.py -v --tb=short` | `2 passed` |
| Terminology | `poetry run python scripts/check_terminology.py` | `Terminology check OK (sample patterns).` exit 0 |
| Doc inline paths | `make validate` → `poetry run python scripts/verify_doc_code_paths.py` | `verify_doc_code_paths OK (48 markdown files, 51 path-like inline codes).` |
| Lint / format / full pytest | `make validate` | Exit **0**; `496 passed, 2 skipped, 5 deselected` (module + root `tests/`, `-m "not slow"`, coverage XML) |
| Graphify | `poetry run python -m graphify update .` | Exit **0**; `252/252` AST files; `graphify-out` updated |
| Checklist | `Project_Action_list.md` §3 | Former line 46 struck; link to layout test |

## Deliverables

| Item | Path |
|------|------|
| Gitignore negation | [`.gitignore`](../.gitignore) |
| Placeholders | [`data/raw/.gitkeep`](../data/raw/.gitkeep), [`data/interim/.gitkeep`](../data/interim/.gitkeep), [`data/processed/.gitkeep`](../data/processed/.gitkeep) |
| Regression test | [`tests/test_architecture_data_directory_layout.py`](../tests/test_architecture_data_directory_layout.py) |
| Architecture note | [`ARCHITECTURE.md`](../ARCHITECTURE.md) |
| Action list | [`Project_Action_list.md`](../Project_Action_list.md) |
| Decision log | [`reports/decision_log.md`](../reports/decision_log.md) |
| Pre-public manifest | [`maintainer/pre_public_cleanup_manifest.md`](../maintainer/pre_public_cleanup_manifest.md) M27 |
