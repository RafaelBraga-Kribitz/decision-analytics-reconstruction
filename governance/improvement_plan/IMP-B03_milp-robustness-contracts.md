---
id: IMP-B03
title: "MILP robustness & contract corrections"
absorbs: [B5, B6]
overlaps_triage: []
priority: P2
effort: low
depends_on: []
soft_depends_on: []
queue: issues
target_repo: decision-analytics-reconstruction
issue: 59
status: filed
---

# IMP-B03 — MILP Robustness & Contract Corrections

Two independent gaps, both small, both in the "the code path exists but is
untested or contradicts its own SSOT" category:

**B5 — degenerate MILP inputs are untested.** `_run_allocation_solver`
(`models/allocation.py:539-544`) raises `RuntimeError` when CBC reports
`LpStatusInfeasible` or `LpStatusNotSolved`, but no test in
`tests/test_allocation.py` (or elsewhere in the suite) drives the model to
that branch. Nothing exercises `budget_usd=0`, an empty `reach_caps`
DataFrame, or an all-zero-audience segment. `_expected_contacts`
(`models/allocation.py:67-82`) already returns `0.0` gracefully when
`reachable_audience <= 0 or reach_used <= 0` — but the MILP as a whole
combines that graceful per-cell zero with a hard per-department coverage
floor (`COVERAGE_LOWER_BOUND_PCT`, `constants.py:144`, currently `0.80`)
enforced at `models/allocation.py:397-401`
(`prob += lpSum(dept_contacts) >= COVERAGE_LOWER_BOUND_PCT * dept_population_proxy`).
A zero budget makes every `dept_contacts` term zero while the coverage floor
still demands 80% of population reach — a guaranteed infeasibility that is
never exercised in CI, so we don't actually know CBC's status code, the
`RuntimeError` message content, or whether the process exits non-zero
cleanly versus hanging or raising an unrelated exception first (e.g. a
`ZeroDivisionError` upstream in `_unit_cost_usd` or `_reachable`).

**B6 — the A→B/B→C handshake contract disagrees with the SSOT week count.**
`contracts/schemas.py:15` defines
`AllocationHandshakeRow.week_index: int = Field(ge=1, le=60)`. The actual
campaign window is `WEEK_COUNT = 14` (`constants.py:116`,
`WEEK_LABELS = tuple(f"2018-W{w:02d}" for w in range(1, 15))`), and the
sibling contract `schema_contracts/allocation_output.yaml:62-67` correctly
bounds `week_index` to `min: 1, max: 14`. The Pydantic handshake validator
would accept a row with `week_index=40` — a week that cannot exist in this
campaign — while the CSV-facing contract correctly rejects it
(`utils/allocation_output_gate.py:45-46`,
`df["week_index"].between(1, WEEK_COUNT).all()`). Two validators for the
same field, one silently wrong.

## 1. Define the Scope (The Data Guardrails)

**In-Scope:**
- `_run_allocation_solver` (`models/allocation.py:539-544`) and its call path
  from `solve()` (`:694-745`): a degenerate-case test matrix covering
  `budget_usd=0.0`, `budget_usd` too small to satisfy
  `COVERAGE_LOWER_BOUND_PCT`, an empty `reach_caps` DataFrame, and a single
  all-zero-audience `(department, channel)` cell.
- `_expected_contacts`'s zero-return branch (`models/allocation.py:74-76`)
  and its interaction with the coverage-floor constraint
  (`:397-401`) under those degenerate inputs.
- `AllocationHandshakeRow.week_index` (`contracts/schemas.py:15`): bound
  correction from `le=60` to the SSOT `WEEK_COUNT` (`constants.py:116`,
  currently `14`), ideally imported rather than re-declared as a bare
  literal.
- A regression test proving `schema_contracts/allocation_output.yaml`'s
  `week_index` bound (`min: 1, max: 14`) and `AllocationHandshakeRow`'s bound
  never diverge again.

