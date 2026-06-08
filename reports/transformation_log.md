# Transformation Log

Records every cleaning step: what it does, why it exists, QA checkpoint.

---

## Module A — 14-step cleaning pipeline

**Implementation status:** Steps 1–11, 13–14 fully coded and passing tests. Step 12 uses synthetic defaults (not actual NBI table data).
Source: `module_a_population_segmentation/src/population_segmentation/data/cleaner.py`

Verification: `poetry run pytest module_a_population_segmentation/tests/ -q` → 116 passed (2026-05-12).

| Step | Status | Operation | Rationale | QA checkpoint |
|------|--------|-----------|-----------|---------------|
| 1 | **Implemented** | **Encoding normalization** — detect source encoding with chardet; decode to UTF-8; tag `enc_source` | Original TSJE CSV exports were Windows-1252; re-typed files were UTF-8; mixing caused garbled ñ, á, é characters that corrupt geographic normalization in step 4 | Zero garbled characters in output; `enc_source` populated for 100% of rows |
| 2 | **Implemented** | **Cédula format standardization** — apply regex `^\d{7,8}$`; zero-pad 7-digit to 8 digits; flag `cedula_invalid = True` for non-conforming | Original registry used both 7-digit and 8-digit formats across departments; without standardization, fuzzy dedup in step 5 produces false positives | `cedula_invalid` rate < 2%; no null cédulas in output |
| 3 | **Implemented** | **Gender normalization** — map all observed variants {M, F, Masculino, Femenino, 1, 2} to canonical {M, F, unknown} via lookup table | Multiple offices used different conventions from different Excel export periods | Zero unmapped gender values; `unknown` rate < 0.5% |
| 4 | **Implemented** | **Geographic dictionary normalization** — fuzzy-match `department` and `municipality` free text against canonical TSJE list using RapidFuzz Levenshtein (threshold ≤ 2) | Free-text entry produced "Cordilera", "Caaguazu", "Misione" variants; these break downstream stratification | All department names match canonical 18-item list; municipality null rate post-imputation < 3% |
| 5 | **Implemented** | **Fuzzy deduplication** — block by `department`; within blocks, compute Jaro-Winkler similarity on (cedula_normalized, name_normalized, dob_normalized); collapse matches above threshold 0.92 | Multiple regional offices independently entered overlapping entity subsets with minor name-spelling differences | Duplicate collapse count logged; deduplication reduces N by 0.5–2% |
| 6 | **Implemented** | **Date format standardization** — detect DD/MM/YYYY vs MM/DD/YYYY using rule-based classifier; flag ambiguous cases where day ≤ 12; derive `age_on_event_date` as integer years on April 22, 2018 | Two regional offices used US-locale Excel settings (MM/DD/YYYY); undetected, this produces age errors of ~months to ~years | Zero derived ages < 18 or > 115 after standardization; `dob_ambiguous` rate < 1% |
| 7 | **Implemented** | **Age range enforcement** — require `age_on_event_date` ∈ [18, 115]; flag `age_out_of_range = True`; exclude from modeling layer | Age errors from step 6 produce out-of-range values that would corrupt the youth cohort calibration anchor | Zero records with `age_on_event_date` < 18 in clean modeling layer |
| 8 | **Implemented** | **Municipality imputation** — for null municipality, draw from empirical distribution conditioned on department; tag `municipality_imputed = True` | ~8% of records had blank municipality; null municipality blocks step 4 geographic normalization and downstream routing | Post-imputation null rate < 0.1% |
| 9 | **Implemented** | **Phone canonicalization** — normalize to E.164 format (+595XXXXXXXXX); flag `phone_invalid = True` | Three coexisting formats across regional offices; does not affect core modeling but required for Module B direct outreach channel scoring | `phone_invalid` rate logged; no normalization errors introduced |
| 10 | **Implemented** | **Rural flag derivation** — join municipality to DGEEC urban/rural classification table; flag `rural_flag_derived = True` | `rural_flag` is not in the original TSJE registry; it must be derived from municipality-to-classification lookup. Required for all demographic stratification | 100% coverage; no null `rural_flag` in clean layer |
| 11 | **Implemented** | **Language bucket assignment** — assign `language_census_bucket` using conditional probabilistic model fit to DGEEC bilingualism statistics by `rural_flag` × `department`; rake joint distribution to national marginals ±1 pp | Language is not in the TSJE registry; synthetic assignment calibrated to DGEEC statistics. Required for module B language-aware channel scoring | Language marginals within ±1 pp of anchors (Jopará 46%, Guaraní-only 34%, Spanish-only 15%) |
| 12 | **Implemented** | **Structural dependency proxy** — assign `structural_dependency_proxy` using NBI-grounded priors by `department` × `rural_flag`; elevated probability for San Pedro, Caazapá, Canindeyú rural strata | NBI data from DGEEC Censo 2012 provides baseline for socioeconomic dependency; required for segmentation and allocation prioritization. `[ESTIMATED]` — exact table identifiers pending | Department × rural strata coverage 100%; global prevalence within documented prior bounds |
| 13 | **Implemented** | **Internet access flag** — assign `internet_access_flag` using conditional Bernoulli draws calibrated to 73.4% urban / 27.9% rural ICT survey anchors | Internet penetration determines digital channel reachability; required for reachability features and Module B channel caps | Urban/rural marginals within ±2 pp of verified anchors |
| 14 | **Implemented** | **QA report generation** — compute and log all pipeline statistics; validate all calibration anchors; raise `QAGateFailure` if any gate fails | Every pipeline run must produce a traceable quality record; failures halt the pipeline | All calibration anchors within tolerance; report saved to `reports/qa_report_YYYYMMDD.md` |

---

## Feature engineering — downstream of cleaning

Engineered features are produced by `src/population_segmentation/features/` after the clean parquet exits the pipeline above.

| Feature group | Status | Module |
|---------------|--------|--------|
| Demographic (age_bin, youth_flag, senior_flag, gender_encoded) | **Implemented** — `features/demographic.py` | A |
| Behavioral (preference_proxy_encoded, structural_dependency_encoded, interactions) | **Implemented** — `features/behavioral.py` | A |
| Reachability (digital, broadcast_tv, broadcast_radio, compound indices) | **Implemented** — `features/reachability.py` | A |
| Department logit offset (rake anchor for propensity) | **Implemented** — `models/propensity.py` | A |
| Segment labels + DBSCAN noise flag | **Implemented** — `models/segmentation.py` | A |
| Media reachability by segment (cross-module contract artifact) | **Implemented** — `data/segment_reachability_aggregate.py` | A→B |
