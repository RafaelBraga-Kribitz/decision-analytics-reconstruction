# /task-execute

Run the plan **stepwise**. Do not skip gates. Evidence is required at each step.

---

## Pre-execution checklist (complete before writing any code)

1. [ ] Plan sections A–J filled; no blank sections; no placeholders.
2. [ ] Context payload confirmed; primary and secondary agents active.
3. [ ] Cross-module? Impact audit doc started per rule `03-cross-module-impact-gate.mdc`.
4. [ ] TDD iron law acknowledged: **no production code in `src/` without a failing test first**.
5. [ ] Systematic-debugging protocol acknowledged: **no fix proposed without root-cause investigation**.

---

## TDD execution loop (repeat for each logical unit)

```
1. WRITE TEST  — write the failing test in tests/ before any src/ change
2. VERIFY RED  — run the test: it MUST fail for the expected reason (feature missing)
                 If it passes immediately: stop, fix the test, it doesn't test what you think
3. IMPLEMENT   — write minimal src/ code to make the test pass; nothing more
4. VERIFY GREEN — run the full test suite; ALL must pass; no warnings
5. REFACTOR    — clean up only after green; do not add behavior
```

**Do not proceed to the next unit without completing all 5 steps for the current unit.**

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
Files changed: [list]
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

### Next step
→ **`/task-verify`** before marking any todo complete.
