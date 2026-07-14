# Epistemic Boundaries — Reconstruction Portfolio

This document classifies **what is verified**, **what is calibrated**, **what is simulated**, and **what is illustrative** for every output artifact in the repository. Its purpose is to allow a technical reviewer, a hiring manager, or a domain expert to understand exactly which claims rest on real-world evidence and which rest on plausible synthetic structure — before reading any code.

**Terminology follows project convention:** entity, population dataset, participation rate, preference proxy, outcome event, survey measurement, program. No real individuals are represented. The reconstruction mirrors the inferential challenge of the original 2018 exercise using publicly verifiable anchors as calibration targets and documented synthetic priors elsewhere.

---

## Status Taxonomy

| Status | Meaning |
|--------|---------|
| **VERIFIED** | Claim matches a publicly available, independently checkable source (electoral authority figures, census statistics). A knowledgeable reviewer can replicate the anchor without code. |
| **CALIBRATED** | Synthetic output constrained to match a verified anchor (e.g., department participation rates, national segment shares). The structure is synthetic; the aggregate statistics hit verified targets within CI-enforced tolerances. |
| **SIMULATED** | Outputs generated under documented priors with no external validation on withheld real microdata. Behavioral fidelity depends on the quality of the prior specification, not on empirical estimation. |
| **ILLUSTRATIVE** | Model outputs intended to demonstrate inferential machinery and decision-support structure. Quantitative values are plausible but not calibrated to real withheld outcomes. Claims about statistical properties (R̂, ESS, interval coverage) are structural — they characterise the model's behavior on sparse fixture data, not real-world calibration. |

---

## Artifact Epistemic Register

