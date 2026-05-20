---
doc_id: DOC-EVID-013
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

# Task verify — Business Framing (§1 Project_Action_list)

Evidence for completion of Section **1. Business Framing** only.

| Gate | Command | Expected | Actual | Result |
|------|---------|-----------|--------|--------|
| Unit + lint + types + docs | `make validate` | exit 0 | `470 passed`; `verify_doc_code_paths OK` tail of validate | PASS |
| Terminology sampler | `poetry run python scripts/check_terminology.py` | exit 0 | `Terminology check OK (sample patterns).` | PASS |
| Allocation manifest contains `baseline_comparison` | `data/processed/module_b/run_manifest_baseline.json` | `baseline_comparison` object | Present after `make module-b-allocate-sensitivity SEED=20180422` | PASS |
| Baseline regeneration | `make module-b-allocate SEED=20180422` | OPTIMAL manifest | `solver_status=OPTIMAL` logged | PASS |
| Sensitive curve (risk table cites) | `make module-b-allocate-sensitivity SEED=20180422` | CSV + markdown | `budget_expansion_curve_baseline.csv`, `allocation_run_baseline.md` | PASS |
| Docs path integrity | `make doc-path-verify` | exit 0 | `verify_doc_code_paths OK` | PASS |
| Graph refresh post–Module B edits | `graphify update .` | exits 0 | `Code graph updated` | PASS |

## Command log (verbatim excerpt)

```
poetry run pytest module_b_resource_allocation/tests/test_baselines.py -v --tb=short
# 5 passed

make validate
# … ruff/black/pyright/pytest/doc-path-verify OK (pytest: 470 passed, 2026-05-12 run)

make tier3-smoke
# (initial run failed: decision_log literals triggered terminology regex — fixed wording)

poetry run python scripts/check_terminology.py
# Terminology check OK (sample patterns).

poetry run python -m graphify update .
# Code graph updated … GRAPH_REPORT.md updated
```

## Deliverables checklist

| Item | Path |
|------|------|
| Business case | `reports/business_case.md` |
| README executive opener | top of `README.md` ("Executive overview") |
| Stakeholder table | `reports/stakeholder_scenario_table.md` |
| Comparator implementation | `module_b_resource_allocation/reporting/baselines.py` + manifest wiring (`run_allocation.py`) |
| Portfolio markdown on sensitivity runs | `module_b_resource_allocation/reporting/run_markdown.py` |
| Decision logged | `reports/decision_log.md` §2026-05-12 — Module B CFO baseline comparator |
