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
| `pct_rural`                     | float32 | Aggregated | Share with rural_flag = True                                     |
| `pct_jopara`                    | float32 | Aggregated | Share with jopara_flag = True                                    |
| `pct_structural_dependency`     | float32 | Aggregated | Share with structural_dependency_proxy = True                    |
| `dominant_department`           | string  | Mode       | Modal department for this segment                                |
| `primary_reach_channel`         | string  | Derived    | Channel with highest mean penetration (tv/radio/whatsapp/direct) |


