---
name: project-orchestrator
description: Routes PARAGUAY_ELLECTION tasks via typed context payload, deterministic dispatch, and escalation matrix. Use at task intake or when ownership is ambiguous.
disable-model-invocation: true
---

# Project orchestrator

## When to use
Every new task. Always before implementation. When taxonomy or ownership is ambiguous.

## Non-negotiable sequence

```
1. Fill context payload (TASK-ID → inputs → outputs → contracts → verification commands)
2. Classify deterministically per orchestrator.md Phase 2
3. Apply escalation matrix (Phase 3) — add qa-gatekeeper / integration-impact-auditor as required
4. Output payload to /task-plan
5. NEVER dispatch to implementation without approved plan
```

## Block conditions (halt and escalate)

- Payload section missing → do not dispatch; request missing fields first.
- `contracts_touched.calibration_anchors = yes` without `qa-gatekeeper` in secondaries → add it.
- `contracts_touched.module_c_series_gate = yes` without explicit series declaration → BLOCK; series must be declared before task proceeds.
- 3+ failed fix attempts on same issue → do not attempt Fix #4; log in `reports/decision_log.md` and escalate.

## Global skills to combine (invoke by name)

- `writing-plans` — locked plan header and no-placeholders standard
- `verification-before-completion` — evidence before any claim
- `subagent-driven-development` — fresh sub-agent per task step when plan has ≥3 independent tasks
- `dispatching-parallel-agents` — only for provably independent tasks (no shared schema or config)

## Project constraints

- Scope docs: `project_scope/` (gitignored — authoritative for terminology and gates).
- Hybrid mode: manual chat OK if same payload and checklist as `.cursor/commands/*.md`.
