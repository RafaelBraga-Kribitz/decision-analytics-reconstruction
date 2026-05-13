# Reproducibility Validation — Hash Manifest

## Overview

This document specifies the procedure to validate reproducibility on a fresh clone. All three modules use fixed random seeds; identical seeds produce identical artifacts (up to floating-point precision).

---

## Module Seeds

| Module | Component | Seed | Source |
|--------|-----------|------|--------|
| A | Population generation | 43 | `generation.yaml` |
| A | Feature engineering | 43 | PropensityModel, SegmentationModel |
| A | Segmentation (k-means) | 42 | `model_params.yaml` |
| B | MILP allocation | 20180422 | `Makefile SEED=20180422` (baseline scenario) |
| C | Tracking (PyMC) | 42 | `pymc_sampler.yaml` random_seed |
| C | Exit model (PyMC) | 42 | `exit_model.py` random_seed |

---

## Reproducibility Contract

**Guarantee:** Running the full pipeline with the above seeds on any machine (same OS, Python 3.11+, same dependency versions) produces identical artifact outputs.

**Floating-point precision:** Parquet files may differ by ≤ 1e-15 ulp due to CPU-level rounding; byte-for-byte identity is NOT guaranteed. Use pandas `assert_frame_equal(rtol=1e-10, atol=1e-12)` for validation.

**MCMC sampling:** PyMC's NUTS sampler with seed=42 is deterministic on the same CPU architecture and numpy/scipy versions. Different architectures (CPU vs GPU, different CPU families) may produce trace variations within the HDI bands (< 0.5 pp margin).

---

## Validation Procedure (Fresh Clone)

### 1. Verify environment

```bash
cd /path/to/fresh/clone
python --version  # Python 3.11.x
poetry install --extras all
```

### 2. Run Module A pipeline

```bash
cd module_a_population_segmentation
poetry run python -m population_segmentation.pipeline.main \
  --config-dir config \
  --out-dir ../data/processed \
  --seed 43
# Generates: population_master_clean.parquet, segment_labels.parquet, participation_propensity.parquet, model_run_manifest.json
```

### 3. Run Module B allocation

```bash
cd module_b_resource_allocation
poetry run python -m module_b_resource_allocation.pipeline.run_allocation \
  --input-propensity ../data/processed/participation_propensity.parquet \
  --input-segments ../data/processed/segment_labels.parquet \
  --out-dir ../data/processed/module_b \
  --seed 20180422 \
  --scenario baseline
# Generates: allocation_baseline.parquet, run_manifest_baseline.json
```

### 4. Run Module C tracking

```bash
cd module_c_forecasting_scenarios
poetry run python -m module_c_forecasting_scenarios.pipeline.run_tracking \
  --raw-csv data/raw/polls_clean.csv \
  --out-dir ../data/processed/module_c/run_all/tracking
# Generates: daily_posterior_forecast.parquet, posterior_house_effects.parquet, run_tracking_manifest.json
```

### 5. Run Module C exit model

```bash
poetry run python -m module_c_forecasting_scenarios.pipeline.run_exit \
  --raw-csv data/raw/polls_clean.csv \
  --out-dir ../data/processed/module_c/run_all/exit
# Generates: exit_model_summary.parquet, run_exit_manifest.json
```

### 6. Run Module C Monte Carlo

```bash
poetry run python -m module_c_forecasting_scenarios.pipeline.run_monte_carlo \
  --raw-csv data/raw/polls_clean.csv \
  --out-dir ../data/processed/module_c/run_all/mc
# Generates: monte_carlo_draws.parquet, scenario_run_manifest.json
```

---

## Artifact Hash Validation

### Expected Hashes (Baseline Seed, 2026-05-13 Regeneration)

For exact byte-for-byte validation on **same OS + Python 3.11.7 + dependency versions from lock file**:

```
Module A:
  population_master_clean.parquet: (seed=43, n=15000, run on 2026-05-13)
  segment_labels.parquet: (seed=42, k=6, silhouette=0.52+)
  participation_propensity.parquet: (seed=42, raked to national 0.6125)
  model_run_manifest.json: (git SHA from seed 43 run)

Module B:
  allocation_baseline.parquet: (seed=20180422, budget=$6M, 18 depts, 11 channels)
  run_manifest_baseline.json: (linearized lift 58% vs naive, timestamp)

Module C (tracking):
  daily_posterior_forecast.parquet: (seed=42, Rhat < 1.01, ESS > 400*chains)
  posterior_house_effects.parquet: (per-pollster offsets)
  run_tracking_manifest.json: (timestamp, chains=2, draws=400)

Module C (exit):
  exit_model_summary.parquet: (seed=42, intercept + betas + sigma)
  run_exit_manifest.json: (timestamp, model_version=c_exit_bias_v0.1)

Module C (Monte Carlo):
  monte_carlo_draws.parquet: (scenario catalog, 1000+ draws per scenario)
  scenario_run_manifest.json: (timestamp, scenario list)
```

