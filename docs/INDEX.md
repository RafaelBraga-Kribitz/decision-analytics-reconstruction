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
- **DOC-DOCS-003** — `docs/agents/AGENTS.md` — *narrative* / *canonical*
- **DOC-DOCS-004** — `docs/agents/GEMINI.md` — *narrative* / *canonical*
- **DOC-GOV-AUDIT-001** — `governance/AUDIT_PROCEDURE.md` — *policy* / *canonical*
- **DOC-ROOT-002** — `governance/CHANGELOG.md` — *narrative* / *canonical*
- **DOC-DOC-001** — `governance/Truth_and_rebuild_sprint.md` — *narrative* / *canonical*
- **DOC-DOC-002** — `governance/adrs/0001-completion-sprint-cadence.md` — *narrative* / *canonical*
- **DOC-DOC-003** — `governance/chart_audit_completion_sprint.md` — *narrative* / *canonical*
- **DOC-DOC-004** — `governance/improvement_plan/IMP-A01_propensity-honesty.md` — *narrative* / *canonical*
- **DOC-DOC-005** — `governance/improvement_plan/IMP-A02_categorical-encoding.md` — *narrative* / *canonical*
- **DOC-DOC-006** — `governance/improvement_plan/IMP-A03_cluster-selection-gates.md` — *narrative* / *canonical*
- **DOC-DOC-007** — `governance/improvement_plan/IMP-A04_cleaner-injector-integrity.md` — *narrative* / *canonical*
- **DOC-DOC-008** — `governance/improvement_plan/IMP-A05_fixed-reference-scaling.md` — *narrative* / *canonical*
- **DOC-DOC-009** — `governance/improvement_plan/IMP-A06_config-doc-parity.md` — *narrative* / *canonical*
- **DOC-DOC-010** — `governance/improvement_plan/IMP-B01_allocation-parameter-provenance.md` — *narrative* / *canonical*
- **DOC-DOC-011** — `governance/improvement_plan/IMP-B02_uncertainty-ingestion.md` — *narrative* / *canonical*
- **DOC-DOC-012** — `governance/improvement_plan/IMP-B03_milp-robustness-contracts.md` — *narrative* / *canonical*
- **DOC-DOC-013** — `governance/improvement_plan/IMP-B04_silent-substitution.md` — *narrative* / *canonical*
- **DOC-DOC-014** — `governance/improvement_plan/IMP-C01_mcmc-convergence-gates.md` — *narrative* / *canonical*
- **DOC-DOC-015** — `governance/improvement_plan/IMP-C02_model-spec-priors-phi.md` — *narrative* / *canonical*
- **DOC-DOC-016** — `governance/improvement_plan/IMP-C03_report-computed-integrity.md` — *narrative* / *canonical*
- **DOC-DOC-017** — `governance/improvement_plan/IMP-C04_shock-herding-calibration.md` — *narrative* / *canonical*
- **DOC-DOC-018** — `governance/improvement_plan/IMP-C05_geo-uncertainty-integrity.md` — *narrative* / *canonical*
- **DOC-DOC-019** — `governance/improvement_plan/IMP-C06_small-sample-honesty.md` — *narrative* / *canonical*
- **DOC-DOC-020** — `governance/improvement_plan/IMP-C07_contract-enforcement.md` — *narrative* / *canonical*
- **DOC-DOC-021** — `governance/improvement_plan/IMP-C08_mc-stratification.md` — *narrative* / *canonical*
- **DOC-DOC-022** — `governance/improvement_plan/IMP-V01_visual-system.md` — *narrative* / *canonical*
- **DOC-DOC-023** — `governance/improvement_plan/IMP-V02_chart-single-sourcing.md` — *narrative* / *canonical*
- **DOC-DOC-024** — `governance/improvement_plan/IMP-V03_shap-provenance.md` — *narrative* / *canonical*
- **DOC-DOC-025** — `governance/improvement_plan/IMP-V04_reliability-standard.md` — *narrative* / *canonical*
- **DOC-DOC-026** — `governance/improvement_plan/IMP-V05_residual-encodings.md` — *narrative* / *canonical*
- **DOC-DOC-027** — `governance/improvement_plan/IMP-V06_dashboard-parity.md` — *narrative* / *canonical*
- **DOC-DOC-028** — `governance/improvement_plan/INDEX.md` — *narrative* / *canonical*
- **DOC-DOC-029** — `governance/improvement_plan/TEMPLATE.md` — *narrative* / *canonical*
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
- **DOC-REP-003** — `reports/module_a/k_sweep_2026-07-09.md` — *narrative* / *canonical*

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
- **DOC-MODC-004** — `module_c_forecasting_scenarios/reports/phi_sensitivity.md` — *active*
- **DOC-MODC-003** — `module_c_forecasting_scenarios/reports/shock_herding_sensitivity.md` — *active*
- **DOC-REF-GEO-ADM1-001** — `module_c_forecasting_scenarios/src/module_c_forecasting_scenarios/geo/paraguay_departments.SOURCE.md` — *active*
- **DOC-MODC-006** — `reports/module_c/battleground_investigation/INVESTIGATION_REPORT.md` — *active*
- **DOC-MODC-007** — `reports/module_c/battleground_investigation/scratch/battleground/anchor_comparison.md` — *active*
- **DOC-MODC-005** — `reports/module_c/walk_forward_loo_report.md` — *active*

## Research inputs (reference only)


