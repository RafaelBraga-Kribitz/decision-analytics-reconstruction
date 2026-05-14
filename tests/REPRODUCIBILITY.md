# Reproducibility Reference — DVC Pipeline

**Generated:** 2026-05-14  
**RNG seed (Module B):** `20180422`  
**Sample size (Module A):** 10 000  
**Module C fast mode:** `MC_FAST=1` (2 chains × 50 draws)

---

## Reproducing from scratch

```bash
# 1. Install dependencies
poetry install

# 2. Run full DVC pipeline (generates all artifacts)
dvc repro

# 3. Verify outputs match reference hashes
dvc status   # expects: "Data and pipelines are up to date."

# 4. (Optional) Push artifacts to remote cache
dvc push
```

For a cross-machine pull:
```bash
dvc pull     # restores data/processed/ from remote cache
make test    # verifies artifact schemas + model metrics
```

---

## Reference artifact hashes (dvc.lock — 2026-05-14 run)

### Module A

| Artifact | MD5 | Size |
|----------|-----|------|
| `population_master_clean.parquet` | `2087d0715865e7bec5f3efbbabe358c8` | 747 294 B |
| `segment_labels.parquet` | `95f522acf7292ac51cf79dc2d48e3629` | 68 276 B |
| `participation_propensity.parquet` | `386ebb7945f58acefdf8872f55d86d27` | 256 915 B |
| `media_reachability_by_segment.csv` | `80c25900c0737fb0a3f08e75b10bb6cb` | 1 027 B |
| `media_reachability_by_segment_department.csv` | `96bb8d26e07321001c4a281096cb34fc` | 12 797 B |

Config dep hashes:
- `generation.yaml`: `e0c706e14674b438ab7cdf669f2ee827`
- `calibration_anchors.yaml`: `1e26a0a2e54120750fe672cc0f9a5f94`
- `model_params.yaml`: `38fb130422ce37d4816b7c9c8e0674e2`

### Module B

| Artifact | MD5 | Size |
|----------|-----|------|
| `allocation_baseline.parquet` | `43171625ce6b7adfce0eeba6d756b97b` | 61 191 B |
| `reach_caps_baseline.csv` | `12421f3a280718d70598d13b4d4f2d81` | 23 360 B |

Key solver metric: `total_usd = 6 029 992.61`, `solver_status = OPTIMAL`

### Module C

| Artifact | MD5 | Size |
|----------|-----|------|
| `daily_posterior_forecast.parquet` | `9cf3cac1360961a3cef3d396ae4328c5` | 9 616 B |
| `posterior_house_effects.parquet` | `88a3fd5b90c8c0e941a24bcd6c091e15` | 5 211 B |
| `monte_carlo_draws.parquet` | `a4da21a04324e15b91cc089dc2e00830` | 5 002 B |
| `battleground_department_probability.parquet` | `4433e27b9c72d175133124a33d2a65d9` | 3 430 B |

Poll fixture dep: `polls_raw_fixture.csv`: `ad3d5f9233cb4f39b15829a921425786`

---

## Pipeline dependency graph

```
generation.yaml  calibration_anchors.yaml  model_params.yaml  population_segmentation/src/
        └──────────────────┬──────────────────────────────────────────┘
                     module_a stage
                           │
              ┌────────────┼────────────┐
              │            │            │
  population_master_clean  │  participation_propensity
  segment_labels           │  media_reachability_*
              └────────────┘
              (conceptual downstream → module_b, module_c run independently)

polls_raw_fixture.csv  calibration.yaml  module_c_forecasting_scenarios/src/
        └──────────────────┬──────────────────────────────────────────┘
                     module_c stage
                           │
         daily_posterior_forecast  posterior_house_effects
         monte_carlo_draws         battleground_department_probability

module_b_resource_allocation/src/
        └─── module_b stage
                   │
         allocation_baseline  reach_caps_baseline
```

---

## Caveats

- Module A hashes are deterministic given the same seed (42) and sample size.
- Module C hashes are NOT stable across runs due to NUTS stochasticity (posterior means converge, exact draws differ). `dvc status` may show Module C as changed on re-run.
- Module B is fully deterministic given `--seed 20180422`.
- DVC cache remote is currently `local-cache` at `../../decision-analytics-dvc-cache`. For cross-machine reproducibility, configure an S3/R2 remote per README setup instructions.
