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

## Post-publish backlog (honest roadmap)

These items are **out of scope** for the reconstruction portfolio but documented
so reviewers know the architecture's next engineering steps:

| ID | Item | Why deferred |
|---|---|---|
| A-3 | Non-circular propensity evaluation (hold-out departments, drop logit offset) | Requires new labeled holdout design; current AUC is diagnostic only |
| C-4 | Stratified Bayesian battleground model | Current dept win map is illustrative jitter on fixture posterior |
| C-10 | Monte Carlo scenarios feeding back into daily forecast | MC draws are standalone; coupling needs new PyMC state |
| B-MMM | MMM-grade empirical response curves | MILP uses piecewise-linear chords on policy caps, not fitted MMM |
| E-7 | Segment-level allocation truth in solver output | S1 chart prorates by segment share; solver is dept×channel×week |
| A-11 | `reliability_max_deviation_pp` enforcement on real model | Helper exists; gate not wired to production export |
| Scale | Full 4.26M roll + 18-week operational ingest | Pipeline models 14 ISO weeks where working data exists |

## Fresh-clone smoke (release gate)

From a clean tree after `poetry install`:

```bash
make test
make verify
poetry run python scripts/check_fresh_clone_smoke.py
```

Optional full path (slow, CPU-only): `make pipeline-full` then golden-metric gates.

`scripts/check_fresh_clone_smoke.py` verifies Makefile targets and release artifacts
without cloning; golden-metric tests skip cleanly when `data/processed/` is empty.
