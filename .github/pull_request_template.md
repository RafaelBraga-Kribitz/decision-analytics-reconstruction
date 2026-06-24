## Summary

<!-- 1-3 bullet points: what changed and why -->
-

## Finding / Issue

<!-- If closing a governance finding, include the finding ID: "Closes F-NNN" -->
<!-- If closing a GitHub issue: "Closes #NNN" -->
Closes:

## Module scope

<!-- Which modules are affected by this PR? -->
- [ ] Module A — Population Segmentation
- [ ] Module B — Resource Allocation
- [ ] Module C — Forecasting & Scenarios
- [ ] Shared / Infrastructure
- [ ] Governance / CI

## Verification

<!-- Check all that apply; mark N/A where not relevant -->
- [ ] `poetry run pytest` — all tests pass
- [ ] `poetry run ruff check .` — 0 errors
- [ ] `poetry run black --check .` — 0 reformats
- [ ] `make verify` — adversary exits 0 (no closed finding regressions)
- [ ] Verification script passes: `python scripts/check_<finding>.py` → `[PASS]`
- [ ] Parameter values unchanged (or `[PARAM]` tag in PR title if changed)

## Test plan

<!-- Enumerate what was tested and how -->
- [ ]

## [PARAM] notice

<!-- If any parameter VALUE changed (not just wiring), add [PARAM] to the PR title and describe here -->
<!-- "No parameter values changed; wiring/structure only." -->
