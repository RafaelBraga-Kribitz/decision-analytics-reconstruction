---
doc_id: DOC-DICT-001
doc_type: specification
doc_role: derived
visibility: public
status: active
owner: portfolio
last_reviewed: '2026-05-20'
canonical_source: &id001
- DOC-SCH-001
- DOC-CHARTER-001
derived_from: *id001
supersedes: null
tags: []
allowed_content:
- interpretation
- summarization
forbidden_content:
- novel_metrics
---

# Data Dictionary

Every field across all modules: type, source, validation rule, business meaning.

---

## Module A — `population_master_clean.parquet`


| Field                         | Type    | Source                       | Validation rule                                                 | Business meaning                                                                            |
| ----------------------------- | ------- | ---------------------------- | --------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| `entity_id`                   | int64   | Generated                    | Unique, non-null, monotonic                                     | Primary key across all modules                                                              |
| `cedula`                      | string  | TSJE (cleaned)               | Regex `^\d{8}$`, non-null                                       | National identity number; deduplication key                                                 |
| `cedula_invalid`              | bool    | Cleaning step 2              | Non-null                                                        | True if failed regex format check; QA audit flag                                            |
| `department`                  | string  | TSJE (normalized)            | Member of 18-item canonical list                                | Administrative department; geographic stratification                                        |
| `municipality`                | string  | TSJE (normalized or imputed) | Non-null after imputation                                       | Municipality; geographic stratification                                                     |
| `municipality_imputed`        | bool    | Cleaning step 8              | Non-null                                                        | True if municipality was imputed from department distribution                               |
| `age_on_event_date`           | int16   | Derived from `dob`           | ≥ 18, ≤ 115, non-null                                           | Age in integer years on April 22, 2018 (outcome event date)                                 |
| `age_out_of_range`            | bool    | Cleaning step 7              | Non-null                                                        | True if derived age was outside [18, 115]; excluded from modeling                           |
| `dob_ambiguous`               | bool    | Cleaning step 6              | Non-null                                                        | True if date format could not be deterministically resolved                                 |
| `gender`                      | string  | TSJE (normalized)            | Member of {M, F, unknown}                                       | Gender; M ~50.4%, F ~49.6% (DGEEC 2018)                                                     |
| `rural_flag`                  | bool    | DGEEC lookup, derived        | Non-null                                                        | True ~38.3% (rural); False ~61.7% (urban)                                                   |
| `rural_flag_derived`          | bool    | Cleaning step 10             | Non-null, always True                                           | Confirms rural_flag is always derived (never from raw)                                      |
| `language_census_bucket`      | string  | DGEEC calibration            | Member of {jopara_bilingual, guarani_only, spanish_only, other} | Language group; calibrated to DGEEC bilingualism statistics                                 |
| `jopara_flag`                 | bool    | Derived                      | Non-null                                                        | True iff language_census_bucket == jopara_bilingual                                         |
| `preference_proxy`            | string  | Probabilistic model          | Member of {A, B, other, none}                                   | Preference proxy; calibrated to department × urban/rural historical share                   |
| `preference_proxy_strength`   | float32 | Propensity model             | [0.0, 1.0], non-null                                            | Strength of preference proxy signal                                                         |
| `participation_propensity`    | float32 | Logistic + Platt + dept rake | [0.0, 1.0], non-null; mean ~0.6125                              | Calibrated P(participates). Used as allocation weight (B) and strata weight (C)             |
| `structural_dependency_proxy` | bool    | NBI-grounded priors × dept   | Non-null                                                        | True for entities in high-NBI strata; San Pedro, Caazapá, Canindeyú rural elevated          |
| `internet_access_flag`        | bool    | Conditional Bernoulli, ICT   | Non-null                                                        | True ~73.4% urban, ~27.9% rural; determines digital channel reachability                    |
| `media_penetration_tv`        | float32 | Department-level lookup      | [0.0, 1.0], non-null                                            | Household TV penetration by department (~0.89 national)                                     |
| `media_penetration_radio`     | float32 | Department-level lookup      | [0.0, 1.0], non-null                                            | Household radio penetration by department                                                   |
| `media_penetration_whatsapp`  | float32 | Dept × urban/rural lookup    | [0.0, 1.0], non-null                                            | WhatsApp penetration (urban higher, rural lower)                                            |
| `media_penetration_facebook_ads` | float32 | Q1 2018 LATAM benchmark, dept × urban/rural | [0.0, 1.0], non-null | Facebook News Feed reach (urban 0.45, rural 0.12); digital advertising channel |
| `media_penetration_instagram_ads` | float32 | Q1 2018 LATAM benchmark, dept × urban/rural | [0.0, 1.0], non-null | Instagram reach (urban 0.42, rural 0.08); digital advertising channel |
| `media_penetration_google_ads` | float32 | Q1 2018 LATAM benchmark, dept × urban/rural | [0.0, 1.0], non-null | Google Search + Display reach (urban 0.38, rural 0.10); digital advertising channel |
| `media_penetration_linkedin_ads` | float32 | Q1 2018 LATAM benchmark, dept × urban/rural | [0.0, 1.0], non-null | LinkedIn professional targeting (urban 0.12, rural 0.02); digital advertising channel |
| `nbi_stress_prior`            | float32 | NBI module, DGEEC 2012       | [0.0, 1.0]; **ESTIMATED**                                       | Socioeconomic stress prior; rural ~0.659 sanitary anchor; ESTIMATED until granular NBI mesh |
| `segment_label`               | string  | K-Means output               | Member of 6-label set, nullable                                 | Population segment assignment; null until segmentation step runs                            |
| `ballot_blank_president`      | bool    | Participation model          | Non-null; rate ~2.41%                                           | Synthetic blank/null ballot indicator for presidential race                                 |
| `ballot_blank_parlasur`       | bool    | Participation model          | Non-null; rate ~8.48%                                           | Synthetic blank/null ballot indicator for Parlasur (higher roll-off rate)                   |
| `enc_source`                  | string  | Cleaning step 1              | Member of {windows1252, utf8, unknown}                          | Encoding provenance of source record                                                        |


