# Task verify — evaluation gap remediation (2026-05-12)

Session evidence for the evaluation-gap plan (CI Poetry install, rural WhatsApp anchor, doc path guard, MLflow opt-in documentation, decision log errata).

| ID | Criterion | Command | Result |
|----|-----------|---------|--------|
| EG1 | First-party imports after editable install | `poetry install -q && poetry run python -c "import population_segmentation; import module_b_resource_allocation; import module_c_forecasting_scenarios; print('imports_ok')"` | PASS (exit 0) |
| EG2 | Generator WhatsApp vs YAML | `poetry run pytest module_a_population_segmentation/tests/test_generator.py::TestWhatsAppPenetrationFromConfig -q --tb=short` | PASS |
| EG3 | Full non-slow suite | `make test` | PASS (466 passed, 1 skipped, 5 deselected; ~205 s) |
| EG4 | Lint/format | `make lint` | PASS |
| EG5 | Typecheck (Modules A+B `src`) | `make typecheck` | PASS (0 errors) |
| EG6 | Doc markdown path sanity | `poetry run python scripts/verify_doc_code_paths.py` | PASS (`verify_doc_code_paths OK`) |
| EG7 | Pre-commit | `poetry run pre-commit run --all-files` | **WAIVED** — hook runs `ruff --fix --exit-non-zero-on-fix` and exits 1 after auto-fixing files outside this change set; `make lint` (ruff check without fix) is PASS |
| EG8 | Terminology sample | `poetry run python scripts/check_terminology.py` | PASS |
| EG9 | QA gatekeeper | [`reports/qa_gatekeeper_verdict_evaluation_gap_2026-05-12.md`](qa_gatekeeper_verdict_evaluation_gap_2026-05-12.md) | PASS WITH CAVEATS |

**Aggregate gate**

| Command | Result |
|---------|--------|
| `make validate` (lint + typecheck + test + `doc-path-verify`) | PASS (exit 0; pytest 466 passed, 1 skipped) |
