"""Calibration plotting helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go


def reliability_frame(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> pd.DataFrame:
    """Bin predicted probabilities and summarize mean predicted vs observed outcomes.

    Args:
        y_true: Binary labels (0/1).
        y_prob: Predicted probabilities used for binning.
        n_bins: Number of equal-width bins on ``[0, 1]``.

    Returns:
        DataFrame with ``bin``, ``predicted_mean``, and ``observed_mean`` columns.

    Raises:
        None

    Example:
        Input to :func:`reliability_chart` for interactive calibration plots.
    """
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    rows: list[dict[str, float]] = []
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        mask = (y_prob >= lo) & (y_prob < hi if i < n_bins - 1 else y_prob <= hi)
        if mask.sum() == 0:
            continue
        rows.append(
            {
                "bin": i,
                "predicted_mean": float(y_prob[mask].mean()),
                "observed_mean": float(y_true[mask].mean()),
            }
        )
    return pd.DataFrame(rows)


def reliability_chart(frame: pd.DataFrame) -> go.Figure:
    """Plotly reliability diagram comparing model curve to the perfect diagonal.

    Args:
        frame: Output of :func:`reliability_frame`.

    Returns:
        ``plotly.graph_objects.Figure`` ready for ``show`` or HTML export.

    Raises:
        KeyError: If expected columns are missing from ``frame``.

    Example:
        Embedded in notebooks comparing raw vs Platt-calibrated propensity scores.
    """
    fig = go.Figure()
    fig.add_scatter(
        x=frame["predicted_mean"],
        y=frame["observed_mean"],
        mode="lines+markers",
        name="Model",
    )
    fig.add_scatter(x=[0, 1], y=[0, 1], mode="lines", name="Perfect")
    fig.update_layout(title="Reliability diagram", xaxis_title="Predicted", yaxis_title="Observed")
    return fig
