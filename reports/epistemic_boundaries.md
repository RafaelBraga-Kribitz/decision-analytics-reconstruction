# Epistemic Boundaries — Reconstruction Portfolio

This document classifies **what is verified**, **what is calibrated**, **what is simulated**, and **what is illustrative** for every output artifact in the repository. Its purpose is to allow a technical reviewer, a hiring manager, or a domain expert to understand exactly which claims rest on real-world evidence and which rest on plausible synthetic structure — before reading any code.

**Domain, named plainly.** This portfolio reconstructs the **Paraguay 2018 presidential election** (Mario Abdo Benítez / ANR-Colorado vs. Efraín Alegre / GANAR alliance; TSJE-administered; election day 22 April 2018). The reader-facing vocabulary is plain and literal:

| Plain term used everywhere | Meaning | Stable code identifier (unchanged) |
|---|---|---|
| **voter** / **synthetic voter record** | one simulated eligible-voter row | `entity_id`, `population_master_clean.parquet` |
| **turnout** | share of eligible voters casting a vote | `participation_propensity.parquet` |
| **poll** / **poll wave** | a published tracking survey | `polls_clean_tracking_wave.yaml`, `poll_wave_id` |
| **campaign** | the multi-week outreach effort | — |
| **vote-preference proxy** | modelled candidate-preference signal | `preference_proxy_*` columns |
| **the 2018 presidential election** | the modelled event and its verified result | — |

**This is not an anonymity claim, and none is made.** Every individual-level record is synthetic microdata; the only real quantities are public aggregate anchors (TSJE returns, DGEEC/INE census and survey statistics, BCP FX corridors). Naming the domain plainly therefore exposes no real person. **No real individuals are represented.** The reconstruction mirrors the inferential challenge of the 2018 exercise using publicly verifiable anchors as calibration targets and documented synthetic priors elsewhere.

---

## Status Taxonomy

| Status | Meaning |
|--------|---------|
| **VERIFIED** | Claim matches a publicly available, independently checkable source (electoral authority figures, census statistics). A knowledgeable reviewer can replicate the anchor without code. |
| **CALIBRATED** | Synthetic output constrained to match a verified anchor (e.g., department turnout rates, national segment shares). The structure is synthetic; the aggregate statistics hit verified targets within CI-enforced tolerances. |
| **SIMULATED** | Outputs generated under documented priors with no external validation on withheld real microdata. Behavioral fidelity depends on the quality of the prior specification, not on empirical estimation. |
| **ILLUSTRATIVE** | Model outputs intended to demonstrate inferential machinery and decision-support structure. Quantitative values are plausible but not calibrated to real withheld outcomes. Claims about statistical properties (R̂, ESS, interval coverage) are structural — they characterise the model's behavior on sparse fixture data, not real-world calibration. |

---

## Artifact Epistemic Register

