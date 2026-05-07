# Harness checklists

## A. Plan completeness (`/task-plan`)

- [ ] Context payload filled (task_id, taxonomy, risk, agents, skills)
- [ ] Objective: single-sentence, no placeholders
- [ ] Must-do / must-not explicit and numbered
- [ ] Success criteria: every row has an exact verification command + expected pass condition
- [ ] TDD plan: test file + function name listed for each logical unit
- [ ] Impact map: files, schema contracts, upstream/downstream effects
- [ ] Todo items mirror Cursor todos
- [ ] Rollback steps explicit
- [ ] No blank sections, no placeholder text ("TBD", "see above", "✓")

## B. Execution gate (`/task-execute`)

- [ ] TDD iron law: test written and observed to fail before any `src/` code
- [ ] Systematic-debugging: 4 phases completed before any fix proposed for bugs/failures
- [ ] No hard-coded literals (Module B); no banned terms (all modules)
- [ ] Progress reported with commands run + pass/fail per chunk

## C. Verification (`/task-verify`)

- [ ] Verification gate function run in THIS session (not prior session)
- [ ] Commands pasted with exact output (exit code, test count)
- [ ] Proof table: every success criterion row filled with numeric evidence
- [ ] No blank rows; no "see above"; no "✓" without value
- [ ] TDD compliance confirmed: watched each test fail first
- [ ] Terminology scan completed (for any deliverable with user-visible text)
- [ ] qa-gatekeeper verdict attached (for medium/high risk)
- [ ] Cross-module audit done if required

## D. Todo lifecycle protocol (gating)

States: **`pending`** → **`in_progress`** → **`completed`** (or **`cancelled`**).

| Transition | Allowed when |
|------------|----------------|
| → `in_progress` | `/task-plan` sections A–J filled; work actually starting |
| → `completed` | `/task-verify` all green; DoD satisfied; qa-gatekeeper signed (medium/high risk); **no** partial criteria |
| → `cancelled` | Task obsolete; reason documented in chat or decision log |

**No-close rule:** Never move to `completed` unless EVERY criterion in the proof table is PASS with evidence. Partial work → leave todo `in_progress` or split a new todo.

## E. Module-specific gates (summary pointers)

| Module | Gate file | Gate IDs |
|--------|-----------|----------|
| Module A | `module-a-specialist.md` Phase 3 | A1–A12 |
| Module B | `module-b-specialist.md` Phase 3 | B1–B11 |
| Module C | `module-c-specialist.md` Phase 3 | C1–C12 |
| All | `qa-gatekeeper.md` | 6-layer QA |

See `professional-grade-rubrics.md` for verdict-to-rubric mapping.

## F. Terminology (quick)

- [ ] No banned terms (scope master §12) in field names, string literals, config keys, comments, report text
- [ ] Module C: single calibration series; no hybrid Series A/B numerators in same model
- [ ] Vocabulary: "participation rate", "entity", "coordinator role", "area tier", "department", "municipality"
