# Validation Summary

Consolidated quality gates and measured metrics. **Canonical table:**
[`NUMERIC_SSOT.md`](NUMERIC_SSOT.md). **Golden CI snapshot:**
[`golden_metrics.json`](golden_metrics.json).

## Module A

| Check | Gate | Measured | Script / test |
|---|---|---|---|
| Silhouette | > 0.22 | 0.2562 (50k; 0.2689 @15k) | `test_segmentation.py` |
| Bootstrap ARI | ≥ 0.40 (50k; 0.50 test floor) | 0.4304 (50k; 0.5418 @15k) | `test_segmentation.py` (canonical `compute_bootstrap_ari`, IMP-A03/#55) |
| Brier | < 0.237 | 0.1185 (15k holdout; 0.1212 @50k) | model card + evaluation |
| AUC | not headline | ≈0.89 (0.8907, circular) | documented limitation |

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
| MCMC divergences | 0 on full run (v0.4 non-centered) | enforced: slow-lane tests fail on any divergence |
| Walk-forward coverage on fixture | sparse | not claimed as external validation |
| LOWO out-of-sample (8 real waves) | mean log-score −4.54; 94% HDI coverage 6/8 | `reports/module_c_lowo_metrics.json`; reduced-draw sampler disclosed below; n=8 caveat |

### Leave-one-wave-out (LOWO) validation — first out-of-sample number (issue #97)

**Method.** For each of the 8 real tracking waves in
`module_c_forecasting_scenarios/tests/fixtures/polls_raw_fixture.csv`, the
hierarchical tracking model is refit on the other 7 waves and the held-out
wave's observed margin is scored against the model's posterior predictive at
that wave's field-window midpoint (`mu_margin[day] + house_offset[pollster] +
Normal(0, sigma_obs(phi))` — the same generative mean and noise the likelihood
assigns to a poll). Log-score is the Gaussian log predictive density of the
observed margin under the predictive draws; coverage uses the model's 94% HDI.
Implementation: `module_c_forecasting_scenarios/.../validation/leave_one_wave_out.py`.

**Model variant scored.** `c_tracking_hierarchical_v0.4` on the **unanchored**
likelihood path (`m_star_pp=None`): the verified TSJE outcome margin (+3.70 pp
Series A) never enters any fold's fit — anchored fits are retrodictions, not
forecasts (F-069). Enforced by `test_lowo_never_anchors_on_outcome`.

**Sampler (disclosed reduced-draw config).** 4 chains × 300 draws / 300 tune,
`target_accept` 0.95, `random_seed` 42, predictive seed 20180422 — i.e. the
MC_FAST base widened via explicit CLI overrides. The preferred full-NUTS v0.4
gates (4 × 1000/1000, `target_accept` 0.99, `max_treedepth` 15) exceeded a
practical runtime budget in the CI-class environment used for this run (no C
compiler: PyTensor pure-Python mode, > 10 min per fold); on a machine with a
compiler, drop `MC_FAST` and the `--chains/--draws/--tune` flags to reproduce
under full gates. Per-fold sampler quality is reported below: 0 divergences on
all 8 fits; max R̂ 1.015–1.021 (marginally above the aspirational 1.01
full-NUTS gate — a consequence of the reduced budget); min bulk ESS ≥ 296.

| Wave | Date | Observed (pp) | Pred. mean (pp) | 94% HDI (pp) | Log-score | Covered | max R̂ | min ESS | Div. |
|---|---|---|---|---|---|---|---|---|---|
| `wave_capli_20180201` | 2018-02-01 | +13.20 | +20.53 | [−8.44, +45.28] | −3.715 | yes | 1.020 | 296 | 0 |
| `wave_capli_20180301` | 2018-03-01 | +31.20 | +16.73 | [−7.38, +40.10] | −4.106 | yes | 1.019 | 393 | 0 |
| `wave_ati_20180315` | 2018-03-15 | −4.50 | +24.47 | [+6.37, +45.45] | −7.082 | no | 1.021 | 604 | 0 |
| `wave_ica_20180318` | 2018-03-18 | +31.40 | +13.11 | [−6.02, +32.25] | −4.855 | yes | 1.018 | 346 | 0 |
| `wave_ecodat_20180326` | 2018-03-26 | +26.43 | +16.63 | [−1.39, +36.51] | −3.706 | yes | 1.016 | 421 | 0 |
| `wave_capli_20180406` | 2018-04-06 | +31.50 | +20.14 | [−1.53, +42.49] | −3.852 | yes | 1.015 | 371 | 0 |
| `wave_grau_20180410` | 2018-04-10 | +25.11 | +14.86 | [−2.70, +35.19] | −3.746 | yes | 1.017 | 494 | 0 |
| `wave_ati_20180418` | 2018-04-18 | −5.12 | +17.16 | [−1.22, +41.59] | −5.244 | no | 1.021 | 500 | 0 |

**Aggregate:** mean predictive log-score **−4.54**; 94% HDI coverage **6/8
(75%)**. Total sampling time ≈ 28 minutes (1,655 s over 8 fits).

**n = 8 caveat (read before citing).** This is out-of-sample predictive
performance on 8 waves of a single election — it is **not** validated
forecasting skill. With 8 folds, coverage can only take values k/8, and the
binomial noise on 6/8 vs a 94% target is large; the log-score is a point
estimate with no meaningful sampling distribution at this n. What the number
does establish: the unanchored tracking model, fit on 7 real waves, produces
predictive intervals wide enough to contain most withheld real waves, and its
two misses are both `ati_snead` waves — the only pollster whose margins
favored candidate B, sitting 20–30 pp from every other house. LOWO surfaces
the cost of treating a systematically divergent house as exchangeable noise.

**Reproduce** (deterministic; identical numbers up to runtime):

```bash
MC_FAST=1 poetry run python -m module_c_forecasting_scenarios.pipeline.run_lowo \
  --raw-csv module_c_forecasting_scenarios/tests/fixtures/polls_raw_fixture.csv \
  --out-dir data/processed/module_c/lowo \
  --summary-json reports/module_c_lowo_metrics.json \
  --chains 4 --draws 300 --tune 300
```

or `make module-c-lowo`. The committed artifact is
[`module_c_lowo_metrics.json`](module_c_lowo_metrics.json).

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
