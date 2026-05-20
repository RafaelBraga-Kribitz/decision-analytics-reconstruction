# /task-complete

**Todo completion gate** — updates Cursor todos **only** when all preconditions are met. This command cannot be run without evidence.

---

## No-close rule

```
TODO ITEMS MUST NOT BE MARKED COMPLETE UNLESS ALL OF THE FOLLOWING ARE TRUE:
1. /task-verify evidence block exists in this session.
2. Every criterion row in the proof table is PASS with numeric/command evidence.
3. QA gatekeeper signed verdict is attached (medium/high risk tasks).
4. Zero open FAIL rows; zero blocking issues.
5. TDD compliance confirmed (watched each test fail before implementing).
6. Terminology scan clean (no banned terms in deliverables).
7. Every planned change unit (`UNIT_ID` in §N, or the single unit if no queue) has a closed transaction:
   commit SHA + `unit_id` recorded (runtime lock `status` closed or equivalent audit trail).
```

Attempting to mark complete without meeting all **7** conditions is a harness violation.

---

## Precondition checklist (verify each before proceeding)

- [ ] `/task-verify` was run in this session (not a prior session or conversation).
- [ ] Proof table from `/task-verify` has zero blank rows and zero `FAIL` rows.
- [ ] For Module C tasks: ArviZ diagnostics summary attached (R-hat, ESS, divergences).
- [ ] For Module B tasks: solver status log attached (status + objective + binding constraints).
- [ ] For Module A tasks: calibration report or `validator.py` output attached.
- [ ] If medium/high risk: `qa-gatekeeper` signed verdict pasted here.
- [ ] If schema/contract changed: `integration-impact-auditor` sign-off logged.
- [ ] Quarto render exit 0 (Module C only).

---

## Actions (only after all boxes checked)

1. Mark related Cursor todos **completed** — only the ones whose criterion rows are all PASS.
2. Summarize **closed deliverables**: list exact file paths produced or modified.
3. List **follow-up tasks** created (if any) with new TASK-IDs.
4. If calibration/schema/pipeline changed: record artifact hash or commit reference:
   ```
   Artifact: <path>
   Hash/Commit: <SHA or DVC hash>
   ```

---

## Forbidden

- Marking `completed` with partial criteria, missing verification, or "assumed passing".
- Marking `completed` without a fresh verification run (prior session output is stale).
- Marking `completed` when qa-gatekeeper is required but not yet signed.

### Next task
→ `/task-intake` for the next item.
