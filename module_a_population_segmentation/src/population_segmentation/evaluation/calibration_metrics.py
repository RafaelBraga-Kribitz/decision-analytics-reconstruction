"""Calibration and predictive metrics for propensity model."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import brier_score_loss, roc_auc_score


def compute_auc(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    return float(roc_auc_score(y_true, y_prob))


def compute_brier(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    return float(brier_score_loss(y_true, y_prob))


def reliability_deviation(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    max_dev = 0.0
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        mask = (y_prob >= lo) & (y_prob < hi if i < n_bins - 1 else y_prob <= hi)
        if mask.sum() == 0:
            continue
        pred = float(y_prob[mask].mean())
        obs = float(y_true[mask].mean())
        max_dev = max(max_dev, abs(pred - obs))
    return float(max_dev * 100.0)  # percentage points
