# Audit Procedure

The single canonical reference for how this repo's audit + remediation cycle works. Do **not** invent a new scoring framework. If this procedure is wrong, edit this file in a dedicated PR and update `governance/findings/F-METHODOLOGY-DRIFT.yaml`.

The cycle is structured as **four stacked loops**, per *loop engineering*: an inner agent loop wrapped by verification, wrapped by event-driven dispatch, wrapped by hill-climbing harness improvement. Each outer loop makes the inner loops more reliable. None of the durable roles, contracts, schemas, or scripts change — they are reframed into the loop they belong to.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ L4 hill-climbing       (analyse traces → harness PRs)                    │
│ ┌──────────────────────────────────────────────────────────────────────┐ │
│ │ L3 event-driven      (Project #1 / command / cron → dispatch)        │ │
│ │ ┌──────────────────────────────────────────────────────────────────┐ │ │
│ │ │ L2 verification    (make verify + adversary CI)                  │ │ │
│ │ │ ┌──────────────────────────────────────────────────────────────┐ │ │ │
│ │ │ │ L1 agent         (Remediator: one finding → change → PR)     │ │ │ │
│ │ │ └──────────────────────────────────────────────────────────────┘ │ │ │
│ │ └──────────────────────────────────────────────────────────────────┘ │ │
│ └──────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

| Loop | Role / mechanism                         | Trigger                                 | Output                              |
|------|------------------------------------------|------------------------------------------|-------------------------------------|
| L1   | **Remediator** (write, one finding)      | Pick one `open` finding                  | PR with `F-NNN` in title             |
| L2   | **make verify** + **Adversary CI**       | Every PR, every push                     | Pass/fail; reopens regressed findings |
| L3   | **Steward** + dispatch                   | Project #1 event / command / cron        | `SESSION_HANDOUT.md`; queued work    |
| L4   | **Hill-climbing analysis**               | Session end + scheduled sweep            | Harness-improvement PR + ADR        |

---

## L3 trigger surfaces (entry to the whole system)

L3 is the outermost runtime loop. It listens for events and dispatches the Steward, which produces a queue the Remediator consumes. Three surfaces fire L3:

### 1. GitHub Project #1 (default, event-driven)

Source of truth for active work: **<https://github.com/users/RafaelBraga-Kribitz/projects/1/>**.

The maintainer dispatcher (`.github/workflows/governance.yml` job `project-watch`) fires when:

- An issue carrying `status:claude-ready` is added to project #1, or
- An item already in project #1 transitions into the **Ready** lane, or
- A `findings/F-*.yaml` is added/modified with `status: open` on `main`.

Dispatch action: trigger `make session-start` in a clean checkout, post `SESSION_HANDOUT.md` to the issue, and label it `agent:queued`.

### 2. Command (manual, ad-hoc)

Any of:

```bash
make session-start        # local: regenerate state + SESSION_HANDOUT.md
make maintainer-run       # local: full L1→L2 against the top SESSION_HANDOUT item
gh workflow run governance.yml -f mode=maintainer   # remote dispatch
```

The slash-command equivalent is `/maintainer-run` (Claude Code skill `init`-mode), which wraps `make session-start` and proceeds into L1 against the top-priority finding.

### 3. Automatic heartbeat (cron, project-driven)

`.github/workflows/governance.yml` runs on `schedule: cron` every 6 h. The heartbeat job:

1. Pulls project #1 via `gh project item-list 1 --owner RafaelBraga-Kribitz`.
2. Flags any `status:claude-ready` item idle > 24 h as `agent:stale`.
3. If a `status:claude-ready` item exists with no `agent:queued` label, calls `gh workflow run governance.yml -f mode=maintainer`.
4. If the Adversary job most recently failed, opens a P0 issue auto-tagged to project #1.

All three surfaces converge on the same L1 entry: the Remediator reads `SESSION_HANDOUT.md`.

---

## Three durable roles, mapped to loops

### L1 — Remediator (agent loop; write; one finding at a time)

- **Entry point:** read `SESSION_HANDOUT.md`, pick **one** `open` finding from `findings/`.
- **Contract:**
  1. Make the change.
  2. Add or extend the `verification_script` named in the finding YAML.
  3. Update the finding YAML: `status: closed`, `closed_at: <iso-date>`, fill `verification_script` path.
  4. Run `make verify`.
  5. Open a PR. PR title must contain the finding ID (`F-NNN`).
- **Forbidden:** touching more than one finding per PR (except trivial cross-cutting cleanups under 10 lines, or themed multi-finding PRs during a declared completion sprint per `adrs/0001-completion-sprint-cadence.md`); inventing new finding categories without prior agreement; declaring closure without a passing `verification_script`.

The Remediator *is* the L1 agent loop: model → tools (file edits, scripts, gh) → observation → repeat until `make verify` passes and the PR is open. Every iteration must produce a single-finding diff or stop.

### L2 — Adversary (verification loop; read-only; CI + session end)

- **Entry point:** GitHub Actions job `adversary` in `.github/workflows/governance.yml`.
- **Contract:**
  1. Clean checkout (no caches).
  2. Run `make audit`.
  3. For every `findings/F-*.yaml` with `status: closed`, execute its `verification_script`.
  4. If any script fails: fail the job. The finding is reopened manually — the Remediator (or maintainer) sets `status: open` in the YAML in a follow-up commit; no automation edits finding YAMLs.
  5. Optionally scan the diff for new symptoms matching a closed-finding category and flag.
- **Forbidden:** modifying any file (the Adversary is strictly read-only); never approving its own PRs.

The Adversary is the L2 grader. It wraps every L1 PR with: rubric = `make audit` + every closed finding's `verification_script` + debt ratchet (`scripts/check_debt_ratchet.py`). Fail → bounce back to L1 with feedback (the failing script's output).

