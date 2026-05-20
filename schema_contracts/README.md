---
doc_id: DOC-SCH-001
doc_type: specification
doc_role: canonical
visibility: public
status: active
owner: architecture
last_reviewed: '2026-05-20'
canonical_source: null
derived_from: null
supersedes: null
tags: []
---

# Schema Contracts

This directory contains YAML schema contracts for all datasets shared across modules.
Each contract is the **authoritative source of truth** for field names, types, validation
rules, and downstream consumers.

Validation is enforced in `validator.py` at pipeline runtime.
A `QAGateFailure` exception is raised — never a warning — if any contract is violated.

## Module A outputs (produced here; consumed downstream)


| Contract file                                       | Dataset                                                                          | Consumed by            |
| --------------------------------------------------- | -------------------------------------------------------------------------------- | ---------------------- |
| `population_master_raw.yaml`                        | Raw synthetic population with injected flaws                                     | Module A cleaner       |
| `population_master_clean.yaml`                      | Cleaned, validated population + features + scores                                | **Module B, Module C** |
| `segment_labels.yaml`                               | K-Means segment assignments (one row per entity)                                 | **Module B, Module C** |
| `participation_propensity.yaml`                     | Platt-calibrated propensity scores (one row per entity)                          | **Module B, Module C** |
| `media_reachability_by_segment.yaml`                | National segment-level rollup (1 row per segment, k=6) — diagnostic only         | **Module B, Module C** |
| `media_reachability_by_segment_department.yaml`     | Segment-by-department companion (1 row per (segment, department), 6 * 18 = 108) | **Module B**           |

## Module B outputs (produced downstream; consumed by Module C and reporting)


| Contract file                          | Dataset                                                                       | Consumed by             |
| -------------------------------------- | ----------------------------------------------------------------------------- | ----------------------- |
| `reachability_caps_dept_channel.yaml`  | Department×channel reach caps with salience, attention, eligibility, costs    | Module B LP/MILP        |
| `routing_cost_matrix.yaml`             | Department×department travel-time matrix per routing scenario                 | Module B TSP heuristic  |
| `allocation_output.yaml`               | Weekly allocation rows (department × channel × week) with FX + persuasion     | **Module C**, reporting |
| `reallocation_counterfactuals.yaml`    | Broadcast-to-direct deltas per grid cell (contacts + budget vs baseline)      | **Module C**, reporting |


## Module C inputs and scenario artifacts


| Contract file                              | Dataset                                           | Consumed by        |
| ------------------------------------------ | ------------------------------------------------- | ------------------ |
| `polls_raw_press_release.yaml`             | Dirty press-extracted survey rows                 | Module C ETL       |
| `polls_clean_tracking_wave.yaml`           | Cleaned tracking waves + transparency fields      | Module C PyMC      |
| `polls_clean_exit_wave.yaml`               | Exit / quick-count cleaned rows (separate stage)  | Module C exit PyMC |
| `house_effect_seed_matrix.yaml`            | Warm-start table for pollster offsets             | Module C PyMC      |
| `monte_carlo_shock_catalog.yaml`           | Shock scores and scenario buckets                 | Module C MC        |
| `daily_posterior_forecast.yaml`            | Daily latent margin posterior summaries           | Module C viz       |
| `posterior_house_effects.yaml`             | Pollster house-effect posterior summaries         | Module C reports   |
| `battleground_department_probability.yaml` | Department win-probability map                    | Module C geo       |


## Version policy

Any breaking change to field names, types, or validation rules requires:

1. A version bump in the contract file (`schema_version` field)
2. An entry in `reports/decision_log.md`
3. Sign-off from `integration-impact-auditor`

## Reachability artifacts: grain discipline

- `media_reachability_by_segment.yaml` is **segment-only** (k=6 rows). It is a
  national diagnostic rollup; `dominant_department` is a descriptive summary
  column, not a row key.
- `media_reachability_by_segment_department.yaml` is the authoritative grain
  for **(segment, department)** caps consumed by Module B's LP/MILP. Module B
  MUST NOT reinterpret the segment-only artifact as a per-department cap source.