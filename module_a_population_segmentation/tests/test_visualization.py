"""Tests for visualization helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd
from population_segmentation.visualization.calibration_curves import (
    reliability_chart,
    reliability_frame,
)
from population_segmentation.visualization.segment_profiles import (
    segment_profile_table,
    segment_size_chart,
)


def test_segment_profile_helpers() -> None:
    df = pd.DataFrame(
        {
            "segment_label": ["a", "a", "b", "b"],
            "participation_propensity": [0.4, 0.6, 0.7, 0.8],
            "reachability_index": [0.2, 0.3, 0.6, 0.7],
            "rural_flag": [True, False, False, True],
            "jopara_flag": [True, False, True, False],
        }
    )
    prof = segment_profile_table(df)
    fig = segment_size_chart(prof)
    assert not prof.empty
    assert fig is not None


def test_calibration_curve_helpers() -> None:
    y_true = np.array([0, 1, 0, 1, 1, 0], dtype=int)
    y_prob = np.array([0.1, 0.8, 0.2, 0.7, 0.9, 0.3], dtype=float)
    frame = reliability_frame(y_true, y_prob, n_bins=3)
    fig = reliability_chart(frame)
    assert not frame.empty
    assert fig is not None
