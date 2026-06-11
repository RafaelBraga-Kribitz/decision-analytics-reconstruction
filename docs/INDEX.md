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
- **DOC-CAL-001** — `appendix/verified_calibration_anchors_full.md` — *registry* / *canonical*
- **DOC-DOCS-001** — `docs/DEPLOYMENT.md` — *narrative* / *canonical*
- **DOC-DOCS-002** — `docs/DEPLOYMENT_CHECKLIST.md` — *narrative* / *canonical*
- **DOC-DOCS-003** — `docs/GITHUB_ACTIONS_SETUP.md` — *narrative* / *canonical*
- **DOC-GOV-AUDIT-001** — `governance/AUDIT_PROCEDURE.md` — *policy* / *canonical*
- **DOC-GOV-CAT-001** — `governance/CATEGORIES.md` — *policy* / *canonical*
- **DOC-ROOT-002** — `governance/CHANGELOG.md` — *narrative* / *canonical*
- **DOC-GOV-DEBT-001** — `governance/DEBT_TOOLS.md` — *policy* / *canonical*
- **ADR-0002** — `governance/adrs/0002-tech-debt-ratchet.md` — *policy* / *canonical*
- **ADR-0003** — `governance/adrs/0003-charter-line-budget.md` — *policy* / *canonical*
- **DOC-MAINT-001** — `maintainer/pre_public_cleanup_manifest.md` — *policy* / *canonical*
- **DOC-MODA-001** — `module_a_population_segmentation/README.md` — *narrative* / *canonical*
- **DOC-MODA-002** — `module_a_population_segmentation/reports/audit_report_module_a_2026-05-11.md` — *narrative* / *canonical*
- **DOC-MODA-003** — `module_a_population_segmentation/reports/model_card_propensity.md` — *narrative* / *canonical*
- **DOC-MODA-004** — `module_a_population_segmentation/reports/model_card_segmentation.md` — *narrative* / *canonical*
- **DOC-MODA-005** — `module_a_population_segmentation/reports/segment_action_matrix.md` — *narrative* / *canonical*
- **DOC-MODB-001** — `module_b_resource_allocation/SPECIFICATION.md` — *specification* / *canonical*
- **DOC-MODC-001** — `module_c_forecasting_scenarios/METHODOLOGY.md` — *methodology* / *canonical*
- **DOC-REP-001** — `reports/baseline_comparison.md` — *narrative* / *canonical*
- **DOC-BIZ-001** — `reports/business_case.md` — *narrative* / *canonical*
- **DOC-REP-002** — `reports/cluster_validation.md` — *narrative* / *canonical*
- **DOC-REP-003** — `reports/data_lineage.md` — *narrative* / *canonical*
- **DOC-DLOG-001** — `reports/decision_log.md` — *narrative* / *canonical*
- **DOC-REP-004** — `reports/eda/eda_report.md` — *narrative* / *canonical*
- **DOC-REP-005** — `reports/eda/strategic_brief.md` — *narrative* / *canonical*
- **DOC-EPI-001** — `reports/epistemic_boundaries.md` — *methodology* / *canonical*
- **DOC-REP-006** — `reports/feature_engineering_justification.md` — *narrative* / *canonical*
- **DOC-REP-007** — `reports/integration_audit_2026-05-12.md` — *narrative* / *canonical*
- **DOC-REP-008** — `reports/module_b_module_c_handshake.md` — *narrative* / *canonical*
- **DOC-REP-009** — `reports/reproducibility_validation.md` — *narrative* / *canonical*
- **DOC-REP-010** — `reports/stakeholder_scenario_table.md` — *narrative* / *canonical*
- **DOC-REP-011** — `reports/statistical_independence_note.md` — *narrative* / *canonical*
- **DOC-REP-012** — `reports/statistical_metrics_summary.md` — *narrative* / *canonical*
- **DOC-WALK-001** — `reports/system_walkthrough.md` — *walkthrough* / *canonical*
- **DOC-REP-013** — `reports/transformation_log.md` — *narrative* / *canonical*
- **DOC-SCH-001** — `schema_contracts/README.md` — *specification* / *canonical*
- **DOC-TST-001** — `tests/README.md` — *narrative* / *canonical*
- **DOC-TST-002** — `tests/REPRODUCIBILITY.md` — *narrative* / *canonical*

## Derived portfolio views

