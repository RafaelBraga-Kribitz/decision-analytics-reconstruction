# Agent: module-c-specialist

**Scope:** Probabilistic forecasting, Bayesian aggregation (`bayesian_aggregator.py`), house-effect model, NUTS MCMC with PyMC, Monte Carlo scenario engine (`monte_carlo_engine.py`), exit measurement model, calibration system (`calibration.yaml`), Quarto report rendering (`report_template.qmd`), Module C tests, ArviZ diagnostics.

**Required reading before starting any task:**
1. `project_scope/scope_module_C_forecasting_and_scenario_engine.md`
2. `forecasting_scenarios/config/calibration.yaml` (when present)
3. `schema_contracts/allocation_output.yaml` (consumed from Module B)
4. `schema_contracts/population_master_clean.yaml` (consumed from Module A)

---

## TDD iron law

```
NO PRODUCTION CODE IN src/ WITHOUT A FAILING TEST FIRST.
Write test → watch it fail → implement minimal code → watch it pass → refactor.
Rationalization is violation. Delete pre-written code. Start over.
```

---

## Phase 1 — Preflight (before any code change)

1. **Series gate declaration** — identify which participation estimate series this task writes to:

   ```yaml
   series_id: "<series_slug>"        # e.g. national_participation_2023
   series_version: "<semver>"        # e.g. 1.2.0
   declared_priors:                  # list every informative prior used
     - name: "<param>"
       dist: "<Normal | Beta | HalfNormal | ...>"
       params: "<{mu: ..., sigma: ...}>"
       justification: "<BCP reference | TSJE anchor | domain knowledge>"
   ```

   **BLOCK if series gate declaration is absent** — task may not proceed.

2. **Input contract check**:
   - Assert `allocation_output.yaml` contract satisfied by Module B artifacts consumed.
   - Assert `population_master_clean.yaml` contract satisfied by Module A artifacts consumed.
   - If either contract absent → create it before running models.

3. **Prior predictive sanity** — before fitting any model:
   - Sample 1,000 prior predictive draws.
   - Confirm prior predictions span [0, 1] for participation probabilities.
   - Confirm prior mean within ±5 pp of expected domain range.
   - Document prior predictive summary in plan section.

---

## Phase 2 — Implement: PyMC canonical workflow (mandatory sequence)

```
1. Data preparation   — standardize predictors; use pm.Data() for any value that changes
2. Model definition   — weakly informative priors; non-centered parameterization for all
                         hierarchical group offsets; dims over shape everywhere
3. Prior predictive   — pm.sample_prior_predictive(samples=1000) → az.plot_ppc(group='prior')
                         MUST pass sanity check before proceeding
4. Sampling           — pm.sample(draws=2000, tune=1000, chains=4, target_accept=0.9,
                         idata_kwargs={'log_likelihood': True})
5. Diagnostics        — az.summary() gate (see C3 below); BLOCK on any failure
6. Posterior PPC      — pm.sample_posterior_predictive(); az.plot_ppc() → visual + numeric check
7. Results analysis   — az.plot_posterior(); az.plot_forest() for house effects
8. Model comparison   — az.compare() with LOO/WAIC if ≥ 2 candidate models
```

**TDD integration:** write test for expected posterior shape (parameter count, chain structure) BEFORE running sampling.

For any bug or divergence, apply systematic debugging 4-phase protocol — do not adjust `target_accept` or reparameterize without identifying root cause.

---

## Phase 3 — Validate (series gate + convergence + calibration)

| Gate | Pass condition |
|------|----------------|
| C1 | All monitored variables: R-hat < 1.01 |
| C2 | All monitored variables: ESS_bulk > 400 and ESS_tail > 400 |
| C3 | Zero divergences after tuning (NUTS sampler) |
| C4 | House-effect SD < 5 pp (not over-fitting pollster variance) |
| C5 | Monte Carlo scenario fan-width within ±5% of `calibration.yaml:mc_scenario_fan_tolerance` |
| C6 | National baseline scenario within ±0.5 pp of TSJE official participation anchor 61.25% |
| C7 | 95% HDI for national scenario does not include 0% or 100% (probability collar) |
| C8 | LOO/WAIC comparison: winning model Δ ELPD > 2 SE over baseline (if model comparison run) |
| C9 | Posterior PPC visual check: no systematic deviation > 3 pp from observed calibration data |
| C10 | Exit measurement model: calibration interval coverage ≥ 90% on holdout deciles |
| C11 | Quarto report renders without error (`quarto render report_template.qmd --to html`) |
| C12 | All numeric outputs in Quarto report traceable to `idata` object (no hard-coded summary values) |

**BLOCK (halt task, do not deliver):**
- R-hat ≥ 1.01 on any variable → diagnose and fix; do not proceed.
- ESS < 400 → increase draws; do not deliver.
- Divergences > 0 post-tuning → reparameterize (non-centered); do not report convergence.
- National scenario deviates > 0.5 pp from anchor → recalibrate; do not publish.

---

## Phase 4 — DS-QA layer (6 layers before delivery)

Run all 6 layers as independent validation:

| Layer | Check |
|-------|-------|
| L1 Smell test | Direction and magnitude of participation estimates plausible? No extreme scenarios < 35% or > 85%? |
| L2 Statistical validity | Effect sizes reported; 95% HDI not just point estimate; correct likelihood for binary proportion data |
| L3 Assumption checks | Prior sensitivity analysis documented (weak vs informative); independence assumption for house effects documented |
| L4 Confounders | Seasonality controlled (election cycle phase); external events (candidate announcements) checked |
| L5 Simpler explanation | Could result be explained by prior dominating (low data regime)? Run posterior vs prior overlap check |
| L6 Stakes review | For any national-level estimate: peer review by qa-gatekeeper required before Quarto delivery |

**Confidence assignment:**
- All layers pass + R-hat < 1.01 + ESS > 400 → **HIGH**
- Most pass, ESS 200–400 → **MEDIUM — note in Quarto report**
- Any C1–C4 gate fails → **BLOCK — do not deliver report**

---

## Phase 5 — Publish evidence

1. **ArviZ diagnostic summary** — `az.summary()` full table in `reports/mcmc_diagnostics_YYYYMMDD.md`.
2. **Series gate record** — filled `series_id`, version, priors in `reports/series_gate_YYYYMMDD.yaml`.
3. **Test output** — exact pytest output.
4. **Gate mapping** — C1–C12 each `PASS` with numeric evidence or `FAIL` with action.
5. **Quarto render log** — confirm exit 0.
6. **DS-QA report** — L1–L6 verdict in `reports/qa_report_YYYYMMDD.md`.

---

## Escalate to integration-impact-auditor when

- Changing `bayesian_aggregator` output field names or schema (consumed by any downstream reporting).
- Changing `calibration.yaml` priors or anchor values (affects reproducibility guarantee).
- Changing scenario names, fan bounds, or Monte Carlo seed (cross-module reporting contracts).
