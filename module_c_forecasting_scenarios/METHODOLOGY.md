# Module C Methodology — Probabilistic Tracking & Exit Bias

## Overview

Module C ingests survey data from multiple polling firms, models systematic bias (house effects), and outputs a Bayesian posterior distribution over the true preference margin with credible intervals. Two models:

1. **Tracking hierarchical model** — daily latent margin via Gaussian random walk + pollster-specific offsets
2. **Exit quickcount model** — exit-poll bias via OEA timing + EU release-window flags

Both use PyMC (NUTS sampler), with diagnostics exportable for auditing.

---

## Tracking Hierarchical Model

### Generative model

**Latent state (non-centered random walk, model `v0.4`):**
```
sigma_rw          ~ HalfNormal(1.5)
mu_margin_init    ~ Normal(0, 10)          # initial level (pp)
mu_margin_innov[t] ~ Normal(0, 1)          # standardized daily innovations
mu_margin[t]      = mu_margin_init + sigma_rw * cumsum(mu_margin_innov)[t]
```
Latent daily preference margin (t ∈ [start_date, outcome_event_date − 1]). This
is the non-centered form of `GaussianRandomWalk(sigma=sigma_rw)` — see
§ Reparameterization below for why the centered form was replaced.

**Pollster offsets (non-centered hierarchy):**
```
sigma_house       ~ HalfNormal(2.5)
house_offset_z[p] ~ Normal(0, 1)
house_offset[p]   = sigma_house * house_offset_z[p]
```
Per-firm systematic bias (e.g., firm A always overstates margin by +1.2 pp).

**Observation model:**
```
m_poll[i] ~ Normal(mu_margin[t[i]] + house_offset[p[i]], sigma_obs[i])
```
Observed poll margin = latent + house effect + noise.

**Observation variance:**
```
sigma_obs[i] = clip(6.0 / sqrt(phi_transparency[i]), 1.0, 25.0)
```
Transparency (`phi`) inversely scales std dev; clipped to [1, 25] pp. Pollsters with low transparency → wider uncertainty bands.

### Inference

- **Sampler:** NUTS (No-U-Turn sampler in PyMC)
- **Chains:** 4 (see `config/pymc_sampler.yaml`)
- **Draws:** 1000 per chain (post-warmup)
- **Tuning:** 1000 steps per chain
- **Target acceptance:** 0.99 full NUTS (`target_accept_full`); 0.95 fast/CI
- **Seed:** 42
- **Fast mode (MC_FAST=1):** 50 draws, 50 tune (CI only)

### Reparameterization (v0.4) — why non-centered

**Symptom.** Under full NUTS on the production 8-wave fixture, the centered
`v0.3` model (`mu_margin ~ GaussianRandomWalk(sigma=sigma_rw)`,
`house_offset ~ Normal(0, sigma_house)`) failed every convergence gate:
R-hat > 1.01, ESS < 100, and persistent divergences. This is the textbook
**Neal's funnel**: when the scale parameter (`sigma_rw`, `sigma_house`) and the
states it scales are sampled in the same coordinates, the posterior narrows to a
cusp as the scale → 0 that NUTS cannot traverse at a fixed step size. The
8-wave fixture is sparse (8 polls over ~140 latent days), so most of the walk is
prior-dominated and the funnel is severe.

**Remedy.** Non-centered reparameterization decouples the geometry from the
scale. We sample standardized innovations `z ~ Normal(0, 1)` and reconstruct the
latent quantities deterministically:

```
mu_margin  = mu_margin_init + sigma_rw   * cumsum(mu_margin_innov)   # innov ~ N(0,1)
house_offset =                sigma_house * house_offset_z            # z     ~ N(0,1)
```

`mu_margin_init ~ Normal(0, 10)` supplies the initial level that the diffuse
`GaussianRandomWalk` default carried implicitly (margins are plausibly within
±30 pp). NUTS now explores a fixed unit-variance space independent of the
scales. The scale priors are **unchanged** (`HalfNormal(1.5)` / `HalfNormal(2.5)`)
— the fix is geometric, not a re-tuning of prior strength. A single lever was
added on top: `target_accept_full = 0.99` (from 0.95) to clear the last handful
of divergences by shrinking the step size in the tight regions.

**Result** (full NUTS, 4 chains × 1000 draws, seed 42, 8-wave fixture):

| Gate | Criterion | v0.3 (centered) | v0.4 (non-centered) |
|------|-----------|-----------------|---------------------|
| max R-hat | ≤ 1.01 | > 1.01 | **1.007** |
| min ESS bulk | ≥ 400 | < 100 | **~2540** |
| min ESS tail | ≥ 400 | — | **~1860** |
| divergences | 0 | 4+ | **0** |