---

## Module A — `segment_labels.parquet`


| Field               | Type   | Source          | Validation rule     | Business meaning                                         |
| ------------------- | ------ | --------------- | ------------------- | -------------------------------------------------------- |
| `entity_id`         | int64  | FK to clean     | Unique, non-null    | Foreign key to population_master_clean                   |
| `segment_label`     | string | K-Means         | 6 allowed values    | Named segment; consumed by Module B as allocation target |
| `segment_id`        | int8   | K-Means         | [0, 7]              | Numeric segment index                                    |
| `dbscan_noise_flag` | bool   | DBSCAN pre-pass | Non-null; < 1% rate | True if flagged as noise; excluded from K-Means input    |


---

## Module A — `participation_propensity.parquet`


| Field                        | Type    | Source               | Validation rule          | Business meaning                                                     |
| ---------------------------- | ------- | -------------------- | ------------------------ | -------------------------------------------------------------------- |
| `entity_id`                  | int64   | FK to clean          | Unique, non-null         | Foreign key to population_master_clean                               |
| `participation_propensity`   | float32 | PropensityModel      | [0.0, 1.0]; mean ~0.6125 | Calibrated participation probability; allocation weight for Module B |
| `raw_logit_score`            | float32 | Logistic regression  | Any real value           | Pre-calibration logit score; for model diagnostics                   |
| `department_rake_multiplier` | float32 | Department rake step | > 0                      | Rake factor applied post-Platt; stored for transparency              |


---

## Module A — `media_reachability_by_segment.csv`


