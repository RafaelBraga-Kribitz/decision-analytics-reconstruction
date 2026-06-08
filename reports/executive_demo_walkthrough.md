# Executive demo walkthrough

Audience: a senior decision-maker (boss, campaign principal, head of analytics)
arriving cold at the repository. The goal is a clear, ordered tour of what to
open, what each artifact represents, and how to talk about it.

Repository: Clone the repo and navigate to its root directory (all paths below are relative to that)
Walkthrough generated: 2026-05-11 (post end-to-end smoke run, see verification
section at the bottom).

**Technical companion:** for a code-path walkthrough of one entity through Modules A→B→C, read [`system_walkthrough.md`](system_walkthrough.md).

---

## 60-second story

The system reconstructs three analytical capabilities for a national-scale
program affecting a population dataset of ~4.26 million entities, against a
verifiable binary outcome event.

1. **Module A — population modeling and segmentation.** Build a synthetic
  population calibrated to verified TSJE and DGEEC anchors, segment entities
   into six operational archetypes, and score each entity's participation
   propensity in [0, 1].
2. **Module B — resource allocation.** Constrained MILP that assigns a fixed
  budget across 18 departments × 11 channels × 14 weeks to maximize expected
   persuasion-adjusted contacts subject to reach caps, bundle constraints, and
   weekly FX translation.
3. **Module C — probabilistic forecasting and scenarios.** Bayesian
  hierarchical tracking model over noisy survey measurements, an exit-wave
   model with transparency adjustments, and a Monte Carlo scenario engine that
   ingests Module B allocation outputs as bounded perturbations.

**What was verified in this session** (see "Reproduction evidence" below):
Module C test suite passes (17/17, MC_FAST); Module A export pipeline emits
all four contract-aligned artifacts; Module B baseline + counterfactual MILPs
both solve to OPTIMAL ($6,029,992.61 total, 2,772 allocation rows); Module C
end-to-end run (tracking + exit + Monte Carlo + battleground geojson)
completes against the fixture CSV.

The reconstruction is the rebuild a practitioner would do today, with the
rigor that was absent at the original operational tempo.

---

## What to open first

A senior reviewer can complete this checklist in under 15 minutes.

