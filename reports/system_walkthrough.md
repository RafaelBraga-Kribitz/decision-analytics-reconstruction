---
doc_id: DOC-WALK-001
doc_type: walkthrough
doc_role: canonical
visibility: public
status: active
owner: portfolio
last_reviewed: '2026-05-20'
canonical_source: null
derived_from: null
supersedes: null
tags: []
---

# System walkthrough — one entity row (technical)

This path is the **code-oriented** complement to `reports/executive_demo_walkthrough.md` (stakeholder narrative).

## 1. Pick one entity

Assume `entity_id = 100042` after a local Module A export at `SAMPLE=50000` (any stable row works). The same `entity_id` appears in:

- `population_master_clean.parquet` (post-cleaner)
- `segment_labels.parquet`
- `participation_propensity.parquet`

## 2. Module A — build artifacts

```bash
make module-a-export SAMPLE=50000
```

Pipeline modules (under `module_a_population_segmentation/src/population_segmentation/`): generator → raw injector → cleaner → features → segmentation → propensity → `population_segmentation.pipeline.export`.

## 3. Module B — allocation row slice

The allocation table is **not keyed by entity**; it is keyed by `(department, channel, iso_week)`. To attach the entity, map `department_clean` on the entity to the allocation slice for that department:

```bash
make module-b-allocate SCENARIO=baseline SEED=20180422
# Optional sensitivity bundle (duals + budget expansion curve + run report):
poetry run python -m module_b_resource_allocation.pipeline.run_allocation \
  --scenario baseline --out-dir data/processed/module_b --seed 20180422 --sensitivity
```

Inspect `data/processed/module_b/allocation_baseline.csv` filtered to the entity’s department.

## 4. Module C — survey measurement track

```bash
MC_FAST=1 poetry run python -m module_c_forecasting_scenarios.pipeline.run_tracking \
  --raw-csv module_c_forecasting_scenarios/tests/fixtures/polls_raw_fixture.csv \
  --out-dir data/processed/module_c/tracking
```

The fixture exercises the hierarchical preference-proxy tracker and emits posterior tables under `data/processed/module_c/tracking/` (see `module_c_forecasting_scenarios` README for exact filenames on your run).

## 5. Contract sources of truth

Cross-module columns: `schema_contracts/*.yaml` and `reports/module_b_module_c_handshake.md`.