| Field                           | Type    | Source     | Business meaning                                                 |
| ------------------------------- | ------- | ---------- | ---------------------------------------------------------------- |
| `segment_label`                 | string  | K-Means    | One row per segment (6 rows total)                               |
| `segment_size`                  | int64   | Aggregated | Count of entities in segment                                     |
| `segment_size_pct`              | float32 | Aggregated | Share of total population                                        |
| `mean_participation_propensity` | float32 | Aggregated | Mean calibrated propensity for this segment                      |
| `pct_internet_access`           | float32 | Aggregated | Share with internet_access_flag = True                           |
| `mean_tv_penetration`           | float32 | Aggregated | Mean media_penetration_tv for this segment                       |
| `mean_radio_penetration`        | float32 | Aggregated | Mean media_penetration_radio for this segment                    |
| `mean_whatsapp_penetration`     | float32 | Aggregated | Mean media_penetration_whatsapp for this segment                 |
| `mean_facebook_ads_penetration` | float32 | Aggregated | Mean media_penetration_facebook_ads for this segment (T10 digital channels) |
| `mean_instagram_ads_penetration` | float32 | Aggregated | Mean media_penetration_instagram_ads for this segment (T10 digital channels) |
| `mean_google_ads_penetration`   | float32 | Aggregated | Mean media_penetration_google_ads for this segment (T10 digital channels) |
| `mean_linkedin_ads_penetration` | float32 | Aggregated | Mean media_penetration_linkedin_ads for this segment (T10 digital channels) |
| `pct_rural`                     | float32 | Aggregated | Share with rural_flag = True                                     |
| `pct_jopara`                    | float32 | Aggregated | Share with jopara_flag = True                                    |
| `pct_structural_dependency`     | float32 | Aggregated | Share with structural_dependency_proxy = True                    |
| `dominant_department`           | string  | Mode       | Modal department for this segment                                |
| `primary_reach_channel`         | string  | Derived    | Channel with highest mean penetration (tv/radio/whatsapp/facebook_ads/instagram_ads/google_ads/linkedin_ads) |

---

## Module B — `allocation_output.parquet`

Resource allocation per (department, channel, week) cell. 2,772 rows (18 deps × 11 channels × 14 weeks). Solver output from PuLP/CBC MILP.

| Field | Type | Nullable | Example | Derivation Rule | Business Meaning |
|-------|------|----------|---------|-----------------|------------------|
| `department` | string | false | Asuncion | 18-item canonical list | Administrative region; geographic stratification |
| `channel` | string | false | tv_spots | 11 allowed values | Media/engagement channel |
| `channel_type` | string | false | broadcast | bilateral / broadcast / broadcast_to_bilateral / in_person | Channel communication mode |
| `week_index` | int8 | false | 1 | [1, 14] | 1-based week ordinal in Jan-Apr 2018 window |
| `iso_week` | string | false | 2018-W01 | Pattern ^2018-W[0-1][0-9]$ | ISO week label |
| `department_tier` | string | false | stronghold | {stronghold, swing, opposition, negligible} | Electoral tier classification |
| `region` | string | false | ORIENTAL | {ORIENTAL, CHACO} | Geographic region (east or west of Rio Paraguay) |
| `budget_allocation_usd` | float64 | false | 12500.00 | CBC solver, truncated to cents | Weekly USD spend for this cell |
| `budget_allocation_pyg` | float64 | false | 62500000.00 | USD × fx_rate | PYG equivalent of spend |
| `fx_tier` | string | false | REF | {REF, RETAIL} | Exchange rate tier applied (reference or retail) |
| `tc_rate_pyg_per_usd` | float32 | false | 5000.0 | BCP daily rate or prior | Exchange rate used for USD→PYG conversion |
| `expected_contacts` | float64 | false | 125000.0 | Population × reach_cap × unit_cost | Raw contacts from spend at face value |
| `persuasion_adjusted_contacts` | float64 | false | 102500.0 | contacts × attention × salience × hostility × scenario_weight × tier_penalty | Persuasion-weighted contacts (objective term) |
| `reach_cap_population_proxy` | float64 | false | 500000.0 | Population × channel reach cap | Reachable audience ceiling for this cell |
| `reach_utilization` | float32 | false | 0.25 | expected_contacts / reach_cap; capped at 1.5 | Proportion of audience reached (0–1.5 when saturation active) |
| `binding_constraint` | string | true | budget_upper | Constraint name or null | Which LP constraint is binding at this row (if any) |
| `bundle_id` | string | true | conglomerate_x | CHANNEL_TO_BUNDLE lookup or null | Conglomerate bundle membership if applicable |
| `scenario_id` | string | false | baseline | {baseline, early_lock, late_flex, broadcast_to_direct} | Scenario tag |
| `solver_status` | string | false | OPTIMAL | {OPTIMAL, FEASIBLE} | CBC solver termination status |
| `solver_seed` | int32 | false | 20180422 | RandomSeed(seed) in CBC call | Deterministic seed for reproducibility |
| `schema_version_used` | string | false | 1.0.0 | Constant | Schema version identifier |

