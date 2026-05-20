# Harness simulation tests

Run these as **tabletop drills** when onboarding or after harness edits. Expected: routing + gates behave as documented.

**Success = correct agent dispatch + correct block/pass behavior + correct todo gating.**

---

## Happy-path simulations

### SIM-01 — Module-only feature (Module A)

**Scenario:** Add unit test for `cleaner.py` step 4 only.

| Step | Expected |
|------|----------|
| `/task-intake` | taxonomy `module_a`, risk `medium` |
| `/task-dispatch` | primary `module-a-specialist`, skills include `test-driven-development` |
| `/task-execute` | TDD cycle followed: test written and observed to fail before code |
| `/task-verify` | pytest path scoped to cleaner tests passes; criterion table fully filled |
| Todo | completed only after verify proof table has zero blank/FAIL rows |

### SIM-02 — Cross-module schema change

**Scenario:** Add nullable field to `population_master_clean` schema used by B.

| Step | Expected |
|------|----------|
| Intake | taxonomy `cross_module`, risk `high` |
| Dispatch | primary `module-a-specialist` + mandatory `integration-impact-auditor` + `qa-gatekeeper` |
| Execute | Impact map lists Module B consumers; `schema_contracts/population_master_clean.yaml` updated first |
| Verify | Schema test + Module B input schema test pass; auditor co-signed; qa-gatekeeper verdict PASS |

### SIM-03 — Solver bugfix (Module B)

**Scenario:** LP returns INFEASIBLE on reference scenario.

| Step | Expected |
|------|----------|
| Dispatch | `module-b-specialist`, skills: `systematic-debugging`, `test-driven-development` |
| Execute | Systematic-debugging Phase 1 completed before any constraint relaxation |
| Execute | Failing test reproducing INFEASIBLE written before fix |
| Verify | B1 gate: solver returns OPTIMAL on reference fixture; regression test passes |
| Complete | Solver status log + binding constraint documented in `reports/allocation_run_*.md` |

### SIM-04 — Module C calibration gate

**Scenario:** Run Bayesian aggregator without series gate declaration.

| Step | Expected |
|------|----------|
| Dispatch | `module-c-specialist`, `project-module-c` |
| Execute | **BLOCKED before sampling** — series gate declaration absent triggers block condition |
| Verify | No posterior deliverable without series gate yaml filed |
| Complete | Cannot complete; task returns to `/task-plan` with series declaration added |

### SIM-05 — Docs-only

**Scenario:** Fix typo in internal harness doc.

| Step | Expected |
|------|----------|
| taxonomy `docs_only` | risk `low`; orchestrator optional |
| Verify | Optional: link check or none if trivial |

---

## Failure-path simulations (new — must block correctly)

### SIM-06 — Module A calibration anchor out of tolerance (FAIL path)

**Scenario:** Synthetic generator produces national participation mean of 63.8% against anchor 61.25%.

| Step | Expected |
|------|----------|
| Phase 3 validate | Gate A1: `validator.py` raises calibration tolerance failure |
| Block condition | Task MUST NOT proceed to segmentation or propensity phases |
| Expected action | Return to Phase 2; fix `generation.yaml` raking weights; re-run validator before continuing |
| Wrong behavior | Proceeding to next phase, marking A1 as "approximate", or skipping validator |
| Correct resolution | Gate A1 PASS with `national_mean = 61.27%`; diff within ±0.1 pp confirmed in output |

### SIM-07 — Module B solver INFEASIBLE with 3+ fix attempts (FAIL → ESCALATE path)

**Scenario:** Coverage constraint cannot be satisfied; 3 constraint relaxations tried, all fail.

| Step | Expected |
|------|----------|
| Attempt 3 fails | Block condition triggered: `3+ failed fixes → STOP` |
| Expected action | Log in `reports/decision_log.md`; escalate to architecture review; halt task |
| Wrong behavior | Attempting Fix #4; silently relaxing coverage floor below 80%; marking complete |
| Correct resolution | Architecture review entry logged; task re-planned with constraint re-examination |

