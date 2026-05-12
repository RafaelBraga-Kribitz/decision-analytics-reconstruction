"""Extended clustering metrics (Davies–Bouldin, Calinski–Harasz)."""

from __future__ import annotations

import numpy as np
import pytest
from population_segmentation.evaluation.clustering_metrics import (
    compute_calinski_harabasz,
    compute_davies_bouldin,
)
from sklearn.cluster import KMeans


@pytest.fixture
def small_clustered() -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(42)
    a = rng.normal(size=(40, 3)) + np.array([0.0, 0.0, 0.0])
    b = rng.normal(size=(40, 3)) + np.array([4.0, 0.0, 0.0])
    x = np.vstack([a, b])
    labels = KMeans(n_clusters=2, n_init="auto", random_state=0).fit_predict(x)
    return x, labels


def test_davies_bouldin_low_for_separated_clusters(
    small_clustered: tuple[np.ndarray, np.ndarray],
) -> None:
    x, labels = small_clustered
    db = compute_davies_bouldin(x, labels)
    assert 0.0 <= db < 2.0


def test_calinski_positive(small_clustered: tuple[np.ndarray, np.ndarray]) -> None:
    x, labels = small_clustered
    ch = compute_calinski_harabasz(x, labels)
    assert ch > 10.0


def test_single_cluster_returns_zero() -> None:
    x = np.zeros((10, 2))
    labels = np.zeros(10, dtype=int)
    assert compute_davies_bouldin(x, labels) == 0.0
    assert compute_calinski_harabasz(x, labels) == 0.0
