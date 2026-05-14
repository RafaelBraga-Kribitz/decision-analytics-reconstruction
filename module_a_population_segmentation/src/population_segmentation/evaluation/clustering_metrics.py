# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false
"""Clustering evaluation helpers for Module A."""

from __future__ import annotations

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import (
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)


def compute_silhouette(x: np.ndarray, labels: np.ndarray) -> float:
    """Silhouette score for clustering quality in embedding space.

    Args:
        x: Feature matrix (``n_samples × n_features``).
        labels: Integer cluster assignment per row.

    Returns:
        ``0.0`` if fewer than two clusters; otherwise sklearn silhouette score.

    Raises:
        None

    Example:
        Used in segmentation gates with ``model_params`` silhouette thresholds.
    """
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
    """Mean adjusted Rand index between reference labels and KMeans on bootstrap subsamples.

    Args:
        x: Feature matrix.
        labels: Reference cluster labels (e.g., primary KMeans fit).
        k: Number of clusters passed to the bootstrap KMeans.
        random_state: RNG seed for reproducibility.
        n_bootstrap: Number of subsample draws.

    Returns:
        Mean ARI across successful bootstrap fits.

    Raises:
        None

    Example:
        Stability gate for segmentation before exporting ``segment_labels``.
    """
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


def compute_davies_bouldin(x: np.ndarray, labels: np.ndarray) -> float:
    """Davies–Bouldin index (lower is better) for the given partition.

    Args:
        x: Feature matrix.
        labels: Cluster assignment per row.

    Returns:
        ``0.0`` if fewer than two clusters; otherwise sklearn DB score.

    Raises:
        None

    Example:
        Logged with silhouette and Calinski–Harabasz for segmentation diagnostics.
    """
    if len(np.unique(labels)) < 2:
        return 0.0
    return float(davies_bouldin_score(x, labels))


def compute_calinski_harabasz(x: np.ndarray, labels: np.ndarray) -> float:
    """Calinski–Harabasz score (higher is better) for the given partition.

    Args:
        x: Feature matrix.
        labels: Cluster assignment per row.

    Returns:
        ``0.0`` if fewer than two clusters; otherwise sklearn CH score.

    Raises:
        None

    Example:
        Logged alongside silhouette for multi-metric segmentation QA.
    """
    if len(np.unique(labels)) < 2:
        return 0.0
    return float(calinski_harabasz_score(x, labels))
