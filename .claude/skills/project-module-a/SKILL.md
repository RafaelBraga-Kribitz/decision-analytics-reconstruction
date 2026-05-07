---
name: project-module-a
description: Population modeling, segmentation, propensity — Module A. Use for synthetic generation, IPF/raking, cleaning pipeline, DBSCAN/KMeans, logistic+Platt, Streamlit. Embeds TDD iron law and DAMA data quality standard.
disable-model-invocation: true
---

# Project Module A

## Non-negotiable order of operations

```
1. Preflight:  DAMA-5 audit on inputs → calibration anchor check → terminology scan
2. TDD:        Failing test first → minimal implementation → verify green
3. Validate:   Run all A1–A12 gates from module-a-specialist.md Phase 3
4. Evidence:   QA report + test output + gate mapping before /task-verify
```

## Required reading
- `project_scope/scope_module_A_population_modeling_and_segmentation.md`
- `module_a_population_segmentation/config/calibration_anchors.yaml` (when present)

## Global skills — invoke in this order

1. `data-science/skills/02-data/data-quality-audit` — run DAMA-5 scorecard first; use project-specific thresholds in Phase 1 above (not generic thresholds).
2. `test-driven-development` — TDD iron law applies to every `src/` change.
3. `scikit-learn` — modeling implementation reference.
4. `shap` — permutation importance + LinearExplainer on 10k-entity sample (required for propensity model deliverable).
5. `systematic-debugging` — for any test failure or unexpected behavior; 4 phases before proposing fixes.
6. `verification-before-completion` — gate function before every completion claim.

## Block conditions

- Calibration anchor outside tolerance → do not proceed to modeling; fix generation/raking parameters first.
- `QAGateFailure` raised by `validator.py` → pipeline halted; document in transformation log before reopening.
- Brier score ≥ 0.22 or fails to beat stratified baseline → do not mark propensity model task complete.
- Silhouette < 0.35 or ARI < 0.80 → do not mark segmentation task complete.
- Banned terminology found in field names or user-facing strings → fix before completion.

## Quantitative acceptance summary

| Metric | Target | Source |
|--------|--------|--------|
| Municipality post-clean null rate | < 0.1% | Scope §4.3 step 8 |
| DBSCAN noise rate | < 1% | Scope §7.1 |
| K-Means mean silhouette (k=6) | > 0.35 | Scope §7.2 |
| Bootstrap mean ARI | > 0.80 | Scope §7.2 |
| Propensity AUC-ROC | > 0.70 | Scope §7.3 |
| Propensity Brier score | < 0.22 | Scope §7.3 |
| Reliability diagram max deviation | < 3 pp per decile | Scope §7.3 |
| National mean propensity | 61.25% ±0.1 pp | Scope §7.3 |
