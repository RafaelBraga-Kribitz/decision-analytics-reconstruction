---
id: 0003
title: "Use a 600-line Charter budget for this three-module project"
status: accepted
date: 2026-06-08
deciders: [Rafael Braga]
supersedes: null
superseded_by: null
---

# ADR-0003: Use a 600-line Charter budget for this three-module project

## Context

The bootstrap kit defaults to a 200-line Charter budget. That cap is useful for
small projects, but this repository has three analytical modules, cross-module
schema contracts, deployment surfaces, and governance state. A 200-line cap risks
making `PROJECT_CHARTER.md` too skeletal to act as the single source of truth.

## Decision

Set the project-specific Charter budget to 600 lines and keep `F-001` closed
against `scripts/check_charter_size.py`.

## Consequences

### Positive

- The Charter can summarize all three modules without pushing essential context
  back into parallel roadmap or plan documents.
- The cap still prevents uncontrolled sprawl because the file must remain below
  a hard, machine-checked line budget.

### Negative

- Reviewers must tolerate a longer Charter than the generic bootstrap default.
- Future agents may be tempted to place implementation detail in the Charter;
  `governance/adrs/` and derived docs remain the correct home for decisions and
  detailed references.

### Neutral

- The generic `governance-bootstrap/` template remains unchanged; this is a
  project-local policy override.

## Alternatives considered

- **Keep 200 lines** — rejected because it over-compresses a three-module system.
- **Remove the line cap** — rejected because it would disable the anti-sprawl
  invariant that `F-001` exists to enforce.

## References

- `PROJECT_CHARTER.md`
- `scripts/check_charter_size.py`
- `governance/findings/F-001-charter-sprawl.yaml`
