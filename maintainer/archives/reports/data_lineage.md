# Population dataset — lineage (Module A)

```mermaid
flowchart TD
  subgraph verified [Verified_inputs]
    TSJE[TSJE_anchors]
    DGEEC[DGEEC_anchors]
  end
  subgraph synth [Synthetic_layers]
    GEN[Generator]
    INJ[Raw_injector]
  end
  CLN[Cleaner_14_steps]
  FEAT[Feature_modules]
  SEG[Segmentation_k6]
  PROP[Participation_propensity]
  EXP[Contract_exports]

  TSJE --> GEN
  DGEEC --> GEN
  GEN --> INJ
  INJ --> CLN
  CLN --> FEAT
  FEAT --> SEG
  FEAT --> PROP
  SEG --> EXP
  PROP --> EXP
```

**Code map**

| Stage | Entry |
|-------|--------|
| Generate | `population_segmentation.data.generator` |
| Inject flaws | `population_segmentation.data.raw_injector` |
| Clean | `population_segmentation.data.cleaner` |
| Features | `population_segmentation.features.*` |
| Segment | `population_segmentation.pipeline.models.segmentation` |
| Propensity | `population_segmentation.pipeline.models.propensity` |
| Export | `population_segmentation.pipeline.export` |

Artifacts consumed by Module B are emitted under `schema_contracts/` names (`population_master_clean`, `segment_labels`, `participation_propensity`, reachability CSVs).
