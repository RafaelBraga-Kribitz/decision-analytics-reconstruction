"""Cleaning pipeline and transparency."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from module_c_forecasting_scenarios.data.cleaning_pipeline import clean_raw_polls
from module_c_forecasting_scenarios.data.exceptions import QAGateFailure
from module_c_forecasting_scenarios.data.raw_loader import load_raw_polls_csv
from module_c_forecasting_scenarios.data.transparency import compute_phi_transparency


def test_transparency_two_missing_pillars_lowers_phi() -> None:
    hi = compute_phi_transparency(True, True, True, True)
    lo = compute_phi_transparency(False, False, False, False)
    assert lo < hi


def test_clean_raw_polls_splits_tracking_exit(fixture_raw_polls_csv: Path) -> None:
    raw = load_raw_polls_csv(fixture_raw_polls_csv)
    tracking, exit_df = clean_raw_polls(raw, "A")
    assert "exit" not in tracking.columns
    assert len(tracking) >= 1
    assert len(exit_df) >= 1
    assert (tracking["calibration_series"] == "A").all()
    assert exit_df["calibration_series"].iloc[0] == "A"


def test_clean_raw_polls_rejects_bad_wave() -> None:
    raw = pd.DataFrame(
        {
            "poll_raw_id": ["x"],
            "publication_date": [pd.Timestamp("2018-03-01")],
            "pollster_display_name": ["Test"],
            "has_ficha": [True],
            "wave_type": ["invalid"],
            "preference_proxy_a_pct": [40.0],
            "preference_proxy_b_pct": [40.0],
            "sample_size_known": [True],
            "field_window_known": [True],
            "mode_known": [True],
        }
    )
    with pytest.raises(QAGateFailure):
        clean_raw_polls(raw, "A")
