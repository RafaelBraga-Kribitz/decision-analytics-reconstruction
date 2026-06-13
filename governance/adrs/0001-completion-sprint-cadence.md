# ADR-0001: Completion-sprint cadence for multi-finding PRs

- **Status:** accepted
- **Date:** 2026-06-13
- **Finding(s):** governance hygiene (referenced by `governance/AUDIT_PROCEDURE.md`)

## Context

`governance/AUDIT_PROCEDURE.md` forbids touching more than one finding per PR,
with an exception for "themed multi-finding PRs during a declared completion
sprint" — but the ADR that exception cited did not exist, so the exception was
unusable in principle and unenforced in practice (e.g. commit `06294d9` closed
F-041, F-043, F-044 and F-008 in one PR with no declaration anywhere).

## Decision

A completion sprint is declared by committing a sprint plan under
`governance/` (e.g. `governance/Truth_and_rebuild_sprint.md`) **before** the
multi-finding PRs land, and every multi-finding PR description must name the
sprint document and list the finding IDs it touches. Without a committed
sprint document, the one-finding-per-PR rule applies with no exception.

## Consequences

- The exception in `AUDIT_PROCEDURE.md` now points at a real, checkable rule.
- Reviewers can audit any multi-finding PR by following its sprint link.
- Closing several findings in one PR without a committed sprint plan is a
  procedure violation that should be called out in review.
