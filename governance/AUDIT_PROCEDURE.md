# Audit Procedure

The single canonical reference for how this repo's audit + remediation cycle works. Do **not** invent a new scoring framework. If this procedure is wrong, edit this file in a dedicated PR and update `governance/findings/F-METHODOLOGY-DRIFT.yaml`.

## Three durable roles

### 1. Steward (read-only; runs at session start)

- **Entry point:** `make session-start`.
- **Contract:** runs `make audit`, reads `AUDIT_STATE.json` + every `findings/F-*.yaml` + the prior `SESSION_END.md`, then writes `governance/SESSION_HANDOUT.md`.
- **Output:** `SESSION_HANDOUT.md` lists (a) open findings by priority, (b) in-progress migrations and whether they're over `max_days_in_progress`, (c) last-verified state, (d) recommended next action.
- **Forbidden:** mutating any file except `SESSION_HANDOUT.md` and `AUDIT_STATE.json`.

### 2. Remediator (write; one finding at a time)

- **Entry point:** read `SESSION_HANDOUT.md`, pick **one** `open` finding from `findings/`.
- **Contract:**
  1. Make the change.
  2. Add or extend the `verification_script` named in the finding YAML.
  3. Update the finding YAML: `status: closed`, `closed_at: <iso-date>`, fill `verification_script` path.
  4. Run `make verify`.
  5. Open a PR. PR title must contain the finding ID (`F-NNN`).
- **Forbidden:** touching more than one finding per PR (except trivial cross-cutting cleanups under 10 lines); inventing new finding categories without prior agreement; declaring closure without a passing `verification_script`.

### 3. Adversary (read-only; CI job + session end)

- **Entry point:** GitHub Actions job `adversary` in `.github/workflows/governance.yml`.
- **Contract:**
  1. Clean checkout (no caches).
  2. Run `make audit`.
  3. For every `findings/F-*.yaml` with `status: closed`, execute its `verification_script`.
  4. If any script fails: fail the job and surface a directive to reopen the finding.
  5. Optionally scan the diff for new symptoms matching a closed-finding category and flag.
- **Forbidden:** modifying findings except via the auto-reopen path; never approving its own PRs.

## Finding lifecycle

```
       opened ─→ in_progress ─→ closed ─┬→ (re-verified each PR) ─→ closed
                                        └→ (re-verification fails) ─→ opened
```

Findings never simply disappear. Three terminal-ish states:

- `closed` — `verification_script` passes; subject to Adversary re-verification on every PR.
- `closed_historical` — describes a one-time change; no `verification_script`; immutable record.
- `wont_fix` — explicit rationale required in `wont_fix_reason`; subject to time-bounded review.

## Finding YAML schema

```yaml
id: F-NNN                          # required; F- prefix + 3-digit zero-padded
title: "human-readable summary"     # required
category: <category-slug>           # required; from your project's category list
kind: recurrence_invariant | historical_change | migration | deprecation
status: open | in_progress | closed | closed_historical | wont_fix
opened_at: YYYY-MM-DD               # required
closed_at: YYYY-MM-DD | null
recurrence_count: 0                 # how many prior cycles re-found this
evidence: "file:line — short claim"
verification_script: path/to/script_or_test.py | null
wont_fix_reason: "..."              # required iff status == wont_fix
notes: |
  free-text; safe to expand
```

## Migration YAML schema

```yaml
name: <slug>
status: not_started | in_progress | complete | abandoned
started_at: YYYY-MM-DD
max_days_in_progress: <int>
phases:
  - id: <slug>
    completion_criterion: "shell-verifiable predicate"
    done: bool
rollback: "git command or instructions"
linked_finding: F-NNN
```

`scripts/check_migrations.py` fails CI when any `in_progress` migration has been alive longer than `max_days_in_progress`.

## Handoff contract

`make session-end` writes `governance/SESSION_END.md` with:

1. Findings touched (IDs + before/after status).
2. ADRs added.
3. Invariants installed (script paths).
4. Open questions for next session.
5. Recommended next-finding priority.

The **next session begins by reading `SESSION_END.md` and running `make session-start`**, not by re-deriving state from prose.

## What to do when something is wrong

- A new failure category that doesn't match an existing slug → propose adding it in a dedicated PR before opening findings against it.
- An existing finding's `verification_script` produces false positives → open a follow-up finding `F-NNN-A` linked to the original; do not relax the original script silently.
- The Steward output looks stale → check `AUDIT_STATE.json` `generated_at`; re-run `make audit`.
- A PR appears to close a finding without a passing `verification_script` → the Adversary job will fail it; do not merge.
