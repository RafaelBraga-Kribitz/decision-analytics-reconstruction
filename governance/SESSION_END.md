# Session End — 2026-06-13 (F-055 — AUD-C1 retrodiction label)

## Context

Remediator pass on the F-054 chart/inference backlog. Picked the top critical
unfiled row (AUD-C1) per the prior handout and AUDIT_PROCEDURE: one finding per
PR, criticals first. A "360° portfolio audit" prompt was reconciled to the
existing governance system rather than re-run from scratch (the banned
anti-pattern) — the audit it asks for already lives in ISSUE_TRIAGE_MASTER.yaml.

## Findings touched

- **F-055 (new, closed):** Module C C1 "Bayesian Forecast Timeline" was an
  in-sample tracking *retrodiction* of the past 2018 Series A election (known
  outcome; +3.70 pp verified anchor) mislabelled as a forecast, with the verified
  anchor never drawn. Fix (`reports/eda/generate_eda.py` chart_c1 + narrative):
  honest "Bayesian Tracking Retrodiction" title, verified outcome anchor drawn +
  labelled from a shared `TSJE_ANCHOR_PP` constant, on-chart not-a-forecast
  disclosure. Sibling `build_notebook.py` + committed `eda_report.md` /
  `paraguay_election_eda.ipynb` headings de-mislabelled to match. Verified by
  `scripts/check_module_c_forecast_retrodiction.py` (static; negative test
  confirms the pre-fix generator fails all five invariants).
- **F-054 (umbrella, still open):** severe-unfiled count 17 → 16; AUD-C1 promoted
  to `verified_closed (F-055)`. Stays open until the backlog clears.

## Invariants installed

- `scripts/check_module_c_forecast_retrodiction.py` (F-055).

## Verification status

- `make audit` green; F-055 and all static closed findings re-verify.
- F-050/F-051/F-052 require regenerated `data/processed/` (gitignored); the CI
  Adversary rebuilds artifacts before verifying, as for F-053. The canonical
  `C1_forecast_timeline.png` is rebuilt by `make pipeline-full` (F-050 lineage) —
  this PR fixes the generator, not the committed PNG bytes (same model as F-053).

## Recommended next action

- Continue the F-054 backlog, criticals first: **AUD-C2** (terminal posterior
  borrowed from the anchor — the row AUD-C1 blocked), then AUD-C5/C6/C9 and
  AUD-B3/B5/B7/B8.

---

# Session End — 2026-06-13

## Context

Adversarial false-confidence audit (20 ranked credibility risks) followed by
remediation. Root cause behind most risks: the Governance workflow had failed
on all 15 prior main-branch runs (`make: poetry: not found`), so the Adversary
job had **never executed** — closed findings drifted unverified while the
handout reported "queue empty".

## Findings touched

- F-001 (workflow): governance.yml now installs poetry + project deps; the
  Adversary and tech-debt jobs run for the first time.
- F-008: refactored 3 over-complexity blocks (check_figure_artifact_lineage
  main, chart_eda_overview, _repair_label_mapping) — radon back to 0.
- F-032: Module C proof table reclassified as operator evidence; ADRs excluded.
- F-036: unanchored-fit test now asserts a relative (platform-robust) property.
- F-046: eda_overview rebuilt empirical-only (model panels removed).
- F-050/051/052: Adversary regenerates Module A artifacts before verifying, so
  these are genuinely re-checked on a clean checkout; segmentation enforces the
  rural_committed urbanicity invariant on the canonical artifact.
- F-053 (new, closed): win-probability charts no longer zoom a noise band
  around 0.5 into a false ranking.
- F-054 (new, OPEN): umbrella tracker keeping the 17 reject/critical
  ISSUE_TRIAGE_MASTER rows visible in the queue until each is filed/resolved.
- F-021 (reopened, recurrence 1): Module A Render demo timed out; per the
  README's deployment note a down demo is a regression, so it is reopened.

## Governance honesty fixes

- Removed the false "a finding reopens itself" automation claim (CLAUDE.md,
  AUDIT_PROCEDURE.md); documented manual reopen + read-only Adversary.
- Created governance/adrs/ (was referenced everywhere, existed nowhere) with
  ADR-0001 completion-sprint cadence; fixed the dangling adrs/0004 citation.
- Added `--cov-fail-under=80` so the documented coverage floor is enforced.
- Removed stale T-task-era PDFs and dangling path references; corrected the
  ARI gate (0.77→0.70) and T9-1 future-tense in epistemic_boundaries.

## Recommended next action

- Work the F-054 backlog one finding per PR (AUD-C1/C2 critical first).
- Human: enable branch protection requiring CI + Governance on main, and move
  Module A off a sleeping free tier (or add a cron deployment-health workflow)
  to close F-021 durably.

---

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
