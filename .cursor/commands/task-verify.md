# /task-verify

**Evidence gate** — attaches proof before completion. All criterion rows must have numeric or command-backed evidence. "Done" and "✓" are not evidence.

**Header (mandatory when using transaction harness):** `unit_id: <TASK-ID-NN>`, `task_id: <…>`.

---

## Verification gate function (run before this command)

```
1. IDENTIFY  — state the exact command that proves each claim
2. RUN       — execute it fresh, fully, in THIS session
3. READ      — read full output; note exit code; count failures
4. VERIFY    — does output confirm the claim?
             → If NO:  state actual status; do NOT run /task-complete
             → If YES: paste the relevant output lines below
5. ONLY THEN — fill the proof table
```

**Forbidden claims:** "should pass", "probably passes", "I'm confident", "manually verified", "passes based on prior run", "similar to last time".

---

## Required proof shape

### Commands executed

```
(paste EXACT commands with arguments — no abbreviations)
```

### Results

```
(paste EXACT terminal output — at minimum: exit code, test count, any numeric gate values)
```

### Criterion mapping (every row mandatory)

| Criterion (from plan § F) | Verification command | Exit / result | Gate | Pass/Fail |
|--------------------------|---------------------|---------------|------|-----------|
| <criterion 1 — exact wording from plan> | `<command>` | `exit 0 / value = X` | A1/B1/C1 | PASS |
| <criterion 2> | `<command>` | `<value>` | | PASS |

**Rules:**
- No row may be blank.
- No row may reference another row ("see above").
- Every `PASS` must have a numeric or textual value from actual output.
- Any `FAIL` row → do not run `/task-complete`; fix and re-run `/task-verify`.

---

### TDD compliance

- [ ] Watched each test fail before implementing (confirmed: yes / no — explain if no).
- [ ] Final test run: `<command>` → exit 0, `N/N` pass.

---

### Module-specific evidence

**Module A — attach if applicable:**
- Gate A1 (calibration anchors): paste `validator.py` output snippet
- Gate A7 (Brier score): `brier = X.XX` (must be < 0.22)
- Gate A5 (silhouette): `silhouette = X.XX` (must be > 0.35)

**Module B — attach if applicable:**
- Gate B1 (solver status): paste solver status line + objective value
- Gate B3 (coverage): paste `coverage = XX.X%` (must be ≥ 80%)

**Module C — attach if applicable:**
- Gate C1–C3 (MCMC): paste `az.summary()` R-hat max, ESS min, divergences
- Gate C6 (national scenario): paste `mean = X.XX%` vs anchor 61.25%
- Gate C11 (Quarto render): paste `quarto render` exit 0 confirmation

---

### Regression / cross-module impact

- Cross-module touches: `integration-impact-auditor` co-signed? yes / no / na
- Terminology scan: `grep -rn "banned_term" src/ reports/` output attached? yes / no / na

---

### QA gatekeeper sign-off (required for medium/high risk)

```
QA VERDICT — [TASK-ID] — [DATE]
Signed by: qa-gatekeeper
Verdict: [PASS | PASS WITH CAVEATS | FAIL — REVISE | BLOCK]
Confidence: [HIGH | MEDIUM | LOW]
Evidence: [paste command → result]
```

---

### Blockers

If ANY criterion row is FAIL or any evidence is missing: **do not run `/task-complete`**.
Fix → re-run `/task-verify` from the top.

### Next step
All rows PASS + QA signed (if required) → **`/task-complete`**
