"""Clustering evaluation helpers for Module A."""

from __future__ import annotations

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score


def compute_silhouette(x: np.ndarray, labels: np.ndarray) -> float:
    if len(np.unique(labels)) < 2:
        return 0.0
    return float(silhouette_score(x, labels))


def compute_bootstrap_ari(
    x: np.ndarray,
    labels: np.ndarray,
    k: int,
    random_state: int = 42,
    n_bootstrap: int = 25,
) -> float:
    rng = np.random.default_rng(random_state)
    n = len(x)
    scores: list[float] = []
    for _ in range(n_bootstrap):
        sample_size = min(n, max(2, int(0.8 * n)))
        idx = rng.choice(n, size=sample_size, replace=False)
        km = KMeans(n_clusters=k, n_init="auto", random_state=random_state)
        sub = km.fit_predict(x[idx])
        scores.append(float(adjusted_rand_score(labels[idx], sub)))
    return float(np.mean(scores))
