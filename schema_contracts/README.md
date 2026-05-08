# Schema Contracts

This directory contains YAML schema contracts for all datasets shared across modules.
Each contract is the **authoritative source of truth** for field names, types, validation
rules, and downstream consumers.

Validation is enforced in `validator.py` at pipeline runtime.
A `QAGateFailure` exception is raised — never a warning — if any contract is violated.

## Module A outputs (produced here; consumed downstream)


| Contract file                        | Dataset                                                  | Consumed by            |
| ------------------------------------ | -------------------------------------------------------- | ---------------------- |
| `population_master_raw.yaml`         | Raw synthetic population with injected flaws             | Module A cleaner       |
| `population_master_clean.yaml`       | Cleaned, validated population + features + scores        | **Module B, Module C** |
| `segment_labels.yaml`                | K-Means segment assignments (one row per entity)         | **Module B, Module C** |
| `participation_propensity.yaml`      | Platt-calibrated propensity scores (one row per entity)  | **Module B, Module C** |
| `media_reachability_by_segment.yaml` | Aggregated reachability by segment (one row per segment) | **Module B**           |


## Version policy

Any breaking change to field names, types, or validation rules requires:

1. A version bump in the contract file (`schema_version` field)
2. An entry in `reports/decision_log.md`
3. Sign-off from `integration-impact-auditor`