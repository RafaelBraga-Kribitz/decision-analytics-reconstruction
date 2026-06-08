# Feature engineering justification — Module A

Each row explains **why** a column exists, **how** it is built, and **how** it is checked. Participation propensity and segmentation consume overlapping but not identical subsets—see [`reports/module_a_model_io_spec.md`](module_a_model_io_spec.md).

## Demographic features (`build_demographic_features`)

| Column | Why | Construction | Validation |
|--------|-----|--------------|------------|
| `age_bin` | Stable categorical cohorts for clustering + stratification | Bucket `AGE_ON_EVENT_DATE` into five bins | Implicit via dtype / export QA |
| `age_bin_encoded` | Ordinal encoding for ML | Map bins to 0–4 | Used in `FEATURE_COLUMNS` / propensity `FEATURES` |
| `gender_encoded` | Numeric gender signal | M→1, F→0, unknown→0.5 | Stratification columns |
| `youth_flag` | Youth participation dynamics | Age 18–24 boolean | Propensity + segmentation |
| `senior_flag` | Older cohort behavior | Age ≥ 65 | Propensity features |
| `chaco_flag`, `department_region` | Regional heterogeneity | CHACO department set | Interpretability |
| `metro_flag` | Urban concentration proxy | Central / Asuncion | Segmentation / propensity |

## Behavioral features (`build_behavioral_features`)

| Column | Why | Construction | Validation |
|--------|-----|--------------|------------|
| `preference_proxy_encoded` | Ordinal stance from categorical preference proxy | Map A/B/other/none → ints | Range checks via downstream models |
| `structural_dependency_encoded` | Socioeconomic stress signal | Cast structural dependency proxy | Used in segmentation matrix |
| `nbi_stress_prior_scaled` | Normalize stress prior across entities | Min–max scale within batch | Division guarded when degenerate |
| `language_jopara_encoded`, `language_guarani_flag` | Language mix indicators | From `JOPARA_FLAG`, census bucket | Segment separation |

## Reachability features (`build_reachability_features`)

| Column | Why | Construction | Validation |
|--------|-----|--------------|------------|
| `reachability_digital` | Digital persuasion feasibility | `internet_access_flag × media_penetration_whatsapp` | Clipped downstream |
| `reachability_broadcast_tv`, `reachability_broadcast_radio` | Broadcast penetration proxies | Direct penetration columns | Used in segmentation PCA space |
| `reachability_index` | Composite channel access score | Weighted mix 0.40/0.35/0.25, clipped [0,1] | Drives `reachability_tier` |
| `reachability_tier` | Low/med/high buckets | Quantile splits on index | Categorical interpretability |
| `urban_digital_compound`, `rural_offline_compound` | Interaction flags | Boolean composites | Narrative segments |

## Segmentation-only columns

See `FEATURE_COLUMNS` in `population_segmentation.pipeline.models.segmentation` — thirteen standardized inputs to PCA(5) before DBSCAN + KMeans (`random_state=42`).

## Propensity-only extensions

Inside `PropensityModel._feature_matrix`, **`department_logit_offset`** encodes department-level participation-rate anchors as a logit prior; **`gender_youth_interaction`** captures encoded gender × youth. Both are documented in [`module_a_population_segmentation/reports/model_card_propensity.md`](../module_a_population_segmentation/reports/model_card_propensity.md).

## Automated checks

- Export exit gate: `_validate_export_contracts` in `population_segmentation.pipeline.export`.
- Integration suite: `module_a_population_segmentation/tests/test_export_artifacts.py` (full artifact shapes at `sample_size=15_000`).
