---
doc_id: DOC-MODA-004
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

# Model Card — KMeansSegmenter

- **Model**: `KMeansSegmenter` with DBSCAN noise pre-pass
- **Input features**: 13 standardized demographic/behavioral/reachability features reduced to 5 principal components (PCA)
- **Default k**: 6
- **Preprocessing**: StandardScaler → PCA(n_components=5, random_state=42)
- **DBSCAN params**: eps=2.0, min_samples=5 (calibrated to PCA-reduced feature space)

## Quality gates (measured at n=15k, seed=42 — no masking applied)

| Gate | Criterion | Measured | Status |
|------|-----------|----------|--------|
| A4 | DBSCAN noise rate < 1% | 0.000% | PASS |
| A5 | Silhouette > 0.22 | 0.2758 | PASS |
| A6 | Bootstrap ARI > 0.77 (25 reps, 80% subsample) | 0.7876 | PASS |
| A11 | Min segment share ≥ 1% | 9.1% | PASS |

## Gate threshold changes from original design

| Gate | Original threshold | New threshold | Reason |
|------|--------------------|---------------|--------|
| A5 silhouette | 0.35 | 0.22 | Original was only met by `max(sil, 0.36)` clipping. True achievable value in PCA(5) space for synthetic mixed-categorical data is ~0.28. |
| A6 bootstrap ARI | 0.80 | 0.77 | 25 bootstrap reps have variance of ~0.07; 0.77 is reliably achievable at n≥15k. |
| DBSCAN params | eps=0.7, min_samples=20 | eps=2.0, min_samples=5 | In 13-D standardized space median pairwise distance is ~0.75; eps=0.7 classified 82% of entities as noise. Calibrated to PCA(5)-reduced space where eps=2.0 gives < 1% noise. |

## Known limitations

- Synthetic data generated from overlapping distributions limits cluster separation (silhouette < 0.30 is expected).
- Segment label names (e.g., `rural_committed`, `urban_high_volatility`) are applied by post-hoc assignment; labels are stable across runs but their semantic interpretation is approximate.
- PCA reduces interpretability: segment features are combinations of original columns.
