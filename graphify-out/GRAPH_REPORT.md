# Graph Report - PARAGUAY_ELLECTION  (2026-05-07)

## Corpus Check
- 62 files · ~46,521 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 586 nodes · 609 edges · 46 communities (36 shown, 10 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 58 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `5e046279`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]

## God Nodes (most connected - your core abstractions)
1. `generate_population()` - 18 edges
2. `Decision Analytics Reconstruction — Master Scope Document` - 15 edges
3. `Module C — Probabilistic Forecasting and Scenario Research Engine` - 14 edges
4. `inject_flaws()` - 13 edges
5. `Module A — Population Modeling and Segmentation System` - 13 edges
6. `Module B — Resource Allocation Engine` - 13 edges
7. `TestFlawTypes` - 12 edges
8. `_build_sample()` - 11 edges
9. `Harness checklists` - 11 edges
10. `10. Shared Engineering Standards` - 11 edges

## Surprising Connections (you probably didn't know these)
- `raw_population()` --calls--> `generate_population()`  [INFERRED]
  module_a_population_segmentation/tests/test_generator.py → module_a_population_segmentation/src/population_segmentation/data/generator.py
- `_build_sample()` --calls--> `generate_population()`  [INFERRED]
  module_a_population_segmentation/app/streamlit_dashboard.py → module_a_population_segmentation/src/population_segmentation/data/generator.py
- `_build_sample()` --calls--> `inject_flaws()`  [INFERRED]
  module_a_population_segmentation/app/streamlit_dashboard.py → module_a_population_segmentation/src/population_segmentation/data/raw_injector.py
- `_build_sample()` --calls--> `KMeansSegmenter`  [INFERRED]
  module_a_population_segmentation/app/streamlit_dashboard.py → module_a_population_segmentation/src/population_segmentation/models/segmentation.py
- `_build_sample()` --calls--> `PropensityModel`  [INFERRED]
  module_a_population_segmentation/app/streamlit_dashboard.py → module_a_population_segmentation/src/population_segmentation/models/propensity.py

## Communities (46 total, 10 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.04
Nodes (47): 10-minute evaluation guide (required in top-level README), 10. Shared Engineering Standards, 11. Engineering Quality Gates, 12. Terminology Compliance, 13. Open Evidence Gaps, 1. Project Identity, 2. Honest Narrative, 3. Selected Calibration Anchors (+39 more)

### Community 1 - "Community 1"
Cohesion: 0.04
Nodes (45): 10. GitHub Structure (Module C), 11. Documentation Package (Module C), 12. Engineering Quality Gates (Module C), 13.1 High-risk field name replacements, 13.2 Narrative framing rules, 13.3 Internal naming conventions, 13. Terminology Compliance (Module C), 1. Project Identity (+37 more)

### Community 2 - "Community 2"
Cohesion: 0.05
Nodes (31): _add_raw_fields(), _garble_encoding(), _generate_names(), inject_flaws(), _randomize_phone_format(), Deterministic flaw injection layer.  Injects all 13 flaw types from scope §4.2 i, Add fields that exist in the raw layer but not the clean generator output., Add fields that exist in the raw layer but not the clean generator output. (+23 more)

