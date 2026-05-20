# /task-intake

Use at the start of any work item. Loads orchestration rules and routes to planning.

## Required output (fill every section)

### 1. Task ID
`TASK-YYYYMMDD-###` or short slug.

### 2. Goal (one sentence)

### 3. Taxonomy
Pick one primary: `infra` | `module_a` | `module_b` | `module_c` | `cross_module` | `docs_only` | `research`

### 4. Scope
- **In scope:** …
- **Out of scope:** …

### 5. Risk
`low` | `medium` | `high` (schema change, calibration, solver, MCMC = high)

### 6. Primary dispatch recommendation
Per `docs/ai_harness/routing-matrix.md`:
- **Primary agent:** …
- **Skills:** …

### 7. Blockers / unknowns

### 8. Next step
→ Run **`/task-plan`** with this intake embedded.
