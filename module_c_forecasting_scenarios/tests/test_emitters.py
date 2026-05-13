"""Seed matrix and transparency audit."""

from __future__ import annotations

from pathlib import Path

from module_c_forecasting_scenarios.data.cleaning_pipeline import clean_raw_polls
from module_c_forecasting_scenarios.data.emitters import (
    build_house_effect_seed_matrix,
    build_polling_transparency_audit,
)
from module_c_forecasting_scenarios.data.raw_loader import load_raw_polls_csv


def test_seed_matrix_columns(fixture_raw_polls_csv: Path) -> None:
    raw = load_raw_polls_csv(fixture_raw_polls_csv)
    tracking, _ = clean_raw_polls(raw, "A")
    m = build_house_effect_seed_matrix(tracking, 3.70, "A")
    for c in (
        "poll_wave_id",
        "pollster_id",
        "m_poll_pp",
        "phi_transparency",
        "pollster_bias_family",
        "m_star_pp",
        "calibration_series",
    ):
        assert c in m.columns


def test_transparency_audit_groups(fixture_raw_polls_csv: Path) -> None:
    raw = load_raw_polls_csv(fixture_raw_polls_csv)
    tracking, _ = clean_raw_polls(raw, "A")
    a = build_polling_transparency_audit(tracking)
    assert "mean_phi_transparency" in a.columns
