---
name: project-module-b
description: Resource allocation engine — Module B. Use for PuLP/CVXPY LP, FX modeling, TSP routing, FastAPI endpoint. Embeds TDD iron law, systematic debugging 4-phase, quantitative feasibility gates.
disable-model-invocation: true
---

# Project Module B

## Non-negotiable order of operations

```
1. Preflight:  Constraint inventory → input schema verification → feasibility pre-check
2. TDD:        Failing test first → minimal implementation → verify green
3. Debug rule: 4-phase systematic debugging before ANY solver fix; 3+ failures → escalate
4. Validate:   Run all B1–B11 gates from module-b-specialist.md Phase 3
5. Evidence:   Solver log + test output + gate mapping + FX provenance before /task-verify
```

## Required reading
- `project_scope/scope_module_B_resource_allocation_engine.md`
- `resource_allocation_engine/config/resource_config.yaml` (when present)

## Global skills — invoke in this order

1. `test-driven-development` — TDD iron law applies to every `src/` change.
2. `systematic-debugging` — 4 phases before proposing any solver or routing fix.
3. `verification-before-completion` — gate function before every completion claim.

## Block conditions

- Solver returns INFEASIBLE → do not proceed; apply systematic-debugging Phase 1 before relaxing constraints.
- Constraint relaxation not justified by root-cause analysis → BLOCK; document rationale in decision log.
- Lead-time literal detected (`grep -rn "[0-9]\+ days\?" src/` returning hard-coded values) → fix before passing B10.
- FX rate used without traceable BCP provenance → BLOCK B5/B6.
- 3+ failed solver fixes → STOP; do not attempt Fix #4; escalate to architecture review.

## Quantitative acceptance summary

| Metric | Target | Source |
|--------|--------|--------|
| Solver status | OPTIMAL or FEASIBLE | Scope §5.1 |
| Municipality coverage | ≥ 80% | Scope §5.2 |
| BCP corridor share | ≤ 10% | Scope §5.3 |
| USD/PYG deviation from BCP | ≤ ±0.5% | Scope §5.4 |
| District mean travel time (Phase 2) | ≤ 4.5 h | Scope §5.5 |
| FastAPI p95 latency | ≤ 2 s (10 concurrent) | Scope §5.7 |
