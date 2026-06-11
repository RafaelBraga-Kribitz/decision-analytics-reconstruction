---
id: 0004
title: "Allow themed multi-finding PRs during completion sprints"
status: accepted
date: 2026-06-11
deciders: [Rafael Braga]
supersedes: null
superseded_by: null
---

# ADR-0004: Allow themed multi-finding PRs during completion sprints

## Context

`governance/AUDIT_PROCEDURE.md` mandates one finding per PR. That cadence is
correct for steady-state maintenance: it keeps diffs reviewable and makes the
Adversary's per-finding re-verification unambiguous. During a time-boxed
completion sprint (AI-driven development, human in the loop for decisions and
validation) the same rule multiplies ceremony: a single root cause often spans
several findings (e.g. one pipeline-wiring change closes both a missing-artifact
finding and a stale-output finding), and serializing them into separate PRs
adds review latency without adding safety, because closure was never defined by
PR shape — it is defined by the finding's `verification_script` exiting 0.

## Decision

During a declared completion sprint, the Remediator may close **multiple
findings in one themed PR** when they share a root cause or a single
remediation surface (one subsystem, one pipeline stage, one document set).

Non-negotiable invariants that do **not** change:

- A finding is closed only when its named `verification_script` exits 0.
- Every closed finding remains subject to Adversary re-verification on every PR.
- The PR title must list **every** finding ID it closes.
- Unrelated findings must not ride along; "themed" means a reviewer can state
  the shared root cause in one sentence.

Outside a declared sprint, the default one-finding-per-PR cadence applies.

## Consequences

### Positive

- Root-cause fixes land atomically; no artificial sequencing of co-dependent
  findings.
- Sprint throughput matches AI-driven development speed while the closure gate
  (script exit 0 + Adversary ratchet) keeps integrity guarantees intact.

### Negative

- Larger diffs per PR; reviewer effort per PR increases during sprints.
- A regression in a themed PR reopens several findings at once.

### Neutral

- The Adversary CI job is unchanged — it already re-runs every closed finding's
  script regardless of how the finding was closed.

## Alternatives considered

- **Keep strict one-finding-per-PR** — rejected for sprints: serializes
  co-dependent fixes and inflates calendar time without improving verification.
- **Drop the findings queue during sprints** — rejected: loses machine-readable
  state and the Adversary ratchet, the system's core value.

## References

- `governance/AUDIT_PROCEDURE.md` (Remediator contract, amended by this ADR)
- ADR-0002 (debt ratchet — the verification-first philosophy this preserves)
