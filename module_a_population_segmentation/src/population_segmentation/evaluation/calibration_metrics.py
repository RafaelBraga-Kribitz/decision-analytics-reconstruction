# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false
"""Calibration and predictive metrics for propensity model."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import brier_score_loss, roc_auc_score


def compute_auc(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    """Area under the ROC curve for binary outcomes.

    Args:
        y_true: Binary labels (0/1).
        y_prob: Predicted probabilities in ``[0, 1]``.

    Returns:
        ROC-AUC as a Python ``float``.

    Raises:
        ValueError: Delegated from scikit-learn when inputs are degenerate or invalid.

    Example:
        Used in propensity reporting alongside Brier score and reliability deviation.
    """
    return float(roc_auc_score(y_true, y_prob))


def compute_brier(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    """Brier score (mean squared error) for probabilistic binary predictions.

    Args:
        y_true: Binary labels (0/1).
        y_prob: Predicted probabilities.

    Returns:
        Brier score (lower is better).

    Raises:
        ValueError: Delegated from scikit-learn for invalid inputs.

    Example:
        Compared before and after Platt calibration in propensity evaluation.
    """
    return float(brier_score_loss(y_true, y_prob))


def reliability_deviation(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    """Maximum absolute deviation between mean predicted and observed rate across bins.

    Args:
        y_true: Binary labels (0/1).
        y_prob: Predicted probabilities used to assign decile-style bins.
        n_bins: Number of equal-width probability bins on ``[0, 1]``.

    Returns:
        Worst-case absolute gap in **percentage points** (scaled ``× 100``).

    Raises:
        None

    Example:
        Gates propensity calibration quality against ``model_params`` thresholds.
    """
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
