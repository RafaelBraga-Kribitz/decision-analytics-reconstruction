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

- **DOC-CLAUDE-001** — `.claude/skills/project-orchestrator/SKILL.md` — *policy* / *canonical*
- **DOC-CURSOR-001** — `.cursor/skills/project-orchestrator/SKILL.md` — *policy* / *canonical*
- **DOC-ARCH-001** — `ARCHITECTURE.md` — *specification* / *canonical*
- **DOC-ROOT-002** — `CHANGELOG.md` — *narrative* / *canonical*
- **DOC-PLAN-001** — `IMPLEMENTATION_PLAN.md` — *execution* / *canonical*
- **DOC-ROOT-001** — `README.md` — *narrative* / *canonical*
- **DOC-CAL-001** — `appendix/verified_calibration_anchors_full.md` — *registry* / *canonical*
- **DOC-DOCS-001** — `docs/DEPLOYMENT.md` — *narrative* / *canonical*
- **DOC-DOCS-002** — `docs/DEPLOYMENT_CHECKLIST.md` — *narrative* / *canonical*
- **DOC-DOCS-003** — `docs/GITHUB_ACTIONS_SETUP.md` — *narrative* / *canonical*
- **DOC-HARNESS-001** — `docs/ai_harness/CONTROLLED_WORKFLOW_PLAYBOOK.md` — *policy* / *canonical*
- **DOC-HARNESS-002** — `docs/ai_harness/README.md` — *policy* / *canonical*
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

- **DOC-PLAN-010** — `ROADMAP.md` — canonical: DOC-PLAN-001
- **DOC-PLAN-011** — `TASK_REFERENCE.md` — canonical: DOC-PLAN-001
- **DOC-MODB-002** — `module_b_resource_allocation/reports/response_curve_spec.md` — canonical: DOC-MODB-001
- **DOC-MODCRS-001** — `module_c_forecasting_scenarios/reports/research/exit_bias_mechanisms.md` — canonical: DOC-MODC-001
- **DOC-MODCRS-002** — `module_c_forecasting_scenarios/reports/research/oea_eu_survey_release_metadata.md` — canonical: DOC-MODC-001
- **DOC-MODCRS-003** — `module_c_forecasting_scenarios/reports/research/tsje_calibration_sources.md` — canonical: DOC-MODC-001
- **DOC-BIZ-005** — `reports/HIRING_CONTEXT.md` — canonical: DOC-BIZ-001
- **DOC-BIZ-002** — `reports/case_study_business.md` — canonical: DOC-BIZ-001
- **DOC-BIZ-003** — `reports/case_study_technical.md` — canonical: DOC-ARCH-001, DOC-EPI-001
- **DOC-BIZ-004** — `reports/competitive_positioning.md` — canonical: DOC-BIZ-001
- **DOC-DICT-001** — `reports/data_dictionary.md` — canonical: DOC-SCH-001, DOC-ARCH-001
- **DOC-WALK-002** — `reports/executive_demo_walkthrough.md` — canonical: DOC-WALK-001
- **DOC-RPT-010** — `reports/model_hierarchy.md` — canonical: DOC-ARCH-001
- **DOC-RPT-011** — `reports/module_a_model_io_spec.md` — canonical: DOC-SCH-001, DOC-ARCH-001
- **DOC-RPT-012** — `reports/module_b_optimization_formulation.md` — canonical: DOC-MODB-001
- **DOC-RPT-013** — `reports/module_c_forecast_validation.md` — canonical: DOC-MODC-001

## Evidence and internal artifacts

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

- **DOC-RES-001** — `notebooklm-sources-2026-05-14/Analysis_of_Digital_Advertising_Performance_Metrics_in_Latin_America_A_Historical_Review_of_Q1_2018_.md`
- **DOC-RES-002** — `notebooklm-sources-2026-05-14/Comprehensive_Analysis_of_Electorate_Distribution_and_Voter_Participation_in_the_2018_Paraguayan_Gen.md`
- **DOC-RES-003** — `notebooklm-sources-2026-05-14/Digital_Transformation_in_the_Southern_Cone_An_Exhaustive_Analysis_of_Paraguay’s_Digital_Landscape_i.md`
- **DOC-RES-004** — `notebooklm-sources-2026-05-14/Macroeconomic_Analysis_of_the_Paraguayan_Guaraní_Daily_Exchange_Rate_Dynamics_and_the_Institutional_.md`
- **DOC-RES-005** — `notebooklm-sources-2026-05-14/Paraguayan_Exchange_Rate_Dynamics_A_Comprehensive_Analysis_of_Retail_Spreads_and_Interbank_Benchmark.md`
- **DOC-RES-006** — `notebooklm-sources-2026-05-14/Psephological_Divergence_and_the_Structural_Dynamics_of_the_2018_Paraguayan_Presidential_Election_A_.md`
- **DOC-RES-007** — `notebooklm-sources-2026-05-14/Socioeconomic_Structural_Analysis_of_Unsatisfied_Basic_Needs_in_Paraguay_A_Comprehensive_Evaluation_.md`
- **DOC-RES-008** — `notebooklm-sources-2026-05-14/Technical_Assessment_of_the_Paraguayan_Road_Infrastructure_National_Inventory,_Departmental_Distribu.md`
- **DOC-RES-009** — `notebooklm-sources-2026-05-14/The_2018_Presidential_Campaign_of_the_Asociación_Nacional_Republicana_An_Exhaustive_Analysis_of_Fina.md`
- **DOC-RES-010** — `notebooklm-sources-2026-05-14/The_Digital_Architecture_of_Paraguay_A_Multi-Dimensional_Analysis_of_ICT_Penetration_and_Socio-Techn.md`
- **DOC-RES-011** — `notebooklm-sources-2026-05-14/notebooklm-chat-currently-facebook-ads-ch-facebook-ads-is-alrea-2026-05-14.md`
- **DOC-RES-012** — `notebooklm-sources-2026-05-14/notebooklm-note-enterprise-analytics-and-political-modeling-glossa-2026-05-14.md`
- **DOC-RES-013** — `notebooklm-sources-2026-05-14/notebooklm-note-the-paraguay-2018-model-data-integration-and-valid-2026-05-14.md`

