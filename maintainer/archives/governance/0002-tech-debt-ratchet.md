<!--
Example ADR shipped with the bootstrap kit. Keep, edit, or delete it — but if
you keep the debt ratchet, keep a record of the decision somewhere.
-->
---
id: 0002
title: "Gate technical debt with a downward-only ratchet"
status: accepted
date: 2026-01-01
deciders: [Rafael Braga]
supersedes: null
superseded_by: null
---

# ADR-0002: Gate technical debt with a downward-only ratchet

## Context

Technical debt (dead code, unused exports, duplication, runaway complexity)
accumulates silently between sessions. By the time it's visible it's expensive
to remove. LLM-driven development accelerates this: each session adds code, few
sessions remove it. We already prevent *finding* regressions with a ratchet
(closed findings re-verified every PR); debt deserves the same treatment.

No single open-source tool does for Python what Fallow does for TS/JS (blend
static analysis with runtime coverage), so the gate must compose several
specialized tools and tolerate any of them being absent.

## Decision

Add a **debt ratchet**: `scripts/debt_scan.py` writes a normalized
`governance/DEBT_BASELINE.json`; `scripts/check_debt_ratchet.py` re-scans on
every PR and fails when any measured metric grows past the baseline, or exceeds
an absolute cap. The baseline can only move down without an explicit PR. The
Steward surfaces current hotspots in the session handout so the next remediation
enters the normal one-finding-per-PR flow rather than an ad-hoc cleanup.

Tools are pluggable and gracefully degrading: Python uses ruff + vulture +
radon; TS/JS uses knip + jscpd, or Fallow directly if installed. A metric whose
tool is missing is reported as unmeasured and does not gate.

## Consequences

### Positive

- Debt cannot grow unnoticed; every increase is a red PR with the specific metric.
- Reductions are durable — once locked into the baseline, the ratchet holds them.
- Remediation reuses the existing finding workflow; no parallel process.

### Negative

- Requires the relevant tools installed in CI (a few extra `pip`/`npm` installs).
- Tool nondeterminism (esp. duplication %) needs an epsilon tolerance.

### Neutral

- Runtime profilers (viztracer, coverage.py) are advisory, not ratcheted — they
  inform but don't gate, because production-shaped runtime data isn't available
  in CI by default.

## Alternatives considered

- **Auto-fix on commit** — rejected: violates one-finding-per-PR and produces
  large unreviewable diffs.
- **A single SaaS code-review bot** — rejected: external dependency, no offline
  story, and it doesn't integrate with the on-disk finding queue.
- **Do nothing / rely on lint** — rejected: lint catches per-file issues, not
  cross-module dead exports, duplication, or architectural drift.

## References

- https://github.com/fallow-rs/fallow
- `governance/DEBT_TOOLS.md`
- `governance/AUDIT_PROCEDURE.md` (the finding ratchet this mirrors)
