# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false
"""Calibration plotting helpers — thin delegates to the shared builder.

The actual reliability-diagram implementation lives in
``shared/src/visual_system/reliability.py`` (IMP-V04 / issue #68): one
builder, square [0,1]x[0,1] axes at enforced equal aspect, Wilson intervals,
count-scaled markers, and an in-canvas disclaimer. This module only adapts it
to Module A's import surface; it draws nothing itself.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "src"))
from visual_system import reliability as _shared

if TYPE_CHECKING:
    from matplotlib.figure import Figure

#: Re-exported so dashboard text and static exports share one caveat wording.
CIRCULARITY_DISCLAIMER = _shared.CIRCULARITY_DISCLAIMER


def reliability_frame(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> pd.DataFrame:
    """Bin predicted probabilities and summarize predicted vs observed outcomes.

    Args:
        y_true: Binary labels (0/1).
        y_prob: Predicted probabilities used for binning.
        n_bins: Number of fixed equal-width bins on ``[0, 1]``.

    Returns:
        One row per non-empty bin with ``bin``, ``predicted_mean``,
        ``observed_mean``, ``count``, ``ci_low``, ``ci_high`` (95% Wilson).

    Raises:
        ValueError: On NaN or out-of-range predictions, or non-binary labels
            (the shared builder aborts instead of silently dropping rows).

    Example:
        Input to :func:`reliability_chart` for the dashboard's calibration tab.
    """
    return _shared.reliability_frame(y_true, y_prob, n_bins=n_bins)


def reliability_chart(frame: pd.DataFrame, *, subtitle: str | None = None) -> Figure:
    """Reliability diagram for the dashboard, via the shared builder.

    Args:
        frame: Output of :func:`reliability_frame`.
        subtitle: Optional second title line (e.g. label-source note).

    Returns:
        Matplotlib ``Figure`` (render with ``st.pyplot``) — square axes,
        45-degree reference, Wilson intervals, in-canvas disclaimer.

    Raises:
        ValueError: If ``frame`` is empty.

    Example:
        ``st.pyplot(reliability_chart(reliability_frame(y, p)))``.
    """
    return _shared.reliability_diagram(frame, subtitle=subtitle)
