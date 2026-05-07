# Routing matrix

Canonical dispatch table for **orchestrator** + **`/task-dispatch`**.

## Cursor project agents (`.cursor/agents/`)

| Agent | Role |
|-------|------|
| `orchestrator` | Classify → fill context payload → recommend specialist + skills |
| `module-a-specialist` | Module A codebase: generation, cleaning, segmentation, propensity |
| `module-b-specialist` | Module B codebase: LP/MILP solver, FX, routing, FastAPI |
| `module-c-specialist` | Module C codebase: Bayesian aggregation, MCMC, scenarios, Quarto |
| `qa-gatekeeper` | Independent QA: DoD + 6-layer checklist + signed verdict |
| `integration-impact-auditor` | Cross-module / schema contracts / CI changes |

## Task type → primary agent → skills

| Task type | Primary agent | Read first | Global skills (invoke in order listed) |
|-----------|---------------|------------|----------------------------------------|
| Intake / ambiguous | `orchestrator` | `project-orchestrator` | `writing-plans`, `verification-before-completion` |
| Module A modeling/data | `module-a-specialist` | `project-module-a` | `data-science/skills/02-data/data-quality-audit` (DAMA-5 first), `test-driven-development`, `scikit-learn`, `shap`, `systematic-debugging`, `verification-before-completion` |
| Module B optimization/API | `module-b-specialist` | `project-module-b` | `test-driven-development`, `systematic-debugging`, `verification-before-completion` |
| Module C Bayesian | `module-c-specialist` | `project-module-c` | `pymc` (8-step canonical), `data-science/agents/ds-qa` (6-layer QA), `test-driven-development`, `systematic-debugging`, `statistical-analysis`, `verification-before-completion` |
| Large refactor / boundaries | `integration-impact-auditor` | `project-verification` | `code-auditor`, `verification-before-completion` |
| Release / high-risk verify | `qa-gatekeeper` | `qa-gatekeeper.md` | `verification-before-completion` |

## Escalation additions (always check orchestrator escalation matrix)

| Trigger | Always add |
|---------|------------|
| Schema contract change | `integration-impact-auditor` |
| Calibration anchor change | `integration-impact-auditor` + `qa-gatekeeper` |
| MCMC delivery (Module C) | `qa-gatekeeper` (mandatory) |
| Risk = high | `qa-gatekeeper` (mandatory) |
| 3+ failed fixes | STOP — log in `reports/decision_log.md`; escalate |

## Parallelism

Independent tasks (e.g. unrelated test files in A vs B): `dispatching-parallel-agents` — **after** separate `/task-plan` items and confirmation of no shared schema/config state.

## Cursor Task tool mapping (optional)

When using Cursor `Task` tool: `explore` for readonly codebase discovery; `coder`/`generalPurpose` for implementation **only after** plan approval; `reviewer` before merge-grade completion.
