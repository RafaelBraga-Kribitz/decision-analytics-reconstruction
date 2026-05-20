---
doc_id: DOC-RPT-011
doc_type: specification
doc_role: derived
visibility: public
status: active
owner: project
last_reviewed: '2026-05-20'
canonical_source:
- DOC-SCH-001
- DOC-ARCH-001
derived_from:
- DOC-SCH-001
supersedes: null
tags: []
allowed_content:
- interpretation
- summarization
forbidden_content:
- novel_metrics
---

# Module A model and stage I/O specification

Column names in **Constant** refer to `module_a_population_segmentation/src/population_segmentation/utils/schema.py` where the symbol exists. Dtypes follow `schema_contracts/*.yaml` and export code; this is a human-facing index, not a substitute for Pandera checks.

## Stage A — Clean population layer (post-cleaner, pre-export enrichments)

**Input:** Raw parquet from `population_segmentation.data.raw_injector.inject_flaws`.  
**Transforms:** `population_segmentation.data.cleaner.clean_population` (+ QA directory outputs under `--out-dir`).  
**Authoritative contract:** `schema_contracts/population_master_clean.yaml`.

Representative fields (see YAML for full list):

| Field concept | Schema constant | Dtype (contract) |
|---------------|-----------------|------------------|
| Primary key | `ENTITY_ID` | int64 |
| Geography | `DEPARTMENT`, `MUNICIPALITY` | string |
| Participation modeling age | `AGE_ON_EVENT_DATE` | int16 |
| Preference narrative | `PREFERENCE_PROXY`, `PREFERENCE_PROXY_STRENGTH` | string / float |
| Participation score column shell | `PARTICIPATION_PROPENSITY` | float32 (filled later in export merge) |

## Stage B — Feature engineering (`FEATURE_COLUMNS` segmentation input)

**Input:** Clean DataFrame.  
**Transforms:** `build_demographic_features` → `build_behavioral_features` → `build_reachability_features` (chain used in `run_export`).  
**Implementation:** `population_segmentation/features/demographic.py`, `behavioral.py`, `reachability.py`.

Segmentation matrix columns (`population_segmentation.pipeline.models.segmentation.FEATURE_COLUMNS`):

| Column | Role |
|--------|------|
| `age_bin_encoded`, `gender_encoded`, `youth_flag`, `metro_flag` | Demographics + geography encoding |
| `rural_flag`, `preference_proxy_encoded`, `preference_proxy_strength`, `structural_dependency_encoded` | Behavioral proxies |
| `reachability_digital`, `reachability_broadcast_tv`, `reachability_broadcast_radio`, `reachability_index`, `reachability_tier` | Channel feasibility composites |
| `language_jopara_encoded`, `nbi_stress_prior_scaled` | Language / stress scaling |

## Stage C — Segmentation

**Input:** Feature frame (`FEATURE_COLUMNS`).  
**Model:** `DBSCANNoiseFilter` + `KMeansSegmenter` (`population_segmentation.pipeline.models.segmentation`).  
**Output:** `segment_labels.parquet` per `schema_contracts/segment_labels.yaml`.

| Output column | Constant |
|---------------|----------|
| `entity_id` | `ENTITY_ID` |
| `segment_label` | `SEGMENT_LABEL` |
| `segment_id` | `SEGMENT_ID` |
| `dbscan_noise_flag` | `DBSCAN_NOISE_FLAG` |

## Stage D — Participation propensity

**Input:** Feature frame + segmentation columns merged + `calibration_anchors.yaml`.  
**Model:** `PropensityModel` (`population_segmentation.pipeline.models.propensity`).  
**Output:** `participation_propensity.parquet` per `schema_contracts/participation_propensity.yaml`.

Classifier features (`FEATURES` in propensity module) plus engineered offsets inside `_feature_matrix`:

| Column | Notes |
|--------|------|
| Base features | `age_bin_encoded`, `gender_encoded`, `rural_flag`, `youth_flag`, `senior_flag`, `metro_flag`, `structural_dependency_encoded`, `preference_proxy_strength`, `internet_access_flag` |
| Derived in matrix | `department_logit_offset`, `gender_youth_interaction` (not separate schema constants; documented in model card) |

## Aggregates and sidecar files

| Artifact | Producer | Contract |
|----------|----------|----------|
| `media_reachability_by_segment.csv` | `aggregate_media_reachability_by_segment` | `schema_contracts/media_reachability_by_segment.yaml` |
| `media_reachability_by_segment_department.csv` | `aggregate_media_reachability_by_segment_department` | `schema_contracts/media_reachability_by_segment_department.yaml` |
| `population_master_clean.parquet` | Export merge of features + labels + propensity | `schema_contracts/population_master_clean.yaml` |
| `model_run_manifest.json` | `population_segmentation.pipeline.model_run_manifest` | Informational provenance (not a Pandera gate) |

## Code index

- `module_a_population_segmentation/src/population_segmentation/pipeline/export.py` — orchestrates all stages.
- `module_a_population_segmentation/src/population_segmentation/utils/schema.py` — canonical column symbols.