| Artifact | Status | Evidence Source | Key Assumptions | Inference Claim |
|---|---|---|---|---|
| **`population_master_clean.parquet`** (Module A) | CALIBRATED | TSJE 2018 roll counts by department; DGEEC 2012 census; INE 2018 ICT survey | Individual records are synthetic; department-level turnout rates, gender split, rural/urban shares, and language buckets hit verified anchor targets within ±1 pp CI gates | Individual synthetic voter records do not represent real registered voters. Department-level demographic distributions match known 2018 registry statistics. |
| **`segment_labels.parquet`** (Module A) | SIMULATED | K-Means on synthetic features; silhouette ≥ 0.22 and bootstrap ARI ≥ 0.40 enforced in CI (50k gate; 0.50 test floor at 15k) | 6-cluster solution maps to operationally defined archetypes; cluster stability validated by bootstrap, not by external labelled microdata | Segment assignments are reproducible under fixed seed. The 6 archetypes capture qualitatively distinct channel-mix profiles. No claim of identifying real population sub-groups. |
| **`participation_propensity.parquet`** (Module A) | CALIBRATED | TSJE 2018 national turnout (**61.25%**); department-level turnout anchors | Platt-calibrated logistic regression; department rake applied post-calibration; CI gate: max reliability-diagram deviation ≤ 3 pp | Individual propensity scores are synthetic model outputs. Population-level mean propensity (≈ 0.6125) is calibrated to the verified national turnout. Department-level rakes use verified anchors only where configured in `calibration_anchors.yaml`; departments without an anchor fall back to the national placeholder, so department-level distributions are CALIBRATED only for anchored departments and SIMULATED elsewhere. |
| **`media_reachability_by_segment.csv`** (Module A) | SIMULATED | INE 2018 ICT survey for internet/WhatsApp penetration; DGEEC for rural flag shares; industry TV/radio reach estimates | Segment-level reachability aggregated from synthetic individual flags; no department × segment cross-tabulation from DGEEC | Relative channel reachability ordering (TV > radio > WhatsApp > direct in rural segments) is grounded in INE penetration data. Absolute segment-level figures are simulated. |
| **`allocation_output.parquet`** (Module B) | SIMULATED | PuLP/CBC MILP solver; budget envelope **$6M USD** reconstruction; BCP 2018 FX rate priors | Linear persuasion-adjusted contacts objective; reach caps from synthetic Module A output; FX rates from BCP corridor priors | Budget allocation is structurally sound and solver-verified (OPTIMAL status). Persuasion-adjusted contacts are a proxy metric — not audited campaign accounting. MILP vs department-uniform naive lift (~55% linearized persuasion proxy on envelope) is a solver comparator, not verified historical causal analytics effect. |
| **`routing_schedules.parquet`** (Module B) | SIMULATED | Nearest-neighbor TSP + 2-opt heuristic; synthetic road-network distance matrix; 3 weather scenarios | Distance matrix derived from great-circle km + weather multipliers; no real 2018 road network data | Route feasibility flags and travel-time estimates demonstrate the scheduling machinery. Absolute km and time values are structural approximations; the 2-opt heuristic produces near-optimal tours but not provably optimal routes. |
| **`daily_posterior_forecast.parquet`** (Module C) | ILLUSTRATIVE | 8 real tracking poll waves from named Paraguayan outlets (La Nación, ABC Color, Última Hora, Radio Ñandutí) and 4 exit surveys — see Module C Tracking Poll Sources table below; GaussianRandomWalk PyMC model; calibrated to verified TSJE outcome margin (+3.70 pp) | 8 tracking waves over 142 campaign days; posterior is prior-dominated on poll-free days; NUTS divergences noted as structural (data sparsity, not mis-specification) | The posterior mean track is directionally consistent with the verified outcome. 95% HDI is structurally wide due to sparse polls — correctly reflecting epistemic uncertainty, not model failure. Walk-forward validation (`validation/walk_forward.py`, F-034) scores the posterior predictive on held-out waves; with 8 tracking waves the reported interval coverage remains structural, not a calibration claim. |
| **`monte_carlo_draws.parquet`** (Module C) | ILLUSTRATIVE | Stratified draws from tracking posterior; LogNormal prior synthesis for sparse buckets; CANONICAL_BUCKETS = {baseline, extreme_tracker, compounded_herd} | Engagement-shock multipliers are illustrative; scenario bucket definitions derive from campaign phase logic, not empirical shock distributions | The MC engine demonstrates stratified scenario coverage and synthesis fallback machinery. Shock scale values are structurally plausible, not calibrated to real campaign-event data. All 3 canonical buckets are guaranteed to be covered by the `bundle_min_spend` floor design. |
| **`battleground_probability_heatmap.geojson`** (Module C) | CALIBRATED | 2018 TSJE per-department presidential results (`geo/tsje_2018_department_results.csv`, 19 departments, reconciliation-gated against verified nationals 1,206,067 / 1,110,464); GeoJSON boundaries from [geoBoundaries](https://www.geoboundaries.org/) PRY ADM1 simplified (`paraguay_departments.geojson`, 18 features; Exterior excluded; provenance in `paraguay_departments.SOURCE.md`); reference survey residuals in `data/reference/battleground/` | Hierarchical swing model (c_battleground_v0.5): primary estimand `poll_implied` uses unanchored national posterior × swing_j; μ_dept = swing_j × m; σ_dept = √(σ_national² + σ_idio,j²) with per-dept σ_idio from reference survey MAD + 2013↔2018 election floor; retrodiction companion adds outcome anchor; HDI on win_prob via percentile propagation | win_probability_a = P(Abdo/Candidate A wins dept j). All 5 GANAR-winning departments (Alto Paraná, Central, Concepción, Cordillera, Exterior) produce win_probability_a < 0.5 at the verified national margin — calibration gate passes in CI. Absolute values depend on the unanchored fixture posterior; swing ordering is empirically derived from real TSJE returns. Choropleth is a portfolio visualization — not a verified per-department outcome forecast or operational targeting recommendation. |

---

## Cross-Cutting Verification Sources

Full register with origin, licence, date and verification status: [Data Source Register](#data-source-register) below.

| Source | What It Anchors | Where Used |
|--------|----------------|------------|
| TSJE 2018 final results (Tribunal Superior de Justicia Electoral) | Election-outcome margin +3.70 pp; department turnout rates; roll counts by department | Module A calibration targets; Module C posterior anchor; README claim verification |
| DGEEC 2012 Census / 2018 estimates | Rural share 38.3%; language 46% Jopará-bilingual / 34% Guaraní-only / 15% Spanish-only; age structure (values as in `module_a_population_segmentation/config/calibration_anchors.yaml`, `demographics` and `language`) | Module A voter-record generation priors; rural flag calibration |
| INE EPHC 2018 household survey (Encuesta Permanente de Hogares Continua) / SENATIC | Internet access 74.1% urban / 48.7% rural; WhatsApp used by 96.3% of internet users (values as in `calibration_anchors.yaml`, `ict`) | Module A `internet_access_flag`; Module B reach caps for digital channels |
| BCP (Banco Central del Paraguay) 2018Q1 FX corridor | **PRIOR, not yet verified** against the published BCP daily series: weekly USD/PYG reference rate 5,500 to 5,640 (2018-W01..W14); retail spread over reference 1.7% to 2.6% (`module_b_resource_allocation/config/bcp_tc_ref_2018Q1_prior.yaml`, `fx_retail_spread_prior.yaml`) | Module B `fx_layer`. No BCP daily CSV is committed; an earlier version of this table cited `schema_contracts/bcp_tc_ref_daily_2018Q1.csv`, which does not exist. |

---

## Data Source Register

Every input the pipeline reads that did not originate in this repository, plus the hand-set priors that stand in for data not yet obtained. **Status** uses the taxonomy above; **PRIOR, not yet verified** means the value is a placeholder that has not been checked against the named source. Where an origin URL or access date is not recorded in the repository, the cell says so instead of guessing.

| Source | Origin | Licence / terms | Date | How it is used | Status |
|---|---|---|---|---|---|
| TSJE 2018 general election, results per polling table (`Resultados-por-mesa-2018.csv`, 21,206 presidential rows) | Tribunal Superior de Justicia Electoral. Origin URL to be added by author; the raw file is not committed (aggregated locally, see `governance/findings/F-070-*.yaml`) | Official public electoral record; terms to be confirmed by author | Election 2018-04-22; access date to be added by author | Aggregated to `module_c_forecasting_scenarios/.../geo/tsje_2018_department_results.csv` (Module C battleground); national and department turnout anchors in `module_a_population_segmentation/config/calibration_anchors.yaml` | VERIFIED (department sums reconcile to the national 1,206,067 / 1,110,464) |
| TSJE 2013 presidential results by department | Portal Guaraní reproduction of TSJE 2013 final totals (secondary source). Origin URL to be added by author | Terms to be confirmed by author | Election 2013-04-21; access date to be added by author | `data/reference/battleground/tsje_2013_department_results.csv`; 2013 to 2018 dispersion floor for the battleground sigma estimate | VERIFIED at national totals (Cartes 1,104,169 / Alegre 889,451); department rows rest on the secondary source |
| DGEEC 2012 National Census and 2018 projections | Dirección General de Estadística, Encuestas y Censos (now INE). Origin URL to be added by author; NBI tables V01 to V08 and P01 to P07, INE Tableau LUID `53cfb7a5-3074-40e0-9d27-7b046d0ce5a8` | Official public statistics; terms to be confirmed by author | Census 2012, projections 2018; access date to be added by author | `calibration_anchors.yaml`: `demographics` (urban 61.7%, rural 38.3%, sex split), `language` (46% / 34% / 15%), `nbi` | VERIFIED (aggregates) |
| INE EPHC 2018 household survey / SENATIC | Encuesta Permanente de Hogares Continua 2018. Origin URL to be added by author | Official public statistics; terms to be confirmed by author | Survey year 2018; access date to be added by author | `calibration_anchors.yaml` `ict`: internet 74.1% urban / 48.7% rural, WhatsApp 96.3% of internet users; Module A `internet_access_flag`, Module B digital reach caps | VERIFIED (aggregates) |
| Eight published 2018 tracking polls | Outlets and publication dates in the poll table below (ABC Color, La Nación, Última Hora, Radio Ñandutí); the same fixture also holds four exit surveys. Per-article URLs to be added by author | Published press figures, transcribed for analysis | 2018-02-01 to 2018-04-18 (exit surveys 2018-04-20 to 04-22) | `module_c_forecasting_scenarios/tests/fixtures/polls_raw_fixture.csv`; Module C tracking likelihood | VERIFIED for outlet, date and figures; pollster labels partly pseudonymized |
| Department-level poll margins (2013, 2018) | Última Hora, 2013-04-14 ([article](https://www.ultimahora.com/cartes-aumenta-ventaja-alegre-la-encuesta-grau-asociados-n613847.html)); Última Hora, 2018-04-10 ([article](https://www.ultimahora.com/marito-aventaja-24-puntos-alegre-intencion-voto-n1142092.html)); Infobae, 2018-04-19 ([article](https://www.infobae.com/america/america-latina/2018/04/19/guerra-de-encuestas-y-cuenta-regresiva-en-paraguay-quienes-son-los-favoritos/)) | Published press figures | Access date to be added by author | `data/reference/battleground/dept_poll_margins.csv`; per-department residual dispersion | VERIFIED for the published figures; several rows are regional breakdowns weighted down |
| geoBoundaries PRY ADM1 (department boundaries) | [geoBoundaries](https://www.geoboundaries.org/), gbOpen PRY ADM1; underlying source DGEEC 2012 departments | **CC BY 4.0** (Creative Commons Attribution 4.0 International), per the geoBoundaries API metadata for PRY ADM1, read 2026-10-26; cite per `CITATION-AND-USE-geoBoundaries.txt` in the source archive | Boundary year 2012; repo build 2026-07-14 (`paraguay_departments.SOURCE.md`) | `paraguay_departments.geojson` (18 features) for the battleground choropleth | VERIFIED (geometry) |
| BCP USD/PYG weekly reference rate, 2018-W01 to W14 | Banco Central del Paraguay. Values are hand-set, not downloaded | Not applicable until replaced by the published series | 2018Q1 | `module_b_resource_allocation/config/bcp_tc_ref_2018Q1_prior.yaml` (5,500 to 5,640 PYG per USD); Module B `fx_layer` | **PRIOR, not yet verified** |
| Retail FX spread over the BCP reference rate | Hand-set | Not applicable | 2018-01 to 2018-04 | `fx_retail_spread_prior.yaml` (1.7% to 2.6%); Module B `fx_layer` | **PRIOR, not yet verified** |
| Channel unit costs (PYG per reachable contact) | Hand-set; to be replaced by 2018 vendor rate cards | Not applicable | 2018 | `channel_unit_costs_pyg.yaml`; Module B MILP cost coefficients | **PRIOR, not yet verified** |
| Department population | Hand-set, rounded thousands; to be hardened against DGEEC 2012 census plus projection | Not applicable | 2018 | `department_population_prior.yaml`; Module B reach-cap fallback only | **PRIOR, not yet verified** |
| MILP objective weights (tier weights, week weights, diminishing-returns curves) | Hand-set modelling assumptions | Not applicable | n/a | `allocation_parameter_provenance.yaml` lists every coefficient with its provenance | ESTIMATED (no calibration data) |
| Synthetic 50,000-row voter file | Generated in this repository (Module A, seed 42), raked to the VERIFIED aggregates above | MIT, as the repository | Regenerated per run | All individual-level Module A outputs | SIMULATED / CALIBRATED at anchored aggregates |

---

## Module C — Tracking Poll Sources

Raw fixture: `module_c_forecasting_scenarios/tests/fixtures/polls_raw_fixture.csv`

Each row transcribes a real public poll published ahead of the April 2018 Paraguayan presidential election. The externally checkable elements of each row are the **outlet/carrier, publication date, and published figures — these are verbatim from the cited publication**. Pollster names are **not** uniformly verbatim: several are pseudonymized or generic (e.g. "Ati Snead", "Taka Chase ICA", and the "Exit Survey …"/"Consortium Exit" labels), while others match the published attribution (e.g. "Grau & Asociados"). Names were abstracted because the tracking model consumes them only as house-effect identifiers and because press attributions for some polls were inconsistent across editions — do not treat the Pollster column as a set of searchable firm names. `eu_release_window_flag` marks polls published after EU MOE deployment (Mar 13 2018); `oea_timing_compliant` marks polls compliant with OEA pre-election silence rules.

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

**Fixture pollster label → published attribution (where known).** Use the outlet/date/figures columns to verify each row; the Pollster column is a house-effect identifier, not always a searchable firm name.

| Fixture `pollster_display_name` | Published attribution (verify via cited outlet + date) | Status |
|---|---|---|
| Ati Snead | ATI / Snead (La Nación Mar 15 2018; Radio Ñandutí Apr 18 2018) | pseudonymized house-effect ID |
| Taka Chase ICA | ICA (Última Hora / Vierci, Mar 18 2018) | pseudonymized house-effect ID |
| Capli / Capli First Análisis / First Análisis y Estudios | CAPLI (ABC Color, Feb–Apr 2018 waves) | spelling variants of same firm |
| EcoDat | EcoDat (La Nación, Mar 26 2018) | matches published attribution |
| Grau & Asociados | Grau & Asociados (Última Hora, Apr 10 2018) | matches published attribution |
| Exit Poll B/C/D, Consortium Exit | carrier-only (TV/Radio/Web); no single published pollster name on the ficha | generic exit labels |

---

## How to Use This Document

1. **Before citing a number**, check which row covers the artifact that produced it. If the status is ILLUSTRATIVE or SIMULATED, the claim should be framed as "the model produces…" or "structurally, the system demonstrates…" — not "the model predicts…" or "historical data shows…".

2. **For hiring reviewers:** The VERIFIED and CALIBRATED rows are the credibility substrate of the portfolio. The SIMULATED and ILLUSTRATIVE rows demonstrate engineering and methodological sophistication — they are intentionally marked as such to show that the author distinguishes between what is proven and what is demonstrated.

3. **Upgrading a row:** Move a SIMULATED row to CALIBRATED by obtaining real sub-national survey or administrative microdata and validating against it under a held-out gate. Move ILLUSTRATIVE to CALIBRATED by running out-of-sample validation against withheld poll waves — the committed leave-one-wave-out walk-forward report ([`reports/module_c/walk_forward_loo_report.md`](module_c/walk_forward_loo_report.md)) scores **6 holdouts** from 8 tracking waves (`min_train_size=2`, honestly caveated coverage; regenerate with `MC_FAST=1` for CI-speed MCMC).

4. **Boundary violations:** If any sentence in the README, model cards, or Quarto reports implies a stronger inferential status than the row above, rewrite it to match this register or escalate the status here with supporting evidence.

---

*Last updated: 2026-10-26. Linked from README.md §Epistemic calibration.*
