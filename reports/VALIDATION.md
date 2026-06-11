# Validation Summary

Consolidated quality gates and measured metrics. **Canonical table:**
[`NUMERIC_SSOT.md`](NUMERIC_SSOT.md). **Golden CI snapshot:**
[`golden_metrics.json`](golden_metrics.json).

## Module A

| Check | Gate | Measured | Script / test |
|---|---|---|---|
| Silhouette | > 0.22 | ~0.2566 | `test_segmentation.py` |
| Bootstrap ARI | > 0.70 | ~0.7615 | `test_segmentation.py` |
| Brier | < 0.237 | 0.071 | model card + evaluation |
| AUC | not headline | 0.9679 (circular) | documented limitation |

Department participation raking aligns aggregates to **61.25%** national anchor.

## Module B

| Check | Expected | Notes |
|---|---|---|
| Solver status | OPTIMAL | `test_golden_metrics.py` |
| Coverage floor | 80% | `check_module_b_solver_gates.py` |
| Objective identity | linear proxy = reported contacts | F-037 |

## Module C

| Check | Status | Notes |
|---|---|---|
| Outcome anchor m★ | +3.70 pp Series A | `check_module_c_outcome_anchor.py` |
| Walk-forward estimand | house offset in likelihood | F-034 |
| MC B→C handshake | alloc contacts > 0 | F-040 |
| MCMC divergences | 14 on full run | tracked; does not block delivery |
| Walk-forward coverage on fixture | sparse | not claimed as external validation |

## Pipeline integration

`make pipeline-full` runs A → B → C → EDA regeneration. Adversary verifies closed
findings via `make verify`.

## Statistical independence

Module outputs are designed for sequential decision support; correlation across
modules is documented in `epistemic_boundaries.md`. No single metric summarizes
"portfolio accuracy."
