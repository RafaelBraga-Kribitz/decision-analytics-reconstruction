# Numeric Single Source of Truth

Authoritative headline numbers for the reconstruction portfolio. When narrative
docs disagree with this table, **this table wins**. Regenerate pipeline metrics
via `scripts/generate_golden_metrics.py`; CI gates them in
`tests/test_golden_metrics.py`.

## Scale and program window

| Quantity | Canonical value | Notes |
|---|---|---|
| Production population run | **50,000** entities | Default `make pipeline-dev` / clone-local sample |
| Full-scale design reference | **4,260,816** entities | TSJE 2018 roll; design-scale narrative only |
| Dashboard demo sample | **15,000** | Streamlit subsample; not production run size |
| Program scope | **18 weeks** (full operational program) | Historical program window |
| Reconstruction pipeline window | **14 ISO weeks** (2018-W01..W14) | Only weeks with operational data in this repo; 2,772 MILP rows |
| Budget envelope (code) | **$6M USD** | `constants.py` / `budget_envelope.yaml`; sole budget figure in narrative |

## Verified outcome (TSJE 2018)

| Quantity | Series A | Series B |
|---|---|---|
| Preference margin | **+3.70 pp** (46.43% vs 42.73%) | **+3.88 pp** (48.96% vs 45.08%) |
| Outcome event date | 2018-04-22 | same |
| National participation rate | **61.25%** | same anchor family |

**63.6% participation is wrong** — use 61.25% everywhere.

## Module B solver comparator (reconstruction envelope)

Provable from `data/processed/module_b/run_manifest_baseline.json` → `baseline_comparison`:

| Comparator | Metric | Reference value |
|---|---|---|
| MILP optimized vs department-uniform naive | Linearized persuasion-proxy lift | **~54.77%** (`linearized_lift_pct_milp_vs_naive`) |
| Budget envelope | Total USD allocated | **$6,029,991** (within $6M ±0.5% gate) |

This is a **solver comparator on the reconstruction envelope**, not a verified historical causal claim about the 2018 program.

## Module A quality gates (enforced in CI)

These are **regression locks, not external-quality claims**: thresholds sit just
below values measured on the synthetic reference run, so they guarantee output
stability under the fixed seed — they do not certify model quality against any
held-out real data.

| Metric | Gate | Measured (reference run) | Do not headline |
|---|---|---|---|
| Silhouette | **> 0.22** | 0.2566 | 0.35 aspirational gate is retired |
| Bootstrap ARI | **> 0.70** (test) | 0.7615 | README 0.77 is test threshold, not measured |
| Brier (propensity) | **< 0.237** | 0.071 | 0.22 claim is wrong |
| AUC-ROC | — | 0.9679 | **Circular** (target encodes calibration anchors); never headline |

## Module B allocation grid

| Quantity | Value |
|---|---|
| Decision rows | 18 departments × 11 channels × 14 weeks = **2,772** |
| Coverage floor | **80%** department reach (enforced at export) |

## Module C MC and diagnostics

| Quantity | Value | Notes |
|---|---|---|
| MC draws (default) | 10,000 | 600 when `MC_FAST=1` |
| Scenario buckets | 3 canonical (`baseline`, `extreme_tracker`, `compounded_herd`) | equal-weight stratified sampling |
| NUTS divergences (full run) | 14 measured | **does not block** portfolio delivery; tracked in README diagnostics |
| Walk-forward coverage | sparse fixture | not "validated" on withheld real survey measurements |
| Battleground win probability (fixture posterior) | **~0.49–0.51** per department | illustrative; not a verified outcome forecast |

## Forbidden headline claims

- Causal "with/without analytics → +3.70 pp" or "underperformed by 2–4 pp" counterfactuals (unverifiable)
- Posterior tracking margin as substitute for verified +3.70 pp without "illustrative fixture survey measurements" disclaimer
- Win probability ">79%" when artifacts show ~0.49–0.51
- Any alternate historical budget figure in public narrative (use **$6M** only)
- AUC as generalization evidence
- 75% extreme-tracker draw share (legacy equal-weight misread; use live bucket counts)
- "CONFIDENTIAL program memo" fiction tone in generated briefs

## Provenance

- Anchors: `maintainer/archives/verified_calibration_anchors_full.md`, `config/calibration_anchors.yaml`
- Golden snapshot: `reports/golden_metrics.json`
- Baseline comparator: `data/processed/module_b/run_manifest_baseline.json`
