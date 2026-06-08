# Task verify — Architecture Quality (Project_Action_list §3, first bullet)

**Task ID:** TASK-20260512-ARCH-Q1-MODULE-ROOTS  
**Date:** 2026-05-12

## Success criteria evidence

| Criterion | Command | Result |
|-----------|---------|--------|
| New invariant test | `poetry run pytest tests/test_architecture_three_module_layout.py -v --tb=short` | `1 passed` |
| Lint / format / typecheck / pytest suite | `make validate` | Exit **0**; `ruff` all checks passed; `black` 169 files unchanged; `pyright` 0 errors; `pytest` **476 passed**, 2 skipped, 5 deselected (~248s); `verify_doc_code_paths OK` |
| Terminology | `poetry run python scripts/check_terminology.py` | `Terminology check OK (sample patterns).` exit 0 |
| Doc inline paths | `make doc-path-verify` | `verify_doc_code_paths OK (39 markdown files, 23 path-like inline codes).` exit 0 |
| Checklist | `Project_Action_list.md` §3 | First bullet reconciled to canonical directory names and fully struck with `~~`; subsequent §3 bullets unchanged |

## Deliverables

| Item | Path |
|------|------|
| Layout regression test | [`tests/test_architecture_three_module_layout.py`](../tests/test_architecture_three_module_layout.py) |
| Action list reconciliation | [`Project_Action_list.md`](../Project_Action_list.md) |
| Canonical roots note | [`ARCHITECTURE.md`](../ARCHITECTURE.md) |
| Pre-public manifest row | [`maintainer/pre_public_cleanup_manifest.md`](../maintainer/pre_public_cleanup_manifest.md) M19 |

No `module_*/*/src/**/*.py` changes in this task; **`graphify update .` not required** ([graphify rule](.cursor/rules/graphify.mdc)).
