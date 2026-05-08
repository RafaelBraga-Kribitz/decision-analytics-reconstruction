# Model Card — KMeansSegmenter

- **Model**: `KMeansSegmenter` with DBSCAN pre-pass
- **Input features**: 13 standardized demographic/behavioral/reachability features
- **Default k**: 6
- **Primary gates**:
  - Silhouette > 0.35 (A5)
  - Bootstrap ARI > 0.80 (A6)
  - DBSCAN noise rate < 1% (A4)
  - Min segment size >= 1% (A11)
- **Known limitations**:
  - Synthetic data calibration can inflate stability metrics versus real-world noise.
  - Segment labels are canonicalized post-clustering for operational readability.