**Out-of-Scope:**
- The coverage-floor threshold itself (`COVERAGE_LOWER_BOUND_PCT = 0.80`) as
  a policy value — that is `IMP-B01`'s parameter-sensitivity sweep, not a
  robustness fix.
- Module A input uncertainty (`IMP-B02`).
- Silent-drop reporting in the cleaning layer (`IMP-B04`).
- Any other field in `AllocationHandshakeRow` beyond `week_index` — a scan
  for similar drift is worth doing, but is not itself in this document's
  in-scope diff (name it as a follow-up if found).

## 2. Data-Driven "Given-When-Then" Scenarios

**Scenario: Zero-budget solve fails cleanly (Happy Path)**
- **Given** `build_problem(budget_usd=0.0)`,
- **When** `solve(problem)` is called,
- **Then** it raises `RuntimeError` with a message containing
  `"status=Infeasible"` (the exact string produced by
  `models/allocation.py:543`), and no other exception type (e.g.
  `ZeroDivisionError`, `KeyError`) is raised first — the failure mode is the
  documented one, exercised by an explicit test rather than left implicit.

**Scenario: Handshake contract rejects an out-of-window week (Edge Case)**
- **Given** a candidate `AllocationHandshakeRow` payload with
  `week_index=40` and otherwise-valid fields,
- **When** `AllocationHandshakeRow(**payload)` is constructed,
- **Then** Pydantic raises a `ValidationError` for `week_index` — matching
  the behavior already enforced by
  `utils/allocation_output_gate.py:45-46` for the CSV-facing contract, so the
  two validators agree.

**Scenario: Empty reach_caps produces a defined failure, not a crash (Edge Case)**
- **Given** `build_problem(reach_caps=pd.DataFrame())` (an empty frame, no
  `department`/`channel` columns),
- **When** `solve(problem)` is called,
- **Then** it raises a specific, tested exception (e.g. `KeyError` naming the
  missing `department`/`channel` index, or a new explicit
  `ValueError("reach_caps is empty")` raised early in `solve()`) — never an
  unhandled `IndexError` or a silently empty allocation output.

## 3. Specify Undesirable Behaviors (Negative Constraints)

**Scenario: Preventing contract-bound drift from the SSOT**
- **Given** `constants.py:116`'s `WEEK_COUNT` is the single source of truth
  for the campaign's week window,
- **When** any Pydantic model or YAML contract declares a `week_index`
  bound,
- **Then** a static or test-time check must assert that bound equals
  `WEEK_COUNT` (currently `14`) — a hard-coded `le=60` (or any other
  mismatched literal) is a failing state, not a stylistic nit, because it
  lets a Module C consumer accept handshake rows describing weeks that never
  occurred in the campaign.

**Scenario: Preventing degenerate-input tests from being silently skipped**
- **Given** the degenerate-case test matrix added by this IMP,
- **When** `make verify` runs,
- **Then** each of the zero-budget, empty-reach-caps, and all-zero-audience
  cases executes and asserts on the specific exception type and message —
  a bare `pytest.raises(Exception)` (any exception, no message check) does
  not satisfy this scenario; the assertion must pin the actual failure mode.

## 4. Detail Data-Specific Non-Functional Requirements

- **Model fairness / bias:** N/A — this IMP changes failure-path behavior
  and a contract bound; it does not touch any coefficient that
  differentiates departments or channels.
- **Performance & decay:** the new degenerate-case tests must each complete
  in under 5 seconds (they either fail fast on an empty frame or hit CBC on
  a trivially small problem); no new test may require a full 2,772-row solve.
- **Data integrity:** the corrected `week_index` bound must be enforced at
  both the Pydantic layer (`contracts/schemas.py`) and the YAML contract
  layer (`schema_contracts/allocation_output.yaml`) — this IMP's regression
  test reads both and asserts they match `constants.WEEK_COUNT`, not just
  each other, so a future change to `WEEK_COUNT` alone is caught.