1. **README.** `README.md` — top-of-tree narrative and architecture diagram.
2. **Live dashboard.** Streamlit deploy:
  [https://decision-analytics-module-a.onrender.com](https://decision-analytics-module-a.onrender.com).
   Set `k = 6` and look at: (a) Segment Explorer tab, (b) Propensity
   National-Rate Reference Diagnostic tab, (c) Data Quality Report tab.
3. **Local Module C scenario explorer (Plotly HTML).**
  `data/processed/module_c/run_all/tracking/scenario_explorer.html`
   Posterior mean margin + HDI band + survey wave markers.
4. **Module A model cards.**
  `module_a_population_segmentation/reports/model_card_segmentation.md` and
   `module_a_population_segmentation/reports/model_card_propensity.md`.
   Every gate, threshold, and known limitation is in one page each.
5. **Cross-module handshake.** `reports/module_b_module_c_handshake.md` —
  the contract that connects Module B allocation rows to Module C scenario
   perturbations.
6. **Decision log tail.** `reports/decision_log.md` (last ~10 entries) — every
  non-trivial choice made during reconstruction, dated, with alternatives
   considered.
7. **Schema contracts.** `schema_contracts/` — authoritative cross-module
  data contracts (one YAML per artifact).
8. **CI badge / workflow.** Linked from README (`/.github/workflows/ci.yml`).
  The CI job runs lint, typecheck, Module A tests, and a Docker smoke build.

---

## Module A — population modeling and segmentation

**What the dashboard shows.** Three tabs, all driven by an in-memory build of
the synthetic population at `n = 15,000` with a fixed seed:


| Tab                                           | What it is                                                                                              | What to look at                                                                                                                                                                                                               |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Segment Explorer                              | k-means segmentation (k=6) over 13 standardized features reduced to 5 PCs, with a DBSCAN noise pre-pass | Segment size distribution and the per-segment profile means                                                                                                                                                                   |
| Propensity National-Rate Reference Diagnostic | A reliability-style plot built against `Bernoulli(national_rate)` reference labels                      | Whether the calibrated propensity is monotone with the reference, with the caveat that this is a *reference baseline*, not a hold-out calibration plot (see the dashboard caption and the decision log entry on this relabel) |
| Data Quality Report                           | Missingness, duplicate, and value-range checks from the cleaner step                                    | Field-level health of the population dataset                                                                                                                                                                                  |


**How to read the segment table.** Each row of `segment_labels.parquet` is one
entity. The six segments are stable archetypes (e.g. `rural_committed`,
`urban_high_volatility`). Operationally, a segment is a group of entities
that the channel-cap and routing model can address with a coherent mix of
broadcast vs bilateral vs in-person instruments. The names are post-hoc; the
underlying clustering is reproducible (bootstrap ARI 0.79 across 25 reps at
n=15k, seed 42).

**How to read the propensity curve.** `participation_propensity` is a value
in [0, 1] per entity, produced by logistic regression + Platt scaling + a
department rake. The model has Brier 0.088 on the synthetic target (gate
threshold 0.237). Four department anchors (Presidente Hayes, Alto Paraná,
Central, Guairá) pass exact-anchor calibration; national, gender, and youth
calibration are documented as informational (the upstream TSJE anchor table
is internally inconsistent — see propensity model card §"Known limitations").

**What "segment" means operationally.** Segments are not demographic buckets;
they are joint demographic + behavioral + reachability clusters in the
PCA-reduced feature space. The downstream optimizer cares because reach caps
and channel costs differ across segments: a `rural_committed` entity and an
`urban_high_volatility` entity are reached cheaply through very different
channels, and the allocation engine encodes those differences as
per-(segment, department, channel) caps and persuasion weights.

**Local artifacts after `make module-a-export`.** Written to `data/processed/`:

- `population_master_clean.parquet` — entity-level base table.
- `segment_labels.parquet` — entity → (segment_id, segment_label, dbscan_noise_flag).
- `participation_propensity.parquet` — entity → calibrated propensity.
- `media_reachability_by_segment.csv` — segment-level reach diagnostic (k=6 rows).
- `media_reachability_by_segment_department.csv` — segment × department grain
(108 rows). This is the authoritative grain consumed by Module B; the
segment-only rollup must not be reinterpreted as district-level.

---

## Module B — resource allocation

**What allocation output represents.** Each row of `allocation_baseline.csv`
is one decision cell: one (department, channel, week_index). The columns
translate dollars into contacts:


| Column                                            | Plain language                                                                                          |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `budget_allocation_usd`, `budget_allocation_pyg`  | What is spent in this cell, in USD and in PYG after weekly FX translation                               |
| `expected_contacts`                               | Raw forecast number of entities reached                                                                 |
| `persuasion_adjusted_contacts`                    | Reach scaled by per-channel persuasion weights — the optimizer's actual objective surface               |
| `reach_cap_population_proxy`, `reach_utilization` | The denominator and the share of it consumed by this cell                                               |
| `binding_constraint`                              | Which constraint, if any, is tight at the optimum for this cell (audit hook)                            |
| `bundle_id`                                       | Tag identifying packaged-media commitments (e.g. `conglomerate_x`) that are flipped on/off as one block |
| `scenario_id`                                     | `baseline` vs `broadcast_to_direct` vs other counterfactual tags                                        |


**Scenarios available.**

- `baseline` — the canonical solve. Both runs in this session solved to
`OPTIMAL` with total spend $6,029,992.61 across 2,772 rows (18 × 11 × 14).
- `broadcast_to_direct` — a counterfactual: take the budget currently
flowing to broadcast channels (TV spots, radio spots, newspaper inserts)
and reallocate it to direct channels (canvassing, rallies and events,
sound cars, SMS blasts). A 15% bundle-release penalty is applied when
the `conglomerate_x` media bundle is partially unwound. The
`reallocation_counterfactuals.parquet` artifact (per the schema contract)
carries `delta_budget_usd` and `delta_contacts` per cell.

**Counterfactual in plain language.** "Suppose we had decided to spend less
on packaged media and more on direct, person-to-person contact. How many
more reachable entities does that buy, and where? The 15% penalty represents
the sunk logistics cost of partially unwinding a bundled-media contract."

**Local artifacts after `make module-b-allocate`.** Written to
`data/processed/module_b/`:

- `allocation_baseline.parquet` / `.csv` — 2,772 rows.
- `allocation_broadcast_to_direct.parquet` / `.csv` — same shape, counterfactual.
- `reach_caps_baseline.csv`, `reach_caps_broadcast_to_direct.csv` — cap inputs.
- `fx_layer_series_b_weekly.csv` — weekly PYG/USD translation.
- `routing_cost_matrix_dry_standard.csv` — in-person routing cost matrix.
- `run_manifest_baseline.json`, `run_manifest_broadcast_to_direct.json` —
solver status, totals, seed, schema version, provenance.

**FastAPI service.** `make module-b-api` exposes the same solver as a
REST endpoint at `http://127.0.0.1:8088` for interactive scenario probing.

---

## Module C — probabilistic forecasting and scenarios

**Three stages, one calibration gate.**

1. **Tracking model** — a Bayesian hierarchical state-space model over the
  noisy stream of pre-outcome-event survey measurements. Outputs a daily
   posterior on the margin (`daily_posterior_forecast.parquet`), per-firm
   house-effect estimates (`posterior_house_effects.parquet`), and the
   Plotly explorer (`scenario_explorer.html`).
2. **Exit-wave model** — a separate regression on exit-style survey
  measurements with transparency-pillar covariates (OEA timing flag,
   EU release-window flag). Outputs `exit_model_summary.parquet`.
3. **Monte Carlo scenario engine** — 10,000 stratified draws (200 in
  `MC_FAST=1` mode) using `shock_score_s` and `scenario_bucket` from the
   tracking-clean table, optionally ingesting Module B allocation means as
   bounded perturbations. Outputs `monte_carlo_draws.parquet` and
   `monte_carlo_shock_catalog.yaml`.

**Series A vs Series B calibration in one sentence.** Series A uses
valid-vote shares of the preference proxies (m* = +3.70 pp) and Series B
uses the headline pair (m* = +3.88 pp); each run picks exactly one series and
the test suite blocks any hybrid mix of A numerators with B denominators.
The active series is set in
`module_c_forecasting_scenarios/config/calibration.yaml` (this session ran
with `series: A`).

**Where the Plotly HTML and daily posterior live.**

- HTML explorer: `data/processed/module_c/run_all/tracking/scenario_explorer.html`
— open in any browser. Lines: posterior mean margin (pp), HDI low, HDI high.
Diamond markers: the four survey measurements with their `m_poll_pp`.
- Daily posterior table: `data/processed/module_c/run_all/tracking/daily_posterior_forecast.parquet`.
- Battleground geojson: `data/processed/module_c/run_all/battleground/battleground_department_probability.geojson`
(and accompanying `.parquet`) — per-department posterior probability of the
outcome event, ready to render in any GIS tool.
- Run manifest: `data/processed/module_c/run_all/tracking/run_tracking_manifest.json`
(calibration series, m*, outcome event date, repo root, wave count).

*How to read `m` and the posterior bracket idea without claiming fraud.**
`m`* is the verified post-event margin under the active series convention.
The posterior bracket is the per-day HDI from the tracking model. The QA
check (`posterior_margin_tolerance_pp: 4.0`) confirms that the late-window
posterior bracket *contains* `m`* within the calibration tolerance. The
language is deliberately descriptive: this is a calibration-quality check
on the tracking system, not a forensic claim about any survey measurement
or measurement firm. House-effect estimates summarize systematic offsets
per firm with full uncertainty propagation — they do not adjudicate intent.

---

## Graphics inventory

Every chart, HTML page, GIS layer, and notebook a reviewer might want to open.

**Live web.**

- Module A Streamlit dashboard: [https://decision-analytics-module-a.onrender.com](https://decision-analytics-module-a.onrender.com)
(segment explorer · propensity diagnostic · data quality report).

**Local HTML.**

- `data/processed/module_c/run_all/tracking/scenario_explorer.html` —
Plotly: posterior mean margin + HDI low/high + survey measurement markers.

**Local GIS.**

- `data/processed/module_c/run_all/battleground/battleground_department_probability.geojson`
— per-department posterior probability layer for the outcome event.
Pair with `.parquet` of the same name for tabular access.

**Local parquet / CSV outputs.**

- Module A: `data/processed/population_master_clean.parquet`,
`segment_labels.parquet`, `participation_propensity.parquet`,
`media_reachability_by_segment.csv`,
`media_reachability_by_segment_department.csv`.
- Module B: `data/processed/module_b/allocation_baseline.{parquet,csv}`,
`allocation_broadcast_to_direct.{parquet,csv}`,
`reach_caps_baseline.csv`, `reach_caps_broadcast_to_direct.csv`,
`fx_layer_series_b_weekly.csv`,
`routing_cost_matrix_dry_standard.csv`,
`run_manifest_baseline.json`, `run_manifest_broadcast_to_direct.json`.
- Module C: `data/processed/module_c/run_all/tracking/daily_posterior_forecast.parquet`,
`posterior_house_effects.parquet`,
`house_effect_seed_matrix.csv`,
`polling_transparency_audit.csv`,
`exit/exit_model_summary.parquet`,
`mc/monte_carlo_draws.parquet`,
`mc/monte_carlo_shock_catalog.yaml`.

**Notebooks.** Under `module_a_population_segmentation/notebooks/`:

- `01_data_quality_exploration.ipynb`
- `02_feature_engineering.ipynb`
- `03_segmentation_analysis.ipynb` (entry point for interpretability)
- `04_propensity_model_diagnostics.ipynb`

**Quarto skeleton.** `data/processed/module_c/run_all/post_mortem.qmd`
(also in `module_c_forecasting_scenarios/portfolio/quarto/post_mortem.qmd`)
— render with `quarto render` once a narrative layer is added.

**Knowledge graph (engineering-only).**
`graphify-out/GRAPH_REPORT.md` and `graphify-out/graph.html` —
1,387 nodes / 1,781 edges / 128 communities. Useful for code review and
onboarding; not a candidate-facing artifact.

**CI badge.** Linked from the README top-matter at
`/.github/workflows/ci.yml`; the `module-a` job plus a Docker smoke build
runs on every push.

---

## How this would be reported

### 1-page memo outline

1. **Headline (3 lines).** What the system is, who it serves, what was
  verified end-to-end in this session.
2. **Outcome framing.** The verified post-event margin under the active
  calibration series (Series A: +3.70 pp; Series B: +3.88 pp). State the
   convention explicitly.
3. **Module A — what the population dataset and segments give the program.**
  One paragraph each on segmentation, propensity, and reachability.
4. **Module B — what the optimizer buys per dollar.** Total spend, total
  persuasion-adjusted contacts, and one named binding constraint.
5. **Module C — what the forecast says with how much uncertainty.** Posterior
  mean margin near the outcome event, HDI width, and the m* bracket check.
6. **Counterfactual.** One paragraph on the `broadcast_to_direct` scenario:
  delta budget, delta contacts, bundle-penalty assumption.
7. **Limitations.** Synthetic targets at entity level, four out of 18
  department anchors verified, source-inconsistency notes on the national
   anchor table.
8. **Next step.** Verified-source ingestion to replace `PRIOR` provenance
  tags in `run_manifest_*.json` with `VERIFIED`.

### Appendix — file paths

- `README.md`, `reports/decision_log.md`, `reports/data_dictionary.md`,
`reports/module_b_module_c_handshake.md`, `reports/transformation_log.md`.
- `schema_contracts/` (cross-module YAML contracts).
- `module_a_population_segmentation/reports/model_card_segmentation.md`,
`model_card_propensity.md`,
`audit_report_module_a_2026-05-11.md`.
- `module_c_forecasting_scenarios/reports/C_research_proof_table.md`.
- `appendix/verified_calibration_anchors_full.md`.
- Plus every artifact listed in the Graphics Inventory above.

### Suggested figure order for a slide deck

1. **Architecture diagram** (from README): TSJE + DGEEC anchors →
  Module A → Module B → Module C, with the four cross-module artifacts called
   out by name.
2. **Segment table** (Module A dashboard, Segment Explorer): six rows, one
  per segment, with size share and one signature feature.
3. **Propensity diagnostic** (Module A dashboard, Tab 2): national-rate
  reference plot with the explicit caption.
4. **Department reachability** (`media_reachability_by_segment_department.csv`
  pivoted into a heatmap): segment × department reach intensity.
5. **Allocation Sankey or stacked bar** (`allocation_baseline.csv`): USD by
  week by channel family (broadcast vs bilateral vs in-person).
6. **Counterfactual delta** (`reallocation_counterfactuals.parquet`):
  delta contacts per channel between baseline and `broadcast_to_direct`.
7. **Tracking posterior** (the Plotly `scenario_explorer.html` exported as
  a static figure): posterior mean + HDI + survey measurement markers,
   with the m* line annotated under the active series.
8. **Battleground map** (`battleground_department_probability.geojson`):
  per-department posterior probability of the outcome event, colored choropleth.
9. **House-effect summary** (`posterior_house_effects.parquet`): per-firm
  posterior offset with credible interval, ordered by magnitude.
10. **Monte Carlo shock distribution** (`monte_carlo_draws.parquet`):
  histogram of `shock_scale` colored by `scenario_bucket`.

---

## Reproduction evidence (this session)

Each command below was run before this walkthrough was written. Numeric
outputs are quoted verbatim where useful.


| Command                                                                          | Status | Key output                                                                                    |
| -------------------------------------------------------------------------------- | ------ | --------------------------------------------------------------------------------------------- |
| `MC_FAST=1 poetry run pytest module_c_forecasting_scenarios/tests -m "not slow"` | exit 0 | 17 passed, 4 deselected, 10.04s                                                               |
| `make module-a-export SAMPLE=10000`                                              | exit 0 | Five contract-aligned artifacts written under `data/processed/`; contract validation passed   |
| `make module-b-allocate SCENARIO=baseline`                                       | exit 0 | `solver_status=OPTIMAL total_usd=6029992.61`, 2,772 rows                                      |
| `make module-b-allocate SCENARIO=broadcast_to_direct`                            | exit 0 | `solver_status=OPTIMAL`, counterfactual rows written                                          |
| `make module-c-all`                                                              | exit 0 | Tracking + exit + Monte Carlo + battleground geojson under `data/processed/module_c/run_all/` |


**Honest notes.**

- The tracking MCMC sampler logged divergences and `rhat > 1.01` on the
fixture run; this is expected on the small fixture CSV (four waves) under
the project's fast-sampling defaults and is documented in the Module C
reports. A production run uses a longer sampler configuration.
- The Quarto post-mortem skeleton (`post_mortem.qmd`) is a one-screen stub;
it renders with `quarto render` but the narrative layer is intentionally
left for a human author. Treat it as a placeholder for the 1-page memo
above, not as a finished report.
- Allocation provenance is currently tagged `PRIOR` in the run manifests;
verified-source ingestion is the documented follow-up.