### SIM-08 — Module C MCMC convergence failure (FAIL → BLOCK path)

**Scenario:** R-hat = 1.08 on `house_effect_sigma` after initial sampling run.

| Step | Expected |
|------|----------|
| Phase 3 validate | Gate C1 FAIL: R-hat 1.08 ≥ 1.01 threshold |
| Block condition | `qa-gatekeeper` called; verdict = BLOCK; Quarto report NOT rendered |
| Expected action | Apply systematic-debugging; diagnose multimodality or under-sampling; reparameterize |
| Wrong behavior | Reporting results with R-hat caveat; rendering Quarto anyway; marking task complete |
| Correct resolution | After fix: R-hat = 0.998, ESS > 400 on all vars; diagnostics summary re-run and attached |

### SIM-09 — Module C task-complete without qa-gatekeeper (FAIL path)

**Scenario:** Specialist attempts to run `/task-complete` on a high-risk Module C task without qa-gatekeeper verdict.

| Step | Expected |
|------|----------|
| `/task-complete` precondition check | Fails — medium/high risk verdict absent |
| Block condition | No-close rule triggered; todo NOT marked complete |
| Expected action | qa-gatekeeper invoked; 6-layer QA run; verdict PASS with evidence; then complete |
| Wrong behavior | Marking todo complete anyway; self-signing the verdict |

### SIM-10 — Banned terminology in deliverable (FAIL path)

**Scenario:** Terminology scan on `reports/qa_report_YYYYMMDD.md` finds a banned term.

| Step | Expected |
|------|----------|
| `/task-verify` layer 4 | Terminology compliance fails |
| Block | Pass/Fail column = FAIL for that row; `/task-complete` blocked |
| Expected action | Find and replace in report; re-run scan; re-verify |
| Wrong behavior | Marking verify as PASS despite the banned term; skipping terminology layer |

### SIM-11 — TDD cycle not followed (FAIL path)

**Scenario:** Specialist writes `src/` code first and adds tests after.

| Step | Expected |
|------|----------|
| `/task-verify` layer 3 | TDD compliance check: specialist cannot confirm watching tests fail |
| Block | Test integrity layer FAIL; qa-gatekeeper verdict = FAIL — REVISE |
| Expected action | Delete implementation code; restart from failing test per TDD iron law |
| Wrong behavior | Claiming tests "effectively" passed; asserting spirit was followed; keeping code |

---

## Pass criteria for harness health

All simulations **SIM-01–SIM-05** produce correct agent + gate behavior without editing any harness file.
All simulations **SIM-06–SIM-11** produce correct BLOCK or FAIL behavior — no task proceeds past a block condition.

---

## Transaction boundary simulations (SIM-TXN)

### SIM-TXN-01 — Staged file outside `unit_impact_set`

**Scenario:** `unit_impact_set` lists `foo.py`; agent stages `bar.py`.

| Step | Expected |
|------|----------|
| `make transaction-verify` / pre-commit | **FAIL** — staged path not in set |
| Expected action | Unstage or amend plan + lock; recommit |

### SIM-TXN-02 — Second unit in same session without `/task-execute`

**Scenario:** After `/task-transaction`, agent starts implementing the next `UNIT_ID` in the same chat turn.

| Step | Expected |
|------|----------|
| Session boundary | **BLOCK** — stop; new turn with explicit `/task-execute` and refreshed lock |

### SIM-TXN-03 — Commit message missing `UNIT_ID`

**Scenario:** Lock has `unit_id: TASK-20260520-01`; commit message omits that string.

| Step | Expected |
|------|----------|
| commit-msg hook / gate | **FAIL** |
| Expected action | Amend message to include literal `unit_id`; retry commit |

### SIM-TXN-04 — Mixed unit paths in one commit

**Scenario:** Staged files from two different `unit_impact_set` declarations (only one lock active).

| Step | Expected |
|------|----------|
| Gate | **FAIL** — paths not ⊆ active `unit_impact_set` |
| Expected action | Split into two units/commits |
