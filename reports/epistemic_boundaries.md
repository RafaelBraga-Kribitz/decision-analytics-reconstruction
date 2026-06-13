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
| **`segment_labels.parquet`** (Module A) | SIMULATED | K-Means on synthetic features; silhouette ≥ 0.22 and bootstrap ARI ≥ 0.77 enforced in CI | 6-cluster solution maps to operationally defined archetypes; cluster stability validated by bootstrap, not by external labelled microdata | Segment assignments are reproducible under fixed seed. The 6 archetypes capture qualitatively distinct channel-mix profiles. No claim of identifying real population sub-groups. |
| **`participation_propensity.parquet`** (Module A) | CALIBRATED | TSJE 2018 national participation rate (**61.25%**); department-level participation anchors | Platt-calibrated logistic regression; department rake applied post-calibration; CI gate: max reliability-diagram deviation ≤ 3 pp | Individual propensity scores are synthetic model outputs. Population-level mean propensity (≈ 0.6125) and department-level distributions are calibrated to 2018 TSJE participation statistics. |
| **`media_reachability_by_segment.csv`** (Module A) | SIMULATED | INE 2018 ICT survey for internet/WhatsApp penetration; DGEEC for rural flag shares; industry TV/radio reach estimates | Segment-level reachability aggregated from synthetic individual flags; no department × segment cross-tabulation from DGEEC | Relative channel reachability ordering (TV > radio > WhatsApp > direct in rural segments) is grounded in INE penetration data. Absolute segment-level figures are simulated. |
| **`allocation_output.parquet`** (Module B) | SIMULATED | PuLP/CBC MILP solver; budget envelope **$6M USD** reconstruction; BCP 2018 FX rate priors | Linear persuasion-adjusted contacts objective; reach caps from synthetic Module A output; FX rates from BCP corridor priors | Budget allocation is structurally sound and solver-verified (OPTIMAL status). Persuasion-adjusted contacts are a proxy metric — not audited program accounting. MILP vs department-uniform naive lift (~55% linearized persuasion proxy on envelope) is a solver comparator, not verified historical causal analytics effect. |
| **`routing_schedules.parquet`** (Module B) | SIMULATED | Nearest-neighbor TSP + 2-opt heuristic; synthetic road-network distance matrix; 3 weather scenarios | Distance matrix derived from great-circle km + weather multipliers; no real 2018 road network data | Route feasibility flags and travel-time estimates demonstrate the scheduling machinery. Absolute km and time values are structural approximations; the 2-opt heuristic produces near-optimal tours but not provably optimal routes. |
| **`daily_posterior_forecast.parquet`** (Module C) | ILLUSTRATIVE | 4 synthetic survey-measurement-wave fixtures calibrated to verified TSJE outcome margin (+3.70 pp); GaussianRandomWalk PyMC model with optional outcome anchor | Only 4 survey measurement waves over 142 program days; outcome anchor (σ≈0.5 pp) tightens terminal HDI to ≈±0.8 pp — use `daily_posterior_forecast_filtered.parquet` for non-anchored prospective track | Anchored track is retrospective smoothing to Series A outcome. Filtered export preserves wider pre-anchor uncertainty for C1 information-set honesty. Walk-forward validation (T9-1) quantifies out-of-sample interval coverage. |
| **`monte_carlo_draws.parquet`** (Module C) | ILLUSTRATIVE | Stratified draws from tracking posterior; LogNormal prior synthesis for sparse buckets; CANONICAL_BUCKETS = {baseline, extreme_tracker, compounded_herd} | Engagement-shock multipliers are illustrative; scenario bucket definitions derive from program phase logic, not empirical shock distributions | The MC engine demonstrates stratified scenario coverage and synthesis fallback machinery. Shock scale values are structurally plausible, not calibrated to real program-event data. All 3 canonical buckets are guaranteed to be covered by the `bundle_min_spend` floor design. |
| **`battleground_probability_heatmap.geojson`** (Module C) | ILLUSTRATIVE | Logistic transformation of last-day national posterior margin; deterministic per-department jitter (seed=42); approximate polygon boundaries | Department-level probabilities derived from single national margin with synthetic geographic noise; polygon boundaries are simplified rectangular approximations | Relative win probability ordering across departments reflects the national posterior direction. Individual department values (range ≈ **0.49–0.51** on current fixture artifacts) are illustrative model outputs — not verified outcome forecasts. Choropleth is a portfolio visualization, not an operational targeting recommendation. |

---

## Cross-Cutting Verification Sources

| Source | What It Anchors | Where Used |
|--------|----------------|------------|
| TSJE 2018 final results (Tribunal Superior de Justicia Electoral) | Outcome margin +3.70 pp; department participation rates; roll counts by department | Module A calibration targets; Module C posterior anchor; README claim verification |
| DGEEC 2012 Census / 2018 estimates | Rural share ≈ 38.3%; bilingualism ≈ 27.6% Guaraní-dominant; age structure | Module A entity generation priors; rural flag calibration |
| INE 2018 ICT Household Survey | Internet access ≈ 73.4% urban / 27.9% rural; WhatsApp penetration proxies | Module A `internet_access_flag`; Module B reach caps for digital channels |
| BCP (Banco Central del Paraguay) 2018Q1 FX corridor | USD/PYG reference rate ≈ 5,000; retail spread band ≤ 0.5% | Module B `fx_layer`; `schema_contracts/bcp_tc_ref_daily_2018Q1.csv` |

---

## How to Use This Document

1. **Before citing a number**, check which row covers the artifact that produced it. If the status is ILLUSTRATIVE or SIMULATED, the claim should be framed as "the model produces…" or "structurally, the system demonstrates…" — not "the model predicts…" or "historical data shows…".

2. **For hiring reviewers:** The VERIFIED and CALIBRATED rows are the credibility substrate of the portfolio. The SIMULATED and ILLUSTRATIVE rows demonstrate engineering and methodological sophistication — they are intentionally marked as such to show that the author distinguishes between what is proven and what is demonstrated.

3. **Upgrading a row:** Move a SIMULATED row to CALIBRATED by obtaining real sub-national survey or administrative microdata and validating against it under a held-out gate. Move ILLUSTRATIVE to CALIBRATED by adding walk-forward validation (T9-1) with real coverage metrics.

4. **Boundary violations:** If any sentence in the README, model cards, or Quarto reports implies a stronger inferential status than the row above, rewrite it to match this register or escalate the status here with supporting evidence.

---

*Last updated: 2026-05-14. Linked from README.md §Epistemic calibration.*