---

## Module C — `daily_posterior_forecast.parquet`

Daily posterior preference-margin distribution from Bayesian hierarchical tracking model. One row per (date, calibration_series). 142 rows (Jan 1 – Apr 22, 2018).

| Field | Type | Nullable | Example | Derivation Rule | Business Meaning |
|-------|------|----------|---------|-----------------|------------------|
| `date` | timestamp | false | 2018-04-22 | Campaign date range | Calendar date |
| `calibration_series` | string | false | A | {A, B} | Calibration series; A = valid-preference-proxy convention |
| `series_tag` | string | false | A | Echo of calibration_series | Series label |
| `posterior_mean_preference_margin_pp` | float64 | false | 3.70 | PyMC posterior samples, mean | Daily posterior mean margin (percentage points) |
| `posterior_hdi_low_pp` | float64 | false | 2.10 | PyMC posterior quantile(0.025) | 95% HDI lower bound (pp) |
| `posterior_hdi_high_pp` | float64 | false | 5.30 | PyMC posterior quantile(0.975) | 95% HDI upper bound (pp) |
| `model_version` | string | false | c_tracking_hierarchical_v0.1 | Constant versioning string | Tracking model version tag |

---

## Module C — `monte_carlo_draws.parquet`

Stratified Monte Carlo scenario draws. 10,000 rows (default; 600 when MC_FAST=1). One row per draw. All 3 canonical scenario buckets represented.

| Field | Type | Nullable | Example | Derivation Rule | Business Meaning |
|-------|------|----------|---------|-----------------|------------------|
| `draw_id` | int64 | false | 0 | Sequential 0..n-1 | Draw ordinal index |
| `poll_wave_id` | string | true | wave_20180410 | Source row from tracking or null | Poll wave identifier (null if synthesized) |
| `scenario_bucket` | string | false | baseline | {baseline, extreme_tracker, compounded_herd} | Canonical scenario bucket |
| `shock_scale` | float64 | false | 1.25 | expit(logit_transform) × multiplier | Engagement shock magnitude (post-multiplier) |
| `alloc_mean_persuasion_contacts` | float64 | false | 500000.0 | allocation_output.mean() or 0.0 | Mean persuasion-adjusted contacts from allocation (handshake) |
| `draw_source` | string | false | tracking_sample | {tracking_sample, synthetic_prior} | Whether draw is from tracking data or synthesized |

---

## Module C — `battleground_probability_heatmap.geojson`

Department-level posterior win probability with geometric boundaries. 18 features (one per Paraguay department). GeoJSON FeatureCollection with Polygon geometries.

| Property | Type | Example | Derivation Rule | Business Meaning |
|----------|------|---------|-----------------|------------------|
| `department` | string | Asuncion | 18-item canonical list | Department name |
| `posterior_win_prob` | float64 | 0.724 | expit(logit transform of national posterior + dept-level jitter) | Posterior win probability [0, 1] |
| `hdi_low` | float64 | 0.689 | expit(logit(HDI_low) + jitter) | 95% HDI lower bound on win probability |
| `hdi_high` | float64 | 0.756 | expit(logit(HDI_high) + jitter) | 95% HDI upper bound on win probability |
| `calibration_series` | string | A | Constant | Calibration series |
| `geometry` | Polygon | [...] | Approximate rectangular bounds per department | Department geographic boundary (simplified) |