| Artifact | Status | Evidence Source | Key Assumptions | Inference Claim |
|---|---|---|---|---|
| **`population_master_clean.parquet`** (Module A) | CALIBRATED | TSJE 2018 roll counts by department; DGEEC 2012 census; INE 2018 ICT survey | Individual records are synthetic; department-level participation rates, gender split, rural/urban shares, and language buckets hit verified anchor targets within ±1 pp CI gates | Individual entities do not represent real registered entities. Department-level demographic distributions match known 2018 registry statistics. |
| **`segment_labels.parquet`** (Module A) | SIMULATED | K-Means on synthetic features; silhouette ≥ 0.22 and bootstrap ARI ≥ 0.70 enforced in CI | 6-cluster solution maps to operationally defined archetypes; cluster stability validated by bootstrap, not by external labelled microdata | Segment assignments are reproducible under fixed seed. The 6 archetypes capture qualitatively distinct channel-mix profiles. No claim of identifying real population sub-groups. |
| **`participation_propensity.parquet`** (Module A) | CALIBRATED | TSJE 2018 national participation rate (**61.25%**); department-level participation anchors | Platt-calibrated logistic regression; department rake applied post-calibration; CI gate: max reliability-diagram deviation ≤ 3 pp | Individual propensity scores are synthetic model outputs. Population-level mean propensity (≈ 0.6125) is calibrated to the verified national rate. Department-level rakes use verified anchors only where configured in `calibration_anchors.yaml`; departments without an anchor fall back to the national placeholder, so department-level distributions are CALIBRATED only for anchored departments and SIMULATED elsewhere. |
| **`media_reachability_by_segment.csv`** (Module A) | SIMULATED | INE 2018 ICT survey for internet/WhatsApp penetration; DGEEC for rural flag shares; industry TV/radio reach estimates | Segment-level reachability aggregated from synthetic individual flags; no department × segment cross-tabulation from DGEEC | Relative channel reachability ordering (TV > radio > WhatsApp > direct in rural segments) is grounded in INE penetration data. Absolute segment-level figures are simulated. |
| **`allocation_output.parquet`** (Module B) | SIMULATED | PuLP/CBC MILP solver; budget envelope **$6M USD** reconstruction; BCP 2018 FX rate priors | Linear persuasion-adjusted contacts objective; reach caps from synthetic Module A output; FX rates from BCP corridor priors | Budget allocation is structurally sound and solver-verified (OPTIMAL status). Persuasion-adjusted contacts are a proxy metric — not audited program accounting. MILP vs department-uniform naive lift (~55% linearized persuasion proxy on envelope) is a solver comparator, not verified historical causal analytics effect. |
| **`routing_schedules.parquet`** (Module B) | SIMULATED | Nearest-neighbor TSP + 2-opt heuristic; synthetic road-network distance matrix; 3 weather scenarios | Distance matrix derived from great-circle km + weather multipliers; no real 2018 road network data | Route feasibility flags and travel-time estimates demonstrate the scheduling machinery. Absolute km and time values are structural approximations; the 2-opt heuristic produces near-optimal tours but not provably optimal routes. |
| **`daily_posterior_forecast.parquet`** (Module C) | ILLUSTRATIVE | 8 real tracking measurement waves from named Paraguayan outlets (La Nación, ABC Color, Última Hora, Radio Ñandutí) and 4 exit surveys — see Module C Tracking Measurement Sources table below; GaussianRandomWalk PyMC model; calibrated to verified TSJE outcome margin (+3.70 pp) | 8 tracking waves over 142 program days; posterior is prior-dominated on measurement-free days; NUTS divergences noted as structural (data sparsity, not mis-specification) | The posterior mean track is directionally consistent with the verified outcome. 95% HDI is structurally wide due to sparse survey measurements — correctly reflecting epistemic uncertainty, not model failure. Walk-forward validation (`validation/walk_forward.py`, F-034) scores the posterior predictive on held-out waves; with 8 tracking waves the reported interval coverage remains structural, not a calibration claim. |
| **`monte_carlo_draws.parquet`** (Module C) | ILLUSTRATIVE | Stratified draws from tracking posterior; LogNormal prior synthesis for sparse buckets; CANONICAL_BUCKETS = {baseline, extreme_tracker, compounded_herd} | Engagement-shock multipliers are illustrative; scenario bucket definitions derive from program phase logic, not empirical shock distributions | The MC engine demonstrates stratified scenario coverage and synthesis fallback machinery. Shock scale values are structurally plausible, not calibrated to real program-event data. All 3 canonical buckets are guaranteed to be covered by the `bundle_min_spend` floor design. |
| **`battleground_probability_heatmap.geojson`** (Module C) | CALIBRATED | 2018 TSJE per-department presidential results (`geo/tsje_2018_department_results.csv`, 19 departments, reconciliation-gated against verified nationals 1,206,067 / 1,110,464); GeoJSON boundaries from [geoBoundaries](https://www.geoboundaries.org/) PRY ADM1 simplified (`paraguay_departments.geojson`, 18 features; Exterior excluded; provenance in `paraguay_departments.SOURCE.md`); reference survey residuals in `data/reference/battleground/` | Hierarchical swing model (c_battleground_v0.5): primary estimand `poll_implied` uses unanchored national posterior × swing_j; μ_dept = swing_j × m; σ_dept = √(σ_national² + σ_idio,j²) with per-dept σ_idio from reference survey MAD + 2013↔2018 election floor; retrodiction companion adds outcome anchor; HDI on win_prob via percentile propagation | win_probability_a = P(Abdo/Candidate A wins dept j). All 5 GANAR-winning departments (Alto Paraná, Central, Concepción, Cordillera, Exterior) produce win_probability_a < 0.5 at the verified national margin — calibration gate passes in CI. Absolute values depend on the unanchored fixture posterior; swing ordering is empirically derived from real TSJE returns. Choropleth is a portfolio visualization — not a verified per-department outcome forecast or operational targeting recommendation. |

---

## Cross-Cutting Verification Sources

| Source | What It Anchors | Where Used |
|--------|----------------|------------|
| TSJE 2018 final results (Tribunal Superior de Justicia Electoral) | Outcome margin +3.70 pp; department participation rates; roll counts by department | Module A calibration targets; Module C posterior anchor; README claim verification |
| DGEEC 2012 Census / 2018 estimates | Rural share ≈ 38.3%; bilingualism ≈ 27.6% Guaraní-dominant; age structure | Module A entity generation priors; rural flag calibration |
| INE 2018 ICT Household Survey | Internet access ≈ 73.4% urban / 27.9% rural; WhatsApp penetration proxies | Module A `internet_access_flag`; Module B reach caps for digital channels |
| BCP (Banco Central del Paraguay) 2018Q1 FX corridor | USD/PYG reference rate ≈ 5,000; retail spread band ≤ 0.5% | Module B `fx_layer`; `schema_contracts/bcp_tc_ref_daily_2018Q1.csv` |

---

## Module C — Tracking Measurement Sources

Raw fixture: `module_c_forecasting_scenarios/tests/fixtures/polls_raw_fixture.csv`

Each row is a real public survey measurement published by a named Paraguayan outlet ahead of the April 2018 presidential election. Figures are verbatim from the cited publication. `eu_release_window_flag` marks measurements published after EU MOE deployment (Mar 13 2018); `oea_timing_compliant` marks measurements compliant with OEA pre-election silence rules.

| poll_raw_id | Publication Date | Pollster | Outlet / Carrier | Source publication | eu_release_window_flag | Notes |
|---|---|---|---|---|---|---|
| raw_capli_20180201 | 2018-02-01 | Capli First Análisis | ABC Color (ABC) | ABC Color print/digital, Feb 2018 | (pre-deployment) | No sample size on ficha |
| raw_capli_20180301 | 2018-03-01 | Capli | ABC Color (ABC) | ABC Color print/digital, Mar 1 2018 | (pre-deployment) | Field window stated "semana pasada"; no ficha |
| raw_ati_20180315 | 2018-03-15 | Ati Snead | La Nación | La Nación, Mar 15 2018 | (pre-deployment) | n=800; pre-EU deployment |
| raw_ica_20180318 | 2018-03-18 | Taka Chase ICA | Última Hora (Vierci) | Última Hora, Mar 18 2018 | (pre-deployment) | n=600; no ficha |
| raw_ecodat_20180326 | 2018-03-26 | EcoDat | La Nación (Nación Media) | La Nación, Mar 26 2018 | true | n=1412; field window Mar 20–23; post EU MOE deployment |
| raw_capli_20180406 | 2018-04-06 | First Análisis y Estudios | ABC Color (ABC) | ABC Color, Apr 6 2018 | true | No sample size published; no ficha |
| raw_grau_20180410 | 2018-04-10 | Grau & Asociados | Última Hora (Vierci) | Última Hora, Apr 10 2018 | true | n=1500; field window Mar 27 – Apr 8 |
| raw_ati_20180418 | 2018-04-18 | Ati Snead | Radio Ñandutí | Radio Ñandutí broadcast, Apr 18 2018 | true | n=1500; field window Apr 15–18; broadcast date used (Última Hora print Apr 19) |
| raw_exit_20180421 | 2018-04-21 | Exit Survey C | Radio | Radio, Apr 21 2018 | — | Exit survey; no ficha |
| raw_exit_20180422 | 2018-04-22 | Consortium Exit | TV | TV, Apr 22 2018 | — | Exit survey; n=1200 |
| raw_exit_20180422b | 2018-04-22 | Exit Survey B | TV | TV, Apr 22 2018 | — | Exit survey; n=900 |
| raw_exit_20180420 | 2018-04-20 | Exit Survey D | Web | Web, Apr 20 2018 | — | Exit survey; n=500 |

---

## How to Use This Document

1. **Before citing a number**, check which row covers the artifact that produced it. If the status is ILLUSTRATIVE or SIMULATED, the claim should be framed as "the model produces…" or "structurally, the system demonstrates…" — not "the model predicts…" or "historical data shows…".

2. **For hiring reviewers:** The VERIFIED and CALIBRATED rows are the credibility substrate of the portfolio. The SIMULATED and ILLUSTRATIVE rows demonstrate engineering and methodological sophistication — they are intentionally marked as such to show that the author distinguishes between what is proven and what is demonstrated.

3. **Upgrading a row:** Move a SIMULATED row to CALIBRATED by obtaining real sub-national survey or administrative microdata and validating against it under a held-out gate. Move ILLUSTRATIVE to CALIBRATED by running walk-forward validation against real withheld survey waves (the current 2-holdout fixture cannot support a coverage claim).

4. **Boundary violations:** If any sentence in the README, model cards, or Quarto reports implies a stronger inferential status than the row above, rewrite it to match this register or escalate the status here with supporting evidence.

---

*Last updated: 2026-06-14. Linked from README.md §Epistemic calibration.*
