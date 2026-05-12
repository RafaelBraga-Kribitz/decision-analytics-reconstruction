"""Fast tests for tracking hierarchical helpers (no PyMC sampling)."""

from __future__ import annotations

from datetime import date

import pandas as pd
from module_c_forecasting_scenarios.models.tracking.hierarchical import _build_day_index


def test_build_day_index_accepts_fixture_like_tracking() -> None:
    """Regression: pd.date_range yields DatetimeIndex — must not use .iloc."""
    rows = [
        {
            "field_window_start": date(2018, 2, 1),
            "field_window_end": date(2018, 2, 3),
        },
        {
            "field_window_start": date(2018, 3, 1),
            "field_window_end": date(2018, 3, 2),
        },
    ]
    tr = pd.DataFrame(rows)
    outcome = date(2018, 4, 22)
    days, poll_idx = _build_day_index(tr, outcome)
    assert len(days) >= 1
    assert len(poll_idx) == len(tr)
    assert poll_idx.min() >= 0
    assert poll_idx.max() < len(days)