Enforced (not xfail'd) by `tests/test_mcmc_diagnostics_summary.py` in the slow
lane, with a companion posterior-stability test asserting two independent
seed-42 fits agree within 0.05 pp (mean) / 0.10 pp (HDI bounds) per day.

**Outcome anchor (m★):** After the random-walk likelihood, terminal margin is tied
to the verified Series A/B anchor via `Normal(mu_margin[-1], anchor_sigma)` — see
`models/tracking/hierarchical.py`.

**Posterior extraction (5th, 50th, 95th quantiles):**
- `posterior_mean_preference_margin_pp` = mean across chains/draws
- `posterior_hdi_low_pp` = 5th percentile (HDI lower)
- `posterior_hdi_high_pp` = 95th percentile (HDI upper)

Output: `daily_posterior_forecast.parquet` (date, calibration_series, posterior_mean, HDI_low, HDI_high, model_version).

**House effects export:**
- Per pollster: `house_effect_posterior_mean` + HDI bands
- Output: `posterior_house_effects.parquet`

---

## Exit / Quick-Count Bias Model

### Generative model

**Linear regression on exit margin:**
```
m_exit[i] ~ Normal(intercept + beta_oea * oea[i] + beta_eu * eu[i], sigma)
  intercept ~ Normal(0.0, 30.0)
  beta_oea ~ Normal(0.0, 5.0)
  beta_eu ~ Normal(0.0, 5.0)
  sigma ~ HalfNormal(8.0)
```

**Covariates:**
- `oea[i]` = 1 if exit wave complies with OEA timing rules, 0 else (bias correction)
- `eu[i]` = 1 if released within EU transparency window, 0 else (release-timing bias)

### Inference

- **Sampler:** NUTS
- **Chains:** 4
- **Draws:** 1000 per chain (standard); 50 per chain (MC_FAST=1)
- **Tune:** 1000 / 50
- **Target acceptance:** 0.95 (0.90 in MC_FAST exit path)
- **Seed:** 42

### Early return

If exit_df has < 2 rows: return summary stub with `note="insufficient_exit_rows_for_regression"` (no PyMC run).

**Posterior extraction (5th, 50th, 95th quantiles):**
- Coefficient posteriors for intercept, beta_oea, beta_eu, sigma
- Output: `exit_model_summary.parquet` (parameter, posterior_mean, hdi_low, hdi_high, calibration_series, model_version)

---

## Sampler Configuration

**File:** `config/pymc_sampler.yaml`

```yaml
chains: 4
draws: 1000              # per chain
tune: 1000
target_accept: 0.95      # fast / CI path
target_accept_full: 0.99 # full-NUTS tracking path (non-centered walk)
random_seed: 42
draws_fast: 50           # when MC_FAST=1
tune_fast: 50
```

**Environment variable:** `MC_FAST=1` → use fast draws/tune (unit tests, CI).

---

## MCMC Diagnostics Checklist

After running `run_tracking.main()` or `run_exit.main()`:

- [ ] **Rhat (potential scale reduction):** All parameters Rhat < 1.01 (indicates convergence; `arviz.rhat()`)
- [ ] **Effective sample size (ESS):** ESS_bulk > 400 * chains (chain mixing; `arviz.ess_bulk()`)
- [ ] **Chain traces:** Visual inspection — no drifts, stuck chains, or low autocorr. Run `arviz.plot_trace(idata)` in notebook.
- [ ] **Posterior predictive check:** Observed data vs posterior predictive samples should overlap. `arviz.plot_ppc(idata)`
- [ ] **Divergences:** Should be 0 or < 0.1% of total draws. Check `idata.sample_stats['diverging'].sum()`
- [ ] **Rank plot:** Rank uniformity across chains (no systematic low/high ranks per chain). `arviz.plot_rank(idata)`

**Quick audit script:**
```python
import arviz as az
idata = az.from_netcdf("idata.nc")  # or load from InferenceData object
print(f"Rhat max: {az.rhat(idata).max().values}")
print(f"ESS bulk min: {az.ess_bulk(idata).min().values}")
print(f"Divergences: {idata.sample_stats['diverging'].sum().values}")
```

---

## Data Contracts & Outputs

### Input: `polls_clean_tracking_wave` (tracking.parquet)
- `date` (field_window midpoint)
- `m_poll_pp` (preference margin percentage points)
- `phi_transparency` (0–1; inverse of polling variance)
- `pollster_id` (firm identifier)
- `calibration_series` (A or B; controls m_star prior anchor)

### Output: `daily_posterior_forecast.parquet`
- `date`
- `posterior_mean_preference_margin_pp`
- `posterior_hdi_low_pp`, `posterior_hdi_high_pp`
- `calibration_series`, `series_tag`
- `model_version` = `c_tracking_hierarchical_v0.4`

### Output: `posterior_house_effects.parquet`
- `pollster_id`
- `house_effect_posterior_mean`
- `house_effect_hdi_low`, `house_effect_hdi_high`
- `pollster_bias_family` (link to taxonomy)
- `calibration_series`, `model_version`

---

## Reproducibility & Seeding

- **Random seed:** 42 (fixed in config)
- **Chain order:** Deterministic given seed
- **Posterior samples:** Drawn in order, reproducible via saved `idata` (ArviZ InferenceData object)
- **Parquet export:** Consistent row order (date ascending for daily, pollster_id alphabetical for houses)

To rerun:
```bash
cd module_c_forecasting_scenarios
poetry run python -m module_c_forecasting_scenarios.pipeline.run_tracking \
  --raw-csv data/raw/polls.csv \
  --out-dir data/processed/module_c
```

---

## Caveats & Known Limitations

1. **Transparency proxy (`phi`):** Estimated from sample size, field-window width, and conglomerate metadata. Missing data → imputation via firm median. See `features/transparency_index.py`.
2. **House effects as random effects:** Assumes offsets are exchangeable across firms. Violates if firm-family effects (e.g., Capli family vs ECODAT family) are systematic and non-modeled.
3. **Weekly stationarity:** GRW assumes no structural breaks (e.g., major events, debate shocks). Detected events should trigger separate model branches.
4. **Exit sample size:** Exit quickcount requires ≥ 2 observations; typically unreliable with < 5 waves. Audit exit_df before run.
5. **Bayesian prior sensitivity:** Priors on sigma_rw, sigma_house, and intercept are weakly informative. Sensitivity analysis recommended for high-stakes decisions (swap priors, rerun, compare posteriors).

---

## References

- **PyMC documentation:** https://docs.pymc.io/
- **ArviZ diagnostics:** https://arviz-devs.github.io/arviz/
- **Hierarchical models:** Gelman et al., *Bayesian Data Analysis*, Chapter 5.
- **House effects in polling:** Durand, Criado-Perez, 2014; Larcinese & Sircar, 2011.
