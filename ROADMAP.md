# Roadmap

Honest status of each module and the next concrete milestones.

---

## Module A — Population Modeling and Segmentation

**Status: production-grade**

- 116 tests passing, CI-gated at 80% coverage
- Full 14-step cleaning pipeline with documented flaw injection and QA gates
- Logistic regression + Platt calibration + department rake; all acceptance criteria met
- DBSCAN pre-pass + K-Means (k=6); silhouette > 0.35, bootstrap ARI > 0.80
- Streamlit dashboard deployed on Render
- Model cards, transformation log, QA reports in `reports/`
- Schema contracts published for downstream modules

**Next milestones:**

| Item | Priority |
|---|---|
| Ingest full TSJE departmental participation table (all 18 departments verified, not estimated) | High |
| Add SHAP feature importance chart to Streamlit dashboard | Medium |
| Parameterize flaw injection rates via CLI for sensitivity testing | Low |

---

## Module B — Resource Allocation Engine

**Status: analytically complete, not packaged to Module A engineering standard**

- PuLP CBC solver with OPTIMAL-status enforcement
- Budget envelope, reach cap, FX corridor, and municipality coverage constraints
- Weekly time-series allocation over 18 weeks, 18 departments, 11 channels
- FX modeling: BCP PYG/USD reference rate with scenario bands (5,500–5,700 corridor)
- FastAPI re-optimization endpoint; P95 latency target ≤ 2 sec under 10 concurrent requests
- Counterfactual analysis (uniform vs. optimized spend comparison)

**What is missing vs. Module A standard:**

- Test coverage below 80% threshold
- No CI enforcement for Module B
- FastAPI endpoint not containerized for one-command deployment
- `alloc_mean_persuasion_contacts` not yet linked to Module C (known integration gap)

**Next milestones:**

| Item | Priority |
|---|---|
| Lift test coverage to 80% with CI enforcement | High |
| Wire `alloc_mean_persuasion_contacts` output to Module C scenario engine | High |
| Containerize FastAPI endpoint with Docker Compose | Medium |
| Publish `budget_allocation_weekly_v1.yaml` schema contract | Medium |

---

## Module C — Probabilistic Forecasting

**Status: analytically complete, not packaged to Module A engineering standard**

- PyMC Bayesian hierarchical tracker with house-effect shrinkage priors
- Four polling sources modeled with estimated house effects (−5.1 pp to +3.8 pp)
- 10,000-draw Monte Carlo scenario engine (baseline / moderate / extreme shock profiles)
- MCMC diagnostics: R-hat < 1.01, ESS > 400, zero divergences
- Quarto post-mortem document (`portfolio/quarto/post_mortem.qmd`; `quarto render` exit 0 required)

**What is missing vs. Module A standard:**

- Module B integration gap: `alloc_mean_persuasion_contacts` is unlinked (win-probability cannot yet reflect budget reallocation decisions)
- Test coverage below 80% threshold
- No CI enforcement for Module C

**Next milestones:**

| Item | Priority |
|---|---|
| Complete Module B integration (budget reallocation → win probability delta) | High |
| Lift test coverage to 80% with CI enforcement | High |
| Add posterior predictive check plots to Quarto deliverable | Medium |
| Geographic win-probability heatmap from `battleground_probability_heatmap.geojson` | Low |

---

## Cross-module

| Item | Status |
|---|---|
| Schema contracts (Module A → B) | Published |
| Schema contracts (Module B → C) | Stub; pending Module B finalization |
| End-to-end pipeline smoke test | Not yet implemented |
| DVC artifact tracking | Config present; not yet enforced in CI |
| Docker Compose full-stack | Partial (Module A only) |
