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

## Transparency Proxy φ and Observation-Noise Calibration (IMP-C02 / audit C4, C6)

Every reported credible interval's width traces back to one heuristic:
`data/transparency.py:compute_phi_transparency` maps four disclosure booleans
(`has_ficha`, `sample_size_known`, `field_window_known`, `mode_known`) to a
transparency index `phi` via hand-asserted constants
(`base = 0.55 if not has_ficha else 0.85`, `step = 0.12`, floor
`PHI_MIN = 0.08`, with special cases at `n_ok <= 1` and `n_ok == 0`), and
`models/tracking/hierarchical.py:observation_sigma` maps `phi` to the
likelihood's observation noise: `sigma_obs = clip(6.0 / sqrt(phi), 1.0, 25.0)`.
A pollster with no disclosed pillars (`phi = 0.12`) gets `sigma_obs ~= 17.3`
pp — more than 10x a fully-transparent pollster's `sigma_obs ~= 6.1` pp
(`phi ~= 0.97`).

**Calibration status: this is a documented modeling heuristic, not a value
fit against realized poll accuracy.** No historical poll-vs-outcome residual
dataset was used to derive `0.55`, `0.85`, `0.12`, or `0.08` — they were
chosen so `phi` behaves monotonically and plausibly across the four
disclosure-pillar counts, nothing more. Per IMP-C02's acceptance criteria,
since the constants are not refit against outcome data, a **published
sensitivity analysis quantifies the exposure** instead:
`module_c_forecasting_scenarios/reports/phi_sensitivity.md` (generated by
`reports/generate_phi_sensitivity.py`, deterministic, seed 42) tabulates
`sigma_obs(phi)` at every disclosure-pillar count under +/-20% and +/-50%
perturbation of the `base`/`step` constants, and refits the tracking model at
`MC_FAST` fidelity under the perturbation extremes to report the resulting
delta in posterior summaries (daily posterior mean/HDI width, house-effect
scale) — a numeric bound on how much of the reported uncertainty is
attributable to this heuristic rather than to genuine poll-to-poll variance.

`sigma_obs` remains clipped to `[1.0, 25.0]` pp regardless of how `phi` is
computed (`models/tracking/hierarchical.py:observation_sigma`) — this bound
is unconditional and does not depend on the heuristic's calibration status.

---

## Monte Carlo Scenario Stratification & Reweighting (IMP-C08 / audit C14)

`scenarios/monte_carlo.py` draws its scenario ensemble in **equal thirds**
across the canonical buckets (`baseline` / `extreme_tracker` /
`compounded_herd`). Equal-thirds allocation is a **variance-reduction
design** — it guarantees every bucket has enough draws for a conditional
(per-bucket) view even when a bucket is rare or absent from the tracking
data. It is **not** a claim that the three buckets are equally likely.

### Importance weights

Every draw carries a `draw_weight` column:

```
draw_weight(bucket) = empirical_prevalence(bucket) / design_share(bucket)
```

- `empirical_prevalence(bucket)` is the fraction of **observed** tracking
  polls assigned to that bucket (`features.shock_scores.scenario_bucket_for_margin`
  applied to real poll rows) — recomputed fresh from the tracking data on
  every run (`scenarios.monte_carlo.empirical_bucket_prevalence`), never
  cached, so it cannot silently drift from the data it describes.
- `design_share(bucket)` is that bucket's equal-thirds sampling fraction
  (~1/3 regardless of the data).

Any statistic **pooled across buckets** (mean, quantile, box plot spanning
all three buckets) must use `draw_weight`
(`scenarios.monte_carlo.weighted_pooled_mean`,
`weighted_pooled_quantile`) — an unweighted pool across equal-thirds draws
silently asserts a uniform scenario prior nobody chose. **Per-bucket
(conditional-on-scenario) views do not need the weight** — they are exactly
what equal allocation is for, and remain valid either way.

A bucket with **zero observed prevalence** (no tracking poll fell into it)
is still drawn at its equal-thirds floor from `shock_params.yaml:bucket_priors`
(`draw_source=synthetic_prior`) so conditional exploration of that bucket
stays possible, but its `draw_weight` is exactly `0.0` — it contributes
nothing to pooled statistics. This is the documented
"hypothetical (prevalence 0 in observed data)" case.

### MC standard error under weighting (effective sample size)

Once draws are importance-weighted, the relevant sample size for a pooled
statistic's Monte Carlo standard error is not the raw draw count but the
**Kish effective sample size**:

```
n_eff = (sum(w))^2 / sum(w^2)
```

(`scenarios.monte_carlo.effective_sample_size`). The MC-SE of a weighted
pooled mean scales as `sigma / sqrt(n_eff)`, not `sigma / sqrt(n)` — the more
concentrated the weights (e.g. the degenerate case where one bucket holds
all the observed prevalence), the fewer effective draws the pooled statistic
actually rests on, even though `n` (the raw draw count) is unchanged. The
post-mortem report (`portfolio/quarto/post_mortem.qmd`, `tbl-mc-summary`)
publishes `n_eff` alongside the weighted pooled mean for this reason.

