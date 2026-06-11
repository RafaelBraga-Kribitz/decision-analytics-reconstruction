# Stakeholder scenario table — who asks what?

Maps three decision-maker archetypes (field operations, analytics leadership, finance) to the concerns they probe and **where this repository answers** them. Roles are illustrative; terminology follows project scope (**entity**, **population dataset**, **participation rate**, **preference proxy**, **outcome event**, **survey measurement** / measurement firm).

| Persona | Primary worry | How the system answers | Artifact / command |
|---------|---------------|------------------------|---------------------|
| **Field operations director** (“Did we saturate feasible reach where it persuades?”) | Geographic equity vs efficiency; feasibility of bilateral vs broadcast workloads; routing friction | Segment-level reach proxies and cleanliness gate drive who is targetable before spend lands in Module B MILP schedules | Module A dashboard — `make dashboard` → `module_a_population_segmentation/app/streamlit_dashboard.py`; parquet exports referenced in README |
| **Commercial / marketing analytics lead** (“Which segments move the needle; what shifts weekly?”) | Interpretable clusters + propensity; comparability vs naive baselines; scenario timing | Population modeling + logistic propensity narratives with calibration visuals; README benchmark anchors to model cards | Model cards [`module_a_population_segmentation/reports/model_card_propensity.md`](../module_a_population_segmentation/reports/model_card_propensity.md), segmentation card sibling; notebooks under `module_a_population_segmentation/notebooks/` |
| **Chief financial officer (“CFO”) counterpart** (“Prove ROI discipline vs spreadsheets; quantify downside shocks.”) | Budget envelope integrity, naive vs optimized spend, truncation shocks, FX / participation risks | MILP manifests with **dual / expansion curves** plus `baseline_comparison` (department-uniform naive vs MILP); published business framing | [`reports/business_case.md`](business_case.md); `make module-b-allocate` / `make module-b-allocate-sensitivity` → `data/processed/module_b/run_manifest_baseline.json`, `budget_expansion_curve_baseline.csv`; [`reports/epistemic_boundaries.md`](epistemic_boundaries.md) |

## Cross-cutting pointers

| Question | Redirect |
|-----------|----------|
| “Walk me end-to-end for one entity row.” | [`reports/system_walkthrough.md`](system_walkthrough.md) |
| “What is illustrative vs calibrated?” | [`reports/epistemic_boundaries.md`](epistemic_boundaries.md) |
| “Operational truth vs thesis?” | [`reports/decision_log.md`](decision_log.md) |
