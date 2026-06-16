# CLAUDE.md — Agent Protocol for {PROJECT_SLUG}

This file is read by Claude Code (and any other LLM agent) at the start of every session. It encodes the only sanctioned operating protocol for this repository: read state from disk, do not invent state from prose.

## First action of every session

Run `make session-start`. This regenerates `governance/AUDIT_STATE.json` and writes a fresh `governance/SESSION_HANDOUT.md`. **Read the handout before proposing any work.** The handout names the recommended next finding and surfaces stalled migrations.

Do not skip this step "for speed." The handout is how cross-session memory works in this repo. Skipping it means re-deriving state from chat history, which is the failure mode the governance system was built to prevent.

## Three roles, one PR at a time

This repository's governance is documented in `governance/AUDIT_PROCEDURE.md`. The three roles defined there are the only sanctioned ways to act. Do not invent a new scoring framework, dimension count, or audit tier.

- **Steward** — reads state, regenerates the handout. Read-only. Runs at session start via `make session-start`.
- **Remediator** — picks one `open` finding, makes the change, closes the YAML, runs `make verify`, opens a PR. The PR title contains the finding ID (`F-NNN`).
- **Adversary** — the `governance-audit` CI job. Re-runs every closed finding's `verification_script` on every PR. A closed finding that regresses fails the PR and reopens itself.

If you cannot identify which of the three roles you are currently performing, stop and re-read `AUDIT_PROCEDURE.md`.

## Anti-patterns (banned)

These claims and behaviors have caused recurrence cycles in prior sessions. They are not allowed in this file, in commit messages, in PR descriptions, or in any committed artifact:

- Unverifiable navigation claims ("graph rebuilt on every commit", etc.). There is no such hook in this repo unless one is committed and verified.
- "Audited / fixed / closed" without a passing `verification_script` referenced in a finding YAML.
- Inventing a new methodology (TIER0/1/2, 11-dim, 12-dim, adversarial-Explore, etc). The methodology is `governance/AUDIT_PROCEDURE.md`. Period.
- Editing more than one finding per PR (except trivial cross-cutting cleanups under 10 lines).
- Closing a finding by editing `status: closed` without also running the verification script and confirming it passes.

## The findings directory is the work queue

`governance/findings/F-*.yaml` is the queue. Each YAML names a `verification_script` that defines closure. To close a finding:

1. Make the change.
2. Run the named script. Confirm it exits 0 with `[PASS]`.
3. Update the YAML: `status: closed`, `closed_at: <today>`.
4. Run `make verify` (which runs the Adversary locally).
5. Open a PR. The title must contain the finding ID.

If a finding has `verification_script: null`, it is either `closed_historical` (no script needed) or it needs a script written first. Writing the script is the first half of the work; the change is the second.

## Why this file exists

LLM coding sessions tend to invent a new methodology, run a new audit, declare "all clear," and disappear at `/clear`. The next session starts over because no machine-readable state survived. This file, plus `governance/AUDIT_STATE.json`, plus `governance/SESSION_END.md`, plus the Adversary CI job, exist so that does not happen here.

If you find yourself drifting toward a "let me first audit everything from scratch" approach, you are about to recreate the failure mode. Read `governance/SESSION_HANDOUT.md` instead.

## Where things live

| You want | Read |
|---|---|
| Current audit state | `governance/AUDIT_STATE.json` (machine-generated) |
| Open work queue | `governance/findings/F-*.yaml` |
| Prior session handoff | `governance/SESSION_END.md` |
| Methodology / roles | `governance/AUDIT_PROCEDURE.md` |
| Project SSOT | `PROJECT_CHARTER.md` (≤200 lines; index into specs) |
| Architecture decisions | `governance/adrs/` (with YAML frontmatter) |
| Version history | `governance/CHANGELOG.md` |
| Contributor rules | `CONTRIBUTING.md` |

## What this file does not do

- It does not summarize the project. Read `PROJECT_CHARTER.md` for that.
- It does not list current findings. Run `make session-start` for that.
- It does not contain any "context" that is duplicated elsewhere. Duplication is drift.

`make session-start` first. Then act.
