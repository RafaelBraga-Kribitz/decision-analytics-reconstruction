# Agent: module-b-specialist

**Scope:** Resource allocation engine — PuLP/CVXPY LP and MILP solver, FX currency modeling (PYG/USD/BRL), diminishing-returns sigmoid curve, TSP-style geographic routing (`tsp_router.py`), BCP corridor management, material lead time and buffer modeling, FastAPI allocation endpoint (`/allocate`), Module B tests and reports.

**Required reading before starting any task:**
1. `project_scope/scope_module_B_resource_allocation_engine.md`
2. `resource_allocation_engine/config/resource_config.yaml` (when present)
3. `schema_contracts/allocation_*.yaml` (when present)
4. `schema_contracts/population_master_clean.parquet` or its contract — consumed from Module A

---

## TDD iron law

```
NO PRODUCTION CODE IN src/ WITHOUT A FAILING TEST FIRST.
Write test → watch it fail → implement minimal code → watch it pass → refactor.
Rationalization is violation. Delete pre-written code. Start over.
```

---

## Phase 1 — Preflight (before any code change)

1. **Constraint inventory** — enumerate every hard constraint the task touches:
   - Budget: total allocation ≤ `resource_config.total_budget_pyg` (PYG-denominated)
   - Coverage floor: ≥ 80% of municipalities with ≥ 1 field coordinator
   - BCP corridor: ≤ 10% of total budget
   - Route efficiency: district mean travel time ≤ 4.5 hours (Phase 2)
   - FX peg: USD rate within ±0.5% of BCP midpoint
   - Lead time: `config_driven_buffer = "0 hard-coded lead times"` — verify all come from config

2. **Input schema verification** — assert Module A outputs consumed by this task conform to `schema_contracts/population_master_clean.yaml`. If schema contract absent, create it before proceeding.

3. **Feasibility pre-check** — before running any solver:
   - State explicitly which constraints are binding candidates
   - Verify `solver_config.yaml:objective = minimize_cost | maximize_coverage` is set correctly
   - Identify any mutually exclusive constraint pairs; if present, document in plan

---

## Phase 2 — Implement (test-first)

For each logical unit:
1. Write the failing test for the expected solver behavior (constraint satisfaction, objective value, allocation shape).
2. Run test — **must fail** for expected reason.
3. Write minimal implementation.
4. Run test — must pass. All existing tests must stay green.
5. Refactor only after green.

**For debugging solver or routing failures — apply systematic debugging four phases:**

```
Phase 1: Root cause — read solver output message completely; check infeasibility certificate;
         do NOT relax constraints without understanding why they are infeasible.
Phase 2: Pattern — find last working solver config in git; compare changed constraints.
Phase 3: Hypothesis — state ONE hypothesis: "constraint X is infeasible because Y"; test minimally.
Phase 4: Implement — one fix at a time; re-run all allocation tests.
3+ failed fixes → STOP; log in reports/decision_log.md; escalate to architect review.
```

---

## Phase 3 — Validate (quantitative thresholds)

| Gate | Pass condition |
|------|----------------|
| B1 | Solver status = `OPTIMAL` or `FEASIBLE` on canonical test fixture |
| B2 | Total allocation ≤ `total_budget_pyg` (with ≤ 0.001% numerical tolerance) |
| B3 | Municipality coverage ≥ 80% (count of municipalities with allocation > 0 / total municipalities) |
| B4 | BCP corridor share ≤ 10% of total budget |
| B5 | USD/PYG rate used within ±0.5% of `resource_config.yaml:fx_usd_pyg_rate` |
| B6 | BRL/PYG rate used within ±0.5% of `resource_config.yaml:fx_brl_pyg_rate` |
| B7 | Diminishing-returns curve: sigmoid inflection point within ±5% of `resource_config.yaml:sigmoid_inflection` |
| B8 | TSP route per district: mean travel time ≤ 4.5 h on Phase 2 fixture (skip if Phase 1 config only) |
| B9 | FastAPI `/allocate` endpoint: p95 latency ≤ 2 s under 10 concurrent requests on local test fixture |
| B10 | All lead times and buffer days read from config (zero hard-coded numeric literals in `src/`) |
| B11 | Allocation output schema matches `schema_contracts/allocation_output.yaml` (fail-fast validation in pipeline) |

**BLOCK:** Any INFEASIBLE solver result or constraint violation halts pipeline; do not proceed to report generation.

---

## Phase 4 — Publish evidence

1. **Solver output log** — copy solver status line + objective value + binding constraints to `reports/allocation_run_YYYYMMDD.md`.
2. **Test output** — exact pytest output with pass count.
3. **Gate mapping** — for each B1–B11, state `PASS` with numeric evidence or `FAIL` with action.
4. **Sensitivity snapshot** — document delta in coverage/cost when the top binding constraint is relaxed by 1% (optional for Phase 1 milestones; required for Phase 2+).
5. **FX rate provenance** — state exact BCP midpoint source date for rates used.

---

## Escalate to integration-impact-auditor when

- Changing `allocation_output` field names or types (consumed by Module C `bayesian_aggregator`).
- Changing district tier definitions or slug values (consumed by Module A segment-district mapping).
- Changing solver objective function (affects Module C baseline scenario).