### Community 3 - "Community 3"
Cohesion: 0.04
Nodes (44): 10. Documentation Package (Module A), 11. Engineering Quality Gates (Module A), 12.1 High-risk field name replacements, 12.2 Narrative framing rules, 12.3 Internal naming conventions, 12. Terminology Compliance (Module A), 1. Project Identity, 2. Honest Narrative (Module-Specific) (+36 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (41): 10. Documentation Package (Module B), 11. Engineering Quality Gates (Module B), 12.1 High-risk field name replacements, 12.2 Narrative framing rules, 12.3 Internal naming conventions, 12. Terminology Compliance (Module B), 1. Project Identity, 2. Honest Narrative (Module-Specific) (+33 more)

### Community 5 - "Community 5"
Cohesion: 0.06
Nodes (29): _build_sample(), _load_cfg(), main(), Module A Streamlit dashboard (three tabs)., build_behavioral_features(), Behavioral feature engineering for Module A., build_demographic_features(), Demographic feature engineering for Module A. (+21 more)

### Community 6 - "Community 6"
Cohesion: 0.06
Nodes (22): TYP: gender field should have multiple representation variants., RNG: some derived age values should be <18 or >120 after DOB swap., RNG: some derived age values should be <18 or >120 after DOB swap., SCH: dataset should include a schema drift marker column., SCH: dataset should include a schema drift marker column., NUL: ~25% of qualitative_district should be null., NUL: ~25% of qualitative_district should be null., FMT: some cédulas should be 7-digit (missing zero-pad). (+14 more)

### Community 7 - "Community 7"
Cohesion: 0.08
Nodes (9): Tests for population_segmentation.data.generator.  TDD order: these tests are wr, raw_population(), TestAgeDistribution, TestDepartmentDistribution, TestEntityCount, TestGenderDistribution, TestLanguageDistribution, TestRequiredColumns (+1 more)

### Community 8 - "Community 8"
Cohesion: 0.11
Nodes (19): _assign_language(), _assign_municipalities(), generate_population(), _rake_binary(), _rake_categorical(), Synthetic population generator.  Produces a DataFrame of N synthetic entities ca, Generate a synthetic population DataFrame.      Args:         config: Generation, Generate a synthetic population DataFrame.      Args:         config: Generation (+11 more)

### Community 9 - "Community 9"
Cohesion: 0.09
Nodes (21): Allocation quality, Bayesian workflow quality, Calibration quality, Code quality, Code quality, Contract adherence, Cross-module — Professional output standard, Data quality (+13 more)

### Community 10 - "Community 10"
Cohesion: 0.16
Nodes (15): AnchorCheck, QAGateFailure, Schema and calibration validation gates for Module A., Raised when any QA gate fails., Raised when any QA gate fails., run_all_validations(), validate_calibration_anchors(), validate_schema() (+7 more)

### Community 11 - "Community 11"
Cohesion: 0.12
Nodes (15): Failure-path simulations (new — must block correctly), Happy-path simulations, Harness simulation tests, Pass criteria for harness health, SIM-01 — Module-only feature (Module A), SIM-02 — Cross-module schema change, SIM-03 — Solver bugfix (Module B), SIM-04 — Module C calibration gate (+7 more)

### Community 12 - "Community 12"
Cohesion: 0.2
Nodes (9): DBSCANNoiseFilter, KMeansSegmenter, _matrix(), Segmentation models: DBSCAN noise filter + KMeans segmenter., TDD tests for segmentation models (DBSCAN + KMeans)., test_dbscan_noise_rate_below_threshold(), test_kmeans_bootstrap_ari_above_threshold(), test_kmeans_silhouette_above_threshold() (+1 more)

### Community 13 - "Community 13"
Cohesion: 0.19
Nodes (12): clean_population(), _normalize_dob(), Cleaning pipeline for Module A raw population data., Apply deterministic cleaning steps and emit QA report., _write_qa_report(), get_seed(), make_rng(), Seed management and RNG factory.  All random operations in this project must use (+4 more)

### Community 14 - "Community 14"
Cohesion: 0.21
Nodes (4): PropensityModel, Participation propensity model with calibration gates., TDD tests for propensity model (A7/A8/A9/A10 gates)., test_propensity_metrics_and_calibration_gates()

### Community 15 - "Community 15"
Cohesion: 0.19
Nodes (10): compute_auc(), compute_brier(), Calibration and predictive metrics for propensity model., reliability_deviation(), compute_bootstrap_ari(), compute_silhouette(), Clustering evaluation helpers for Module A., Tests for evaluation helpers. (+2 more)

### Community 16 - "Community 16"
Cohesion: 0.17
Nodes (11): code:block1 ([VERIFIED] TSJE Electoral Roll (N = 4,260,816)  ──┐), code:bash (git clone <repo-url>), code:block3 (├── README.md                    ← this file), Decision Analytics Reconstruction, Honest narrative, How to evaluate this project in 10 minutes, Modules, Repository structure (+3 more)

### Community 17 - "Community 17"
Cohesion: 0.17
Nodes (11): A. Plan completeness (`/task-plan`), B. Execution gate (`/task-execute`), B. Verification (`/task-verify`), C. Todo lifecycle protocol (gating), C. Verification (`/task-verify`), D. Terminology (quick), D. Todo lifecycle protocol (gating), E. Module-specific gates (summary pointers) (+3 more)

### Community 18 - "Community 18"
Cohesion: 0.2
Nodes (9): Demographics (Module A), Departmental Participation Rates (Module A, B), FX (Module B), ICT / Media (Module A, B), Language (Module A), Outcome Event (Module C), Population and Participation (Module A, C), Socioeconomic (Module A) (+1 more)

### Community 19 - "Community 19"
Cohesion: 0.22
Nodes (8): AI orchestration harness — operator guide, code:mermaid (flowchart LR), Dynamic workflow, Failure recovery, Graph context layer, Mirrors, Quick start, Related scope

### Community 20 - "Community 20"
Cohesion: 0.25
Nodes (8): 4.1 Collection simulation, 4.2 Channel taxonomy, 4.3 Raw dirty layer, 4.4 Cleaning pipeline, 4.5 Post-clean QA report specification, 4.6 Data lineage diagram, 4. Data Pipeline Specification, code:mermaid (flowchart TD)

### Community 21 - "Community 21"
Cohesion: 0.29
Nodes (6): Cursor project agents (`.cursor/agents/`), Cursor Task tool mapping (optional), Escalation additions (always check orchestrator escalation matrix), Parallelism, Routing matrix, Task type → primary agent → skills

### Community 22 - "Community 22"
Cohesion: 0.29
Nodes (6): code:bash (poetry install), Key outputs, Module A — Population Modeling and Segmentation, Quality gates (implemented), Quick run, What decision this supports

### Community 23 - "Community 23"
Cohesion: 0.29
Nodes (6): 2026-05-07 — Module A: DBSCAN vs Isolation Forest for noise pre-pass, 2026-05-07 — Module A: Department rake approach, 2026-05-07 — Module A: K selection strategy, 2026-05-07 — Module A: Platt calibration vs isotonic regression, 2026-05-07 — Schema contracts: Module A → B → C dependency, Decision Log

### Community 24 - "Community 24"
Cohesion: 0.33
Nodes (5): Agent instructions (PARAGUAY_ELLECTION), Graphify knowledge graph (always-on context), Project skills, Scope source of truth, Start here

### Community 25 - "Community 25"
Cohesion: 0.33
Nodes (5): Data Dictionary, Module A — `media_reachability_by_segment.csv`, Module A — `participation_propensity.parquet`, Module A — `population_master_clean.parquet`, Module A — `segment_labels.parquet`

### Community 26 - "Community 26"
Cohesion: 0.5
Nodes (3): Module A outputs (produced here; consumed downstream), Schema Contracts, Version policy

### Community 27 - "Community 27"
Cohesion: 0.5
Nodes (3): QA verdicts, /task-verify — TASK-20260507-001, TDD red-green evidence (captured in session)

## Knowledge Gaps
- **308 isolated node(s):** `Module A package root.`, `Module A dashboard app package.`, `Module A Streamlit dashboard (three tabs).`, `TDD tests for segmentation models (DBSCAN + KMeans).`, `Tests for population_segmentation.data.generator.  TDD order: these tests are wr` (+303 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `generate_population()` connect `Community 8` to `Community 2`, `Community 5`, `Community 7`, `Community 10`, `Community 13`?**
  _High betweenness centrality (0.078) - this node is a cross-community bridge._
- **Why does `_build_sample()` connect `Community 5` to `Community 8`, `Community 2`, `Community 12`, `Community 14`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Why does `inject_flaws()` connect `Community 2` to `Community 10`, `Community 13`, `Community 5`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `generate_population()` (e.g. with `_build_sample()` and `feature_df()`) actually correct?**
  _`generate_population()` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `inject_flaws()` (e.g. with `_build_sample()` and `feature_df()`) actually correct?**
  _`inject_flaws()` has 8 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Module A package root.`, `Module A dashboard app package.`, `Module A Streamlit dashboard (three tabs).` to the rest of the system?**
  _308 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.04 - nodes in this community are weakly interconnected._