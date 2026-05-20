# /task-execute

Run the plan **for one change unit** (`UNIT_ID`). Do not skip gates. Evidence is required at each step.

---

## Pre-execution checklist (complete before writing any code)

1. [ ] Plan sections A–N filled; no blank sections; no placeholders (see `/task-plan`).
2. [ ] `.cursor/runtime/current_unit.json` exists, matches the active `unit_id`, and `status` is **not** `closed`.
3. [ ] Context payload confirmed; primary and secondary agents active.
4. [ ] Cross-module? Impact audit doc started per rule `03-cross-module-impact-gate.mdc`.
5. [ ] TDD iron law acknowledged: **no production code in `src/` without a failing test first**.
6. [ ] Systematic-debugging protocol acknowledged: **no fix proposed without root-cause investigation**.
7. [ ] Session scope: **this invocation implements exactly one `UNIT_ID`** — no parallel semantic intentions.

---

## TDD micro-loop (within the current unit only)

Repeat until this unit’s scope is done (still one `UNIT_ID`):

```
1. WRITE TEST  — write the failing test in tests/ before any src/ change
2. VERIFY RED  — run the test: it MUST fail for the expected reason (feature missing)
                 If it passes immediately: stop, fix the test, it doesn't test what you think
3. IMPLEMENT   — write minimal src/ code to make the test pass; nothing more
4. VERIFY GREEN — run the full test suite; ALL must pass; no warnings
5. REFACTOR    — clean up only after green; do not add behavior
```

**Do not** start another **UNIT_ID** in the same session after finishing this loop — use **`/task-transaction`**, then stop; next unit requires a **new** `/task-execute` turn.

If you discover unrelated work: append **`maintainer/agent_transaction_backlog.md`** (include `task_id`, `unit_id`, and what blocked it); do not implement.

---

## Debug gate (applies whenever a test fails unexpectedly or behavior is wrong)

```
STOP. Apply systematic-debugging:
Phase 1 — Root cause: read full error; reproduce consistently; check recent changes
Phase 2 — Pattern: find working examples; compare differences
Phase 3 — Hypothesis: one hypothesis at a time; test minimally
Phase 4 — Implement: one fix; verify; if fails → return to Phase 1
3+ failed fixes → STOP; do not attempt Fix #4; log in reports/decision_log.md; escalate
```

---

## Progress reporting (after each logical chunk)

```
unit_id: <from lock>
Files changed: [list — each must match plan allowed_paths / unit_impact_set]
Test command run: <command>
Result: N/N pass (exit 0) | FAIL: <message>
TDD cycle followed: yes | no (explain)
Root cause investigated: yes | na
```

---

## Mid-execution block conditions

- Test passes without implementation (skip cycle, fix test first).
- Unexpected INFEASIBLE (Module B solver) → apply systematic-debugging Phase 1 before constraint change.
- Divergences appear (Module C MCMC) → apply systematic-debugging before reparameterizing.
- Banned term found in output → halt, fix terminology, re-run.
- Any edit outside `allowed_paths` / `unit_impact_set` → halt; amend plan and lock, or move work to backlog.

### Next step
→ **`/task-verify`** for **this `unit_id`**, then **`/task-transaction`** to close the unit (then **stop** the session).