- **DOC-GOV-AGENTS-001** — `AGENTS.md` — canonical: DOC-GOV-AUDIT-001
- **DOC-ARCH-001** — `ARCHITECTURE.md` — canonical: DOC-CHARTER-001
- **DOC-GOV-GEMINI-001** — `GEMINI.md` — canonical: DOC-GOV-AUDIT-001
- **DOC-ROOT-001** — `README.md` — canonical: DOC-CHARTER-001
- **DOC-MODB-README-001** — `module_b_resource_allocation/README.md` — canonical: DOC-MODB-001
- **DOC-MODB-002** — `module_b_resource_allocation/reports/response_curve_spec.md` — canonical: DOC-MODB-001
- **DOC-MODC-README-001** — `module_c_forecasting_scenarios/README.md` — canonical: DOC-MODC-001
- **DOC-MODCRS-001** — `module_c_forecasting_scenarios/reports/research/exit_bias_mechanisms.md` — canonical: DOC-MODC-001
- **DOC-MODCRS-002** — `module_c_forecasting_scenarios/reports/research/oea_eu_survey_release_metadata.md` — canonical: DOC-MODC-001
- **DOC-MODCRS-003** — `module_c_forecasting_scenarios/reports/research/tsje_calibration_sources.md` — canonical: DOC-MODC-001
- **DOC-BIZ-005** — `reports/HIRING_CONTEXT.md` — canonical: DOC-BIZ-001
- **DOC-BIZ-002** — `reports/case_study_business.md` — canonical: DOC-BIZ-001
- **DOC-BIZ-003** — `reports/case_study_technical.md` — canonical: DOC-CHARTER-001, DOC-EPI-001
- **DOC-BIZ-004** — `reports/competitive_positioning.md` — canonical: DOC-BIZ-001
- **DOC-DICT-001** — `reports/data_dictionary.md` — canonical: DOC-SCH-001, DOC-CHARTER-001
- **DOC-WALK-002** — `reports/executive_demo_walkthrough.md` — canonical: DOC-WALK-001
- **DOC-RPT-010** — `reports/model_hierarchy.md` — canonical: DOC-CHARTER-001
- **DOC-RPT-011** — `reports/module_a_model_io_spec.md` — canonical: DOC-SCH-001, DOC-CHARTER-001
- **DOC-RPT-012** — `reports/module_b_optimization_formulation.md` — canonical: DOC-MODB-001
- **DOC-RPT-013** — `reports/module_c_forecast_validation.md` — canonical: DOC-MODC-001

## Evidence and internal artifacts

- **DOC-GOV-SESSION-END-001** — `governance/SESSION_END.md` — *active*
- **DOC-EVID-001** — `maintainer/evidence/qa_gatekeeper_verdict_evaluation_gap_2026-05-12.md` — *archived*
- **DOC-EVID-002** — `maintainer/evidence/qa_gatekeeper_verdict_portfolio_360_2026-05-12.md` — *archived*
- **DOC-EVID-003** — `maintainer/evidence/task_verify_architecture_quality_pipeline_dev_acceptance_2026-05-12.md` — *archived*
- **DOC-EVID-004** — `maintainer/evidence/task_verify_architecture_quality_task1_2026-05-12.md` — *archived*
- **DOC-EVID-005** — `maintainer/evidence/task_verify_architecture_quality_task2_module_a_2026-05-13.md` — *archived*
- **DOC-EVID-006** — `maintainer/evidence/task_verify_architecture_quality_task3_module_b_2026-05-14.md` — *archived*
- **DOC-EVID-007** — `maintainer/evidence/task_verify_architecture_quality_task4_module_c_2026-05-14.md` — *archived*
- **DOC-EVID-008** — `maintainer/evidence/task_verify_architecture_quality_task5_contracts_2026-05-15.md` — *archived*
- **DOC-EVID-009** — `maintainer/evidence/task_verify_architecture_quality_task6_makefile_2026-05-12.md` — *archived*
- **DOC-EVID-010** — `maintainer/evidence/task_verify_architecture_quality_task7_ci_make_test_2026-05-12.md` — *archived*
- **DOC-EVID-011** — `maintainer/evidence/task_verify_architecture_quality_task8_architecture_md_2026-05-12.md` — *archived*
- **DOC-EVID-012** — `maintainer/evidence/task_verify_architecture_quality_task9_data_gitkeep_2026-05-12.md` — *archived*
- **DOC-EVID-013** — `maintainer/evidence/task_verify_business_framing_2026-05-12.md` — *archived*
- **DOC-EVID-014** — `maintainer/evidence/task_verify_data_science_framing_2026-05-12.md` — *archived*
- **DOC-EVID-015** — `maintainer/evidence/task_verify_evaluation_gap_2026-05-12.md` — *archived*
- **DOC-EVID-016** — `maintainer/evidence/task_verify_portfolio_360_2026-05-12.md` — *archived*
- **DOC-EVID-017** — `maintainer/evidence/verification_session_proof_2026-05-12.md` — *archived*
- **DOC-MODC-002** — `module_c_forecasting_scenarios/reports/C_research_proof_table.md` — *active*

## Research inputs (reference only)


