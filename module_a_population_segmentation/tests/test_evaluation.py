"""Tests for evaluation helpers."""

from __future__ import annotations

import numpy as np
from population_segmentation.evaluation.calibration_metrics import (
    compute_auc,
    compute_brier,
    reliability_deviation,
)
from population_segmentation.evaluation.clustering_metrics import (
    compute_bootstrap_ari,
    compute_silhouette,
)


def test_calibration_metric_functions() -> None:
    y_true = np.array([0, 1, 0, 1, 1, 0], dtype=int)
    y_prob = np.array([0.1, 0.8, 0.2, 0.7, 0.9, 0.3], dtype=float)
    assert 0.0 <= compute_auc(y_true, y_prob) <= 1.0
    assert 0.0 <= compute_brier(y_true, y_prob) <= 1.0
    assert reliability_deviation(y_true, y_prob, n_bins=3) >= 0.0


def test_clustering_metric_functions() -> None:
    x = np.array(
        [
            [0.0, 0.0],
            [0.1, 0.1],
            [0.2, 0.2],
            [3.0, 3.0],
            [3.1, 3.1],
            [3.2, 3.2],
        ]
    )
    labels = np.array([0, 0, 0, 1, 1, 1], dtype=int)
    sil = compute_silhouette(x, labels)
    ari = compute_bootstrap_ari(x, labels, k=2, random_state=42, n_bootstrap=3)
    assert sil > 0.0
    assert ari >= 0.0
