# Session End — 2026-06-11

## Findings touched

- F-021: open -> closed (`scripts/check_live_deployment_urls.py` — all three deploy URLs 200)
- F-023, F-032: regression fixes after doc consolidation (anchor paths, public md count = 20)

## Sprint status

Truth and Rebuild Sprint plan todos marked complete. `make verify` passes (17 closed findings). Only **F-008** (radon complexity) remains open.

## Recommended next action

- F-008 time-boxed refactor of worst demo-path blocks, or deliberate wont-fix with baseline waiver discussion.

---

# Session End — 2026-06-08

## Findings touched

- F-001: opened -> closed (`scripts/check_charter_size.py`)
- F-002: opened -> closed (`scripts/check_claude_md.py`)
- F-003: opened -> closed_historical
- F-004: opened -> closed_historical
- F-005: opened -> open
- F-006: opened -> open
- F-007: opened -> open
- F-008: opened -> open
- F-009: opened -> open

## ADRs added

- `governance/adrs/0002-tech-debt-ratchet.md` — adopted the debt ratchet from the bootstrap kit.

## Invariants installed

- `scripts/check_charter_size.py`
- `scripts/check_claude_md.py`
- `scripts/check_finding_coverage.py`
- `scripts/check_closed_findings.py`
- `scripts/check_debt_ratchet.py`
- `scripts/check_precommit_pyright_all_modules.py`
- `scripts/check_pytest_conftest_collection.py`
- `scripts/check_ruff_unused_zero.py`
- `scripts/check_radon_complexity_zero.py`
- `scripts/check_vulture_dead_code_zero.py`

## Open questions for next session

- Whether `F-005` should be resolved by adding Module C to the pre-commit Pyright hook or by documenting a deliberate local-hook exception.
- Whether `F-006` should be resolved by package/layout changes in test discovery or by adjusting the default pytest target.

## Recommended next-finding priority

- Pick up `F-006` first. It captures the inherited `make test` collection failure and blocks treating the full suite as a reliable regression signal.

## Notes

- `make session-start`, `make verify`, and `make debt-check` exited 0 after the governance replacement.
- Baseline debt metrics: `ruff_unused=9`, `radon_complex_blocks=38`, `vulture_dead_code=3`.
- Historical root planning docs now live under `maintainer/archive/`; active governance lives under `governance/`.