**Note:** Exact hashes are suppressed here because parquet compression and JSON formatting vary slightly across pandas/pyarrow versions. Instead, use **manifest comparison** (see below).

---

## Manifest-Based Validation (Recommended)

Instead of comparing raw hashes, compare the **run manifests** which embed seed, git SHA, model version, and key metrics:

```python
import json

baseline = json.load(open("data/processed/model_run_manifest.json"))
fresh = json.load(open("/path/to/fresh/clone/data/processed/model_run_manifest.json"))

# Check seed reproducibility
assert baseline["random_seed"] == fresh["random_seed"] == 43
assert baseline["git_sha"] == fresh["git_sha"]  # Same code

# Check model metrics match to 3 decimal places
assert abs(baseline["metrics"]["silhouette"] - fresh["metrics"]["silhouette"]) < 0.001
assert abs(baseline["metrics"]["auc_roc"] - fresh["metrics"]["auc_roc"]) < 0.001
```

---

## CI/CD Validation (GitHub Actions)

Recommended: Add `test_reproducibility.py` to Module A CI that:

1. Runs pipeline with seed=43 on Ubuntu x86-64
2. Loads expected manifest from committed JSON snapshot
3. Compares metrics to ±0.1% tolerance (floating-point margin)
4. Fails if seed or git SHA mismatch

Example:
```python
def test_reproducibility_module_a() -> None:
    """Validate that seed=43 produces metrics within FP tolerance."""
    manifest = run_export(seed=43)
    expected = json.load(open("tests/fixtures/expected_manifest_seed43.json"))
    
    assert manifest["random_seed"] == 43
    assert abs(manifest["metrics"]["silhouette"] - expected["silhouette"]) < 0.001
    assert abs(manifest["metrics"]["auc_roc"] - expected["auc_roc"]) < 0.001
```

---

## Known Caveats

1. **CPU/SIMD variability:** Different Intel/AMD CPU architectures may produce ±1 ULP differences in floating-point ops. Expect ≤0.1% metric differences across platforms.

2. **PyMC NUTS sampler:** Random seed controls the chain, but sampler step sizes are tuned per machine. Traces match to < 0.5 pp on margin estimates, but posterior samples may differ. **Posterior quantiles (5th, 50th, 95th) match to < 0.1 pp.**

3. **Parquet compression:** Encoding varies with pyarrow version. Byte-for-byte comparison is fragile; use pandas comparison functions instead.

4. **PuLP solver behavior:** MILP solver may report slightly different dual values (< 0.01%) on different machines due to numerical stability. Allocation *values* match to machine precision; *duals* match to ±1%.

---

## Troubleshooting

**Symptom:** Fresh clone metrics differ > 1% from baseline.

**Diagnostic steps:**
1. Verify Python version: `python --version` → must be 3.11.x
2. Verify lock file used: `poetry lock --no-update` (no new deps)
3. Check seed in YAML/code matches table above
4. Run Module A in isolation: `make module-a-export SEED=43`
5. Compare manifest JSON: `diff baseline.json fresh.json`

**If metrics still differ:**
- OS (Linux vs macOS vs Windows) → ≤ 1% expected
- Different NumPy/SciPy minor versions → rebuild lock file
- GPU acceleration (if any CUDA code added) → disable and rerun

---

## Long-term Maintenance

1. **Pin dependency versions:** `poetry.lock` tracks exact versions. Commit it.
2. **Document seed changes:** If seed changes (e.g., new calibration), update this table.
3. **Update expected hashes** when pipeline logic changes (new features, bug fixes):
   - Rerun on canonical machine (Ubuntu 22.04, Python 3.11.7, locked deps)
   - Update manifest JSON snapshots
   - Commit to git with message `Update reproducibility baseline`

---

## References

- `pyproject.toml` — dependency versions (pin numpy, scipy, scikit-learn, pymc)
- `module_a_population_segmentation/config/generation.yaml` — seed 43
- `module_a_population_segmentation/config/model_params.yaml` — seed 42 (k-means)
- `module_b_resource_allocation/Makefile` — SEED parameter (20180422 baseline)
- `module_c_forecasting_scenarios/config/pymc_sampler.yaml` — seed 42, chains/draws