### Draw-budget justification (`_mc_n`)

`_mc_n()` (`scenarios/monte_carlo.py`) returns 10 000 draws in the full run
and 600 under `MC_FAST=1`. The full-run value is derived from a stated
MC-standard-error target, not asserted:

```
MC-SE = sigma / sqrt(n)
target MC-SE <= 0.1 pp, conservative sigma <= 10 pp (order of magnitude of
  the extreme-bucket margin cutoff, shock_params.yaml:m_star_extreme_pp)
=> n = (sigma / target_MC-SE)^2 = (10 / 0.1)^2 = 10 000
```

`MC_FAST=1` (600 draws, 200 per bucket at equal thirds) is an **engineering
budget for CI runtime**, not an MC-SE-derived value — MC-SE at n=600 is
`10 / sqrt(600) ~= 0.41` pp, far looser than the full run's target. `MC_FAST`
output is never used for report-grade statistics, only for
schema/contract/mapping tests that need bucket coverage rather than
precision. Any future edit to `_mc_n`'s constants must update this
derivation in the same change (the constant and its justification live
together) — a bare constant edit without accompanying arithmetic is a
review-blocking regression of this disclosure.

### Exchangeability of pooled draws

Monte Carlo draws are exchangeable — `draw_id` is a monotone index with no
temporal or ordering meaning (`reports/eda/generate_eda.py` charts C5/C6/C10
disclose this explicitly; do not plot draws against a "draw chunk" x-axis).

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

1. **Transparency proxy (`phi`):** Derived from four disclosure pillars (ficha,
   sample size, field window, mode) via `data/transparency.py:compute_phi_transparency`.
   Its constants are a documented modeling heuristic, not fit against realized
   poll accuracy — see the "φ→σ_obs mapping" caveat below and
   `reports/phi_sensitivity.md` (IMP-C02 / audit C4, C6) for the quantified
   sensitivity bound.
2. **House effects as random effects — exchangeability is a deliberate modeling
   decision (IMP-C02 / audit C4):** `fit_tracking_hierarchical` fits exactly
   one pooled prior for every pollster's house offset —
   `sigma_house ~ HalfNormal(2.5)`, `house_offset[p] ~ Normal(0, sigma_house)`
   (non-centered as `house_offset = sigma_house * house_offset_z`,
   `house_offset_z ~ Normal(0, 1)`) — which assumes house offsets are
   **exchangeable across firms**: no firm or firm-family is a priori expected
   to have a systematically wider or narrower bias than any other.

   A per-pollster-family alternative was once proposed —
   `config/pollster_prior_families.yaml` defined per-family Student-t
   hyperparameters (`student_nu`, `house_sigma_pp`, `house_loc_pp`) for
   `capli` / `ica` / `grau` / `ati_snead` / `default` — but it was **never
   wired into the `pm.Model` block**; `pollster_bias_family` reached the
   fitted model only as a passthrough display label on the exported
   house-effects table (`export_house_effects_table`, sourced from
   `features/taxonomy_tables.py:normalize_pollster_id`). That config file
   has been **deleted** (IMP-C02 resolution (b), not wired) rather than
   implemented, because:
   - the pooled model is the one whose convergence IMP-C01 actually verified
     (R-hat <= 1.01, ESS >= 400, zero divergences) on the production 8-wave
     fixture — reparameterizing to per-family priors on top of an already
     marginal sample size (8 tracking waves across ~4-5 firms) is not
     diagnosable without a materially larger per-firm poll count than this
     fixture provides;
   - a config file that *looks* wired but is a dead passthrough label is
     itself the failure mode this remediation closes — either wire it or
     remove it, and removal is the option that matches what the model
     actually fits today.

   This means the caveat above ("violates if firm-family effects are
   systematic and non-modeled") is an **accepted, disclosed limitation**, not
   an oversight: firm-family systematic bias, if present, is absorbed into
   the shared `sigma_house` scale rather than given its own per-family
   location/scale. `pollster_bias_family` remains in the exported
   house-effects table purely as a display/grouping tag for downstream
   readers — it does not participate in the likelihood.
3. **Weekly stationarity:** GRW assumes no structural breaks (e.g., major events, debate shocks). Detected events should trigger separate model branches.
4. **Exit sample size:** Exit quickcount requires ≥ 2 observations; typically unreliable with < 5 waves. Audit exit_df before run.
5. **Bayesian prior sensitivity:** Priors on sigma_rw, sigma_house, and intercept are weakly informative. Sensitivity analysis recommended for high-stakes decisions (swap priors, rerun, compare posteriors).

---

## References

- **PyMC documentation:** https://docs.pymc.io/
- **ArviZ diagnostics:** https://arviz-devs.github.io/arviz/
- **Hierarchical models:** Gelman et al., *Bayesian Data Analysis*, Chapter 5.
- **House effects in polling:** Durand, Criado-Perez, 2014; Larcinese & Sircar, 2011.