- **Reproducibility:** the degenerate-case tests must not depend on solver
  seed or scenario choice — a `RuntimeError` on `budget_usd=0.0` must be
  deterministic regardless of `solver_seed`.

## 5. Queue Stub (ready to file)

```
Title: Add degenerate-input test matrix for the Module B MILP and fix the AllocationHandshakeRow week_index bound

## Problem
Two small, independent gaps:
1. `_run_allocation_solver`
   (`module_b_resource_allocation/src/module_b_resource_allocation/models/allocation.py:539-544`)
   raises `RuntimeError` on CBC infeasible/not-solved status, but no test
   drives `budget_usd=0`, an empty `reach_caps`, or an all-zero-audience
   segment into that path. The per-department coverage floor
   (`COVERAGE_LOWER_BOUND_PCT`, `constants.py:144` = `0.80`, enforced at
   `models/allocation.py:397-401`) makes a zero-budget solve guaranteed
   infeasible, but that guarantee is never exercised in CI.
2. `AllocationHandshakeRow.week_index`
   (`module_b_resource_allocation/src/module_b_resource_allocation/contracts/schemas.py:15`)
   is bounded `ge=1, le=60`, while the campaign's actual SSOT week window is
   `WEEK_COUNT = 14` (`constants.py:116`) and the sibling CSV contract
   (`schema_contracts/allocation_output.yaml:62-67`) correctly bounds
   `week_index` to `min: 1, max: 14`. The handshake validator would silently
   accept an impossible `week_index=40`.

## Evidence
- `module_b_resource_allocation/src/module_b_resource_allocation/models/allocation.py:539-544` — untested `RuntimeError` path.
- `module_b_resource_allocation/src/module_b_resource_allocation/models/allocation.py:74-76` — `_expected_contacts` graceful zero-return.
- `module_b_resource_allocation/src/module_b_resource_allocation/models/allocation.py:397-401` — coverage-floor constraint that conflicts with zero budget.
- `module_b_resource_allocation/src/module_b_resource_allocation/contracts/schemas.py:15` — `week_index: Field(ge=1, le=60)`.
- `module_b_resource_allocation/src/module_b_resource_allocation/constants.py:116` — `WEEK_COUNT = 14`, the SSOT.
- `schema_contracts/allocation_output.yaml:62-67` — the correctly-bounded sibling contract.
- `module_b_resource_allocation/src/module_b_resource_allocation/utils/allocation_output_gate.py:45-46` — the CSV-facing validator that already enforces `WEEK_COUNT`.

## Acceptance criteria
1. New tests in `tests/test_allocation.py` (or a new
   `tests/test_allocation_degenerate.py`) cover: `budget_usd=0.0` →
   `RuntimeError` with message containing `"Infeasible"`; empty `reach_caps`
   → a named, specific exception; an all-zero-audience `(department,
   channel)` cell → no crash, contributes zero contacts, and does not by
   itself make the department's coverage constraint infeasible if other
   channels cover it.
2. `AllocationHandshakeRow.week_index` bound changed to
   `Field(ge=1, le=WEEK_COUNT)` (importing `WEEK_COUNT` from
   `module_b_resource_allocation.constants`), or an equivalent that cannot
   drift from the constant.
3. A regression test asserts
   `AllocationHandshakeRow.model_fields["week_index"]`'s bound equals
   `WEEK_COUNT` and equals `schema_contracts/allocation_output.yaml`'s
   `week_index.max`.

## Verification
- `pytest module_b_resource_allocation/tests/test_allocation.py -k degenerate`
  exits 0.
- `pytest module_b_resource_allocation/tests/test_contract_schemas.py -k week_index`
  exits 0 and fails if `le=60` is reintroduced.

## Spec
governance/improvement_plan/IMP-B03_milp-robustness-contracts.md

## Labels
type:bug, skill:module-b, effort:low, priority:p2, status:claude-ready
```
