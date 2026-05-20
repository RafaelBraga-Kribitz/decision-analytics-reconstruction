# /task-transaction

**Unit closure gate** — persists one closed **UNIT_ID** with evidence and updates the runtime lock. Does **not** mark a multi-unit task complete unless every unit in §N is closed.

---

## Preconditions

1. [ ] `.cursor/runtime/current_unit.json` exists; `status` is `declared` or `in_progress`.
2. [ ] `/task-verify` evidence for **this UNIT_ID** exists in **this** session.
3. [ ] Staged paths will be ⊆ `unit_impact_set` from the lock (reconcile before staging).

---

## Steps (after verify)

1. Run `make transaction-verify` (plan-reconciliation on the index).
2. `git add` **only** paths listed in `unit_impact_set` for this unit.
3. Compose final commit message: **must include the exact `unit_id` string** (body footer `[UNIT_ID:…]` is acceptable); Conventional Commits first line.
4. `git commit` — commit-msg hook enforces message vs lock when the lock file is present.
5. Record `commit_sha` and set lock `status` to **`closed`**, `closed_at` (ISO-8601); keep file for audit or delete per team policy (default: retain with `closed` for one unit of history).
6. Emit **unit summary**: `unit_id`, `task_id`, `commit_sha`, files, key verification commands + exit 0.

---

## Session boundary (mandatory)

After this command:

- The **unit is closed**.
- **Do not** start another unit in the same session.
- Next unit: explicit **`/task-execute`** or orchestrator dispatch in a **new** turn (new plan slice for that `unit_id`).

---

## Push

**Push is not part of the transaction.** Sync or push only when the operator requests it.

### Next step when more units remain

→ New session turn: update plan §K for the next `unit_id`, refresh `current_unit.json`, then **`/task-execute`**.

### Next step when all units in §N are closed

→ **`/task-complete`**, then `poetry run graphify update .` per graphify rule.
