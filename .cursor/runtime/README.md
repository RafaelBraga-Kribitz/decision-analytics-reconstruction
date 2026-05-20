# Agent runtime state (local only)

This directory holds **machine-local** state for transaction-boundary workflows.

## `current_unit.json`

**Not committed.** Recreated when a change unit is declared (see `/task-plan` §K–N and `.cursor/rules/10-transaction-boundaries.mdc`).

### Schema (illustrative)

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | Parent task identifier |
| `unit_id` | string | Unique unit id (`TASK-ID-NN`) |
| `unit_index` | int | Sequence within task (optional) |
| `scope` | string | One-sentence semantic intention |
| `status` | string | `declared` \| `in_progress` \| `closed` |
| `branch` | string | Working branch (not `main` / `master`) |
| `allowed_paths` | string[] | Glob/prefix patterns where edits are allowed |
| `unit_impact_set` | string[] | **Explicit** repo-relative paths that may appear in the commit |
| `commit_message_draft` | string | Conventional Commit draft (subject line) |
| `diff_budget_max` | int | Soft cap for staging warnings |
| `created_at` | string | ISO-8601 when lock was written |
| `commit_sha` | string | Set when `status` is `closed` |
| `closed_at` | string | ISO-8601 when unit closed |

`scripts/transaction_commit_gate.py` reads this file to enforce **staged ⊆ unit_impact_set** and path allowlists.