Local pre-PR check the Remediator must run: `make verify`, which chains `make audit` → doc registry verify → terminology check → governance tests → `scripts/check_closed_findings.py` → `scripts/check_debt_ratchet.py`.

### L3 — Steward (event loop; read-only; runs at session start / on dispatch)

- **Entry point:** `make session-start` (locally) or the dispatcher above (remote).
- **Contract:** runs `make audit`, reads `AUDIT_STATE.json` + every `findings/F-*.yaml` + the prior `SESSION_END.md`, then writes `governance/SESSION_HANDOUT.md`.
- **Output:** `SESSION_HANDOUT.md` lists (a) open findings by priority, (b) in-progress migrations and whether they're over `max_days_in_progress`, (c) last-verified state, (d) recommended next action.
- **Forbidden:** mutating any file except `SESSION_HANDOUT.md` and `AUDIT_STATE.json`.

The Steward is the L3 event handler. Every dispatch event produces exactly one fresh `SESSION_HANDOUT.md`. Downstream agents (human or Claude) never re-derive state from prose.

### L4 — Hill-climbing analysis (new; read-only; session end + scheduled)

- **Entry point:** `make session-end` and the cron heartbeat above.
- **Contract:**
  1. Read every `findings/F-*.yaml` (`recurrence_count` field), the last N `SESSION_END.md` archives, and `AUDIT_STATE.json` history.
  2. Surface patterns: recurring findings, findings re-opened after closure, migrations exceeding `max_days_in_progress`, `verification_script`s with high false-positive rate.
  3. Open a *harness-improvement* PR (not a finding-close PR) that proposes one of: (i) a new finding category + ADR, (ii) a stronger `verification_script` for a recurring pattern, (iii) a tightened `audit` step (extra `scripts/check_*.py` in the Makefile), (iv) a procedure edit to this file.
- **Forbidden:** closing findings, editing finding YAMLs, modifying any `verification_script` covered by a *currently-open* finding without that finding's owner approval, merging without human review.

L4 is what makes the harness compound. Without it, repeated recurrences just accumulate; with it, each cycle should reduce the long-run recurrence rate.

---

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

`recurrence_count` is the L4 signal: every time a closed finding regresses and is re-opened, it increments. L4 prioritises findings with `recurrence_count >= 2` for harness rewrites.

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

The **next session begins by reading `SESSION_END.md` and running `make session-start`**, not by re-deriving state from prose. That start-of-session read is also the L4 input: the hill-climbing analysis runs over the last `SESSION_END.md` plus the prior N to detect drift.

## Project #1 item / finding correspondence

Every `open` finding *must* have a corresponding issue on project #1 with:

- title containing the finding ID,
- `status:claude-ready` once the Steward has produced a Remediator-actionable plan in `SESSION_HANDOUT.md`,
- automatic transition to `status:in-review` when the Remediator opens the PR (via `gh pr create --project 1`),
- automatic transition to `status:done` when the Adversary job passes on `main`.

Project #1 is the L3 source of truth; `findings/F-*.yaml` is the L1/L2 source of truth. When they disagree, the YAML wins for content; the project wins for *ordering* (what to work on next).

## Human oversight per loop

- **L1 (Remediator):** human review on every PR; required for any change to a `verification_script` or schema.
- **L2 (Adversary):** automated by default. Human override only for false positives, which must produce a follow-up `F-NNN-A` finding (see below).
- **L3 (Steward / dispatch):** humans can override the recommended next-finding by reordering project #1; the system honours project order.
- **L4 (Hill-climbing):** every harness PR requires human review before merge. No autonomous self-modification.

## What to do when something is wrong

- A new failure category that doesn't match an existing slug → propose adding it in a dedicated PR before opening findings against it.
- An existing finding's `verification_script` produces false positives → open a follow-up finding `F-NNN-A` linked to the original; do not relax the original script silently.
- The Steward output looks stale → check `AUDIT_STATE.json` `generated_at`; re-run `make audit`.
- A PR appears to close a finding without a passing `verification_script` → the Adversary job will fail it; do not merge.
- The cron heartbeat keeps re-firing on the same `status:claude-ready` item → check for `agent:stale` label; if present, a human must triage (the dispatcher will not re-queue stale items more than once per 24 h).
- L4 proposes a harness change that conflicts with an open finding → defer the harness PR until the open finding closes, or close the open finding first; never merge both in the same window.
