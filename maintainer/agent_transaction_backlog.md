# Agent transaction backlog

**Audience:** Operators and autonomous agents.

**Purpose:** Capture scope discovered during a **closed `UNIT_ID`** so it is not implemented in the same session. Each line is append-only.

**Format (one row per discovery):**

```text
<ISO date> | task_id=<…> | discovered_in_unit=<UNIT_ID> | intention=<one line> | blocked_by=<active UNIT_ID or session>
```

Do **not** use this file as a substitute for an approved **`/task-plan`** or proof table for work that is actively executing.

**Related:** [`.cursor/rules/10-transaction-boundaries.mdc`](../.cursor/rules/10-transaction-boundaries.mdc), [`CONTROLLED_WORKFLOW_PLAYBOOK.md`](../docs/ai_harness/CONTROLLED_WORKFLOW_PLAYBOOK.md) §4.

---

## Log

<!-- Append below this line -->
