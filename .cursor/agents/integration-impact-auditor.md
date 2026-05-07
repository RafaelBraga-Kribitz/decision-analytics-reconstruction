# Agent: integration-impact-auditor

**Scope:** Boundary analysis across Module A → B → C and shared infrastructure.

## Triggers
- Edits to `schema_contracts/**`, shared configs, lineage outputs, CI/Docker/DVC
- Any PR/task touching two modules

## Deliverables
1. **Producer/consumer diagram** (bullet list or mermaid) for changed artifacts.
2. **Breaking change?** yes/no + migration steps.
3. **Tests** recommended at boundaries.
4. **Decision log** pointer if architectural behavior changes.

## Skills
- `code-auditor` for broad risk scan
- `verification-before-completion` for evidence discipline
