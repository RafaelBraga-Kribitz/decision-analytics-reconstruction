# /task-plan

Produces the **approved execution plan** before implementation. Must satisfy plan-first rules. No plan → no dispatch.

---

## Required sections (all mandatory — no section may be blank or have placeholders)

### A. Objective
Clear, single-sentence outcome for **this change unit only** (must match §K `scope` — not the whole multi-unit epic).

### B. Context payload (copy from orchestrator output)
```yaml
task_id: "TASK-YYYYMMDD-###"
taxonomy: "<label>"
risk: "low | medium | high"
primary_agent: "<agent slug>"
secondary_agents: []
skills: []
```

### C. Constraints
Time, hardware, "must use Poetry", "no secrets in code", active module series for Module C, etc.

### D. Must-do (numbered)
Numbered list. Each item must be verifiable.

### E. Must-not (numbered)
Explicit anti-goals: no banned terminology, no hard-coded literals, no mixing calibration series, no fixing without root-cause investigation.

### F. Success criteria with quantitative thresholds

| Criterion | Verification command | Expected pass condition | Gate |
|-----------|---------------------|------------------------|------|
| <criterion 1> | `<exact command>` | `<exit 0 / value ≥ X / PASS>` | A1/B1/C1/... |
| <criterion 2> | `<exact command>` | `<expected>` | |

**Rule:** Every criterion MUST have an exact verification command. "Review confirms" or "looks correct" are not valid conditions. If you cannot specify a command, the criterion is incomplete.

### G. TDD plan
- List each function/class/endpoint to be implemented.
- For each: name the test file and test function to write first.
- Confirm: code will be written only after the test fails for the expected reason.

### H. Impact map
- **Files touched:** list every file this **unit** may change (`src/`, tests, docs, scripts as applicable).
- **`unit_impact_set`:** explicit repo-relative paths allowed in the **commit** for this unit (feeds `transaction_commit_gate.py`: staged files must be ⊆ this set).
- **`allowed_paths`:** glob/prefix patterns where edits are permitted during the unit (broader than `unit_impact_set` when useful, e.g. `tests/`).
- **Schema contracts touched:** yes/no + which contracts.
- **Upstream/downstream:**
  - Does this change outputs consumed by Module B or C? (Module A)
  - Does this change inputs expected from Module A or outputs to Module C? (Module B)
  - Does this change calibration priors or scenario outputs? (Module C)

### I. Todo list (mirror Cursor todos)
Checkboxes aligned with Cursor todo items for this task.

### J. Rollback
Exact steps to revert if `/task-verify` fails.

### K. Change unit (this cycle) — UNIT_ID
- **`unit_id`:** `TASK-ID-NN` (two-digit sequence per task; example `TASK-20260520-01`).
- **One-sentence `scope`:** the single semantic intention for this unit.
- **`commit_message_draft`:** Conventional Commits subject line **including** the literal `unit_id` in the subject or body (required for commit-msg gate).

### L. Diff budget
- **`diff_budget_max`:** soft cap (default 15). Raise in plan if the unit is legitimately large; use `TRANSACTION_ALLOW_LARGE=1` only when the plan documents the exception.

### M. Branch
Feature branch name (must **not** be `main` / `master`). Example: `feat/docs-registry`.

### N. Unit queue (optional)
If the task has multiple units, list **`unit_id`** values in order. **Only one** unit is active per session: mark the active `unit_id`; others run in later `/task-execute` turns after prior **`/task-transaction`**.

### Runtime lock (operator obligation)

After approval, write **`.cursor/runtime/current_unit.json`** from §B `task_id`, §K–M, §H `unit_impact_set` / `allowed_paths`, with `status` `declared` or `in_progress`. See `.cursor/runtime/README.md` and rule `10-transaction-boundaries.mdc`.

---

## Approval gate

- **Low risk:** author self-approves after all sections filled with non-placeholder content.
- **Medium/high risk:** human acknowledgment required before dispatch. List open questions explicitly.
- **Never approve:** plan with blank sections, placeholder text, or criteria lacking verification commands.

### Next step
→ **`/task-dispatch`** then **`/task-execute`** (one **UNIT_ID** per invocation).
