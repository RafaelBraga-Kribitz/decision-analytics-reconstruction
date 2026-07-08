---
doc_id: DOC-REG-INDEX
doc_type: registry
doc_role: registry
visibility: public
status: generated
owner: architecture
last_reviewed: "2026-05-20"
canonical_source: null
derived_from: []
supersedes: []
tags:
  - generated
---

# Documentation index

_This file is generated from `docs/registry/docs_registry.yaml`. Do not edit by hand._

Run `poetry run python scripts/generate_doc_index.py --write` after registry changes.

## Retrieval order (agents)

1. `docs/registry/docs_registry.yaml`
2. Canonical docs (`authority: canonical`)
3. Derived views
4. Evidence (`maintainer/evidence/`)
5. Archived lineage only

## Canonically authoritative (selection)

- **DOC-GOV-CLAUDE-001** — `CLAUDE.md` — *policy* / *canonical*
- **DOC-GOV-CONTRIB-001** — `CONTRIBUTING.md` — *policy* / *canonical*
- **DOC-CHARTER-001** — `PROJECT_CHARTER.md` — *policy* / *canonical*
- **DOC-DOCS-001** — `docs/DEPLOYMENT.md` — *narrative* / *canonical*
- **DOC-GOV-AUDIT-001** — `governance/AUDIT_PROCEDURE.md` — *policy* / *canonical*
- **DOC-ROOT-002** — `governance/CHANGELOG.md` — *narrative* / *canonical*
- **DOC-DOC-001** — `governance/Truth_and_rebuild_sprint.md` — *narrative* / *canonical*
- **DOC-DOC-002** — `governance/adrs/0001-completion-sprint-cadence.md` — *narrative* / *canonical*
- **DOC-DOC-003** — `governance/chart_audit_completion_sprint.md` — *narrative* / *canonical*
- **DOC-MAINT-001** — `maintainer/AGENT_WORKFLOW_GUIDE.md` — *narrative* / *canonical*
- **DOC-MODA-001** — `module_a_population_segmentation/README.md` — *narrative* / *canonical*
- **DOC-MODA-002** — `module_a_population_segmentation/reports/model_card_propensity.md` — *narrative* / *canonical*
- **DOC-MODA-003** — `module_a_population_segmentation/reports/model_card_segmentation.md` — *narrative* / *canonical*
- **DOC-MODB-001** — `module_b_resource_allocation/SPECIFICATION.md` — *specification* / *canonical*
- **DOC-MODC-001** — `module_c_forecasting_scenarios/METHODOLOGY.md` — *methodology* / *canonical*
- **DOC-REP-SSOT-001** — `reports/NUMERIC_SSOT.md` — *registry* / *canonical*
- **DOC-REP-001** — `reports/eda/eda_report.md` — *narrative* / *canonical*
- **DOC-REP-002** — `reports/eda/strategic_brief.md` — *narrative* / *canonical*
- **DOC-EPI-001** — `reports/epistemic_boundaries.md` — *methodology* / *canonical*

## Derived portfolio views

- **DOC-GOV-AGENTS-001** — `AGENTS.md` — canonical: DOC-GOV-AUDIT-001
- **DOC-ARCH-001** — `ARCHITECTURE.md` — canonical: DOC-CHARTER-001
- **DOC-GOV-GEMINI-001** — `GEMINI.md` — canonical: DOC-GOV-AUDIT-001
- **DOC-ROOT-001** — `README.md` — canonical: DOC-CHARTER-001
- **DOC-MODB-README-001** — `module_b_resource_allocation/README.md` — canonical: DOC-MODB-001
- **DOC-MODC-README-001** — `module_c_forecasting_scenarios/README.md` — canonical: DOC-MODC-001
- **DOC-REP-VAL-001** — `reports/VALIDATION.md` — canonical: DOC-REP-SSOT-001

## Evidence and internal artifacts

- **DOC-GOV-SESSION-END-001** — `governance/SESSION_END.md` — *active*
- **DOC-MODC-002** — `module_c_forecasting_scenarios/reports/C_research_proof_table.md` — *active*

## Research inputs (reference only)


