---
doc_id: DOC-REP-002
doc_type: narrative
doc_role: canonical
visibility: public
status: active
owner: project
last_reviewed: '2026-05-20'
canonical_source: null
derived_from: null
supersedes: null
tags: []
---

# Module A — extended clustering validation

Beyond silhouette and bootstrap ARI (enforced in CI), the reconstruction reports **Davies–Bouldin** (lower is better) and **Calinski–Harasz** (higher is better) on the same PCA-reduced feature matrix used for k-means (`k = 6`).

| Metric | Role |
|--------|------|
| Silhouette | Cohesion / separation in embedding space |
| Bootstrap ARI | Stability of partitions under row resampling |
| Davies–Bouldin | Balance of intra- vs inter-cluster dispersion |
| Calinski–Harasz | Variance ratio criterion |

Implementation: `population_segmentation.evaluation.clustering_metrics` (`compute_davies_bouldin`, `compute_calinski_harabasz`). Deterministic seeds are fixed in tests (`module_a_population_segmentation/tests/test_cluster_metrics_extended.py`).

**Operational reading:** if Davies–Bouldin drifts upward across feature iterations, revisit feature scaling or noise pre-pass thresholds before changing `k`.
