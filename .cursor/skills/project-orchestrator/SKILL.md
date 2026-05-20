---
doc_id: DOC-CURSOR-001
doc_type: policy
doc_role: canonical
visibility: internal
status: active
owner: harness
last_reviewed: '2026-05-20'
canonical_source: null
derived_from: null
supersedes: null
tags: []
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
- **Transaction boundary:** every dispatched **implementation** turn names one **`UNIT_ID`**; after **`/task-transaction`** the session **stops** — next unit needs a new `/task-execute`. Plan must list **`unit_impact_set`** and operators keep **`.cursor/runtime/current_unit.json`** current. Discovered work → **`maintainer/agent_transaction_backlog.md`** (never expand the active unit). Rule: `.cursor/rules/10-transaction-boundaries.mdc`.
- **Pre-public / portfolio:** keep `maintainer/pre_public_cleanup_manifest.md` updated whenever internal-only or AI-visible artifacts appear; orchestrate a final cleanup task from that manifest before external release (.cursor/rules/07-pre-public-cleanup-manifest.mdc).

## Documentation registry (machine-readable)

- Inventory SSOT lives in **`docs/registry/docs_registry.yaml`**; navigation view is regenerated into **`docs/INDEX.md`**.
- Retrieval precedence: **`registry → canonical (`authority: canonical`) → derived → evidence (`maintainer/evidence/`) → archive-only lineage`** (.cursor/rules/09-documentation-registry-governance.mdc).
- Preserve immutable **`doc_id`** values whenever files move paths.
