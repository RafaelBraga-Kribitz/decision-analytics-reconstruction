"""Small-sample honesty: exit low_n flags and coverage binomial CIs (F-085)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from module_c_forecasting_scenarios.data.cleaning_pipeline import clean_raw_polls
from module_c_forecasting_scenarios.data.raw_loader import load_raw_polls_csv
from module_c_forecasting_scenarios.models.exit.exit_model import fit_exit_quickcount
from module_c_forecasting_scenarios.validation.small_n import (
    EXIT_MIN_RELIABLE_WAVES,
    exact_binomial_ci,
    is_low_n,
)
from module_c_forecasting_scenarios.validation.walk_forward import summarize_walk_forward


def test_threshold_matches_methodology() -> None:
    methodology = (Path(__file__).resolve().parents[1] / "METHODOLOGY.md").read_text(
        encoding="utf-8"
    )
    assert f"EXIT_MIN_RELIABLE_WAVES = {EXIT_MIN_RELIABLE_WAVES}" in methodology


@pytest.mark.parametrize(("n", "low"), [(0, True), (4, True), (5, False), (9, False)])
def test_is_low_n_boundary(n: int, low: bool) -> None:
    assert is_low_n(n) is low


def test_exact_binomial_ci_known_values() -> None:
    low, high = exact_binomial_ci(3, 6)
    assert low == pytest.approx(0.118, abs=1e-3)
    assert high == pytest.approx(0.882, abs=1e-3)
    assert exact_binomial_ci(6, 6)[1] == pytest.approx(1.0)


def test_exit_stub_rows_are_flagged() -> None:
    one_row = pd.DataFrame({"m_poll_pp": [10.0]})
    summary, idata = fit_exit_quickcount(one_row, calibration_series="A")
    assert idata is None
    assert summary["low_n"].all()
    assert summary["n_waves"].eq(1).all()


@pytest.mark.slow
def test_exit_fixture_fit_is_flagged_low_n(
    fixture_raw_polls_csv: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MC_FAST", "1")
    _, exit_df = clean_raw_polls(load_raw_polls_csv(fixture_raw_polls_csv), "A")
    assert len(exit_df) < EXIT_MIN_RELIABLE_WAVES  # committed fixture: 4 exit waves
    summary, _ = fit_exit_quickcount(exit_df, calibration_series="A")
    assert summary["low_n"].all()
    assert summary["n_waves"].eq(len(exit_df)).all()


def test_walk_forward_summary_reports_k_and_ci() -> None:
    per_holdout = pd.DataFrame(
        {
            "prob_margin_positive": [0.9, 0.8, 0.7, 0.6, 0.4, 0.3],
            "observed_positive": [1, 1, 1, 0, 0, 1],
            "in_hdi80": [True, False, True, False, False, False],
            "in_hdi95": [True, True, True, False, False, False],
        }
    )
    m = summarize_walk_forward(per_holdout)
    assert m["n_holdouts"] == 6
    assert m["coverage_95pct_k"] == 3
    assert m["coverage_95pct"] == pytest.approx(0.5)
    assert m["coverage_95pct_ci_low"] == pytest.approx(0.118, abs=1e-3)
    assert m["coverage_95pct_ci_high"] == pytest.approx(0.882, abs=1e-3)
    assert m["coverage_80pct_k"] == 2
