"""Exit bias stage."""

from __future__ import annotations

from pathlib import Path

import pytest

from module_c_forecasting_scenarios.data.cleaning_pipeline import clean_raw_polls
from module_c_forecasting_scenarios.data.raw_loader import load_raw_polls_csv
from module_c_forecasting_scenarios.models.exit.exit_model import fit_exit_quickcount

pytestmark = pytest.mark.slow


@pytest.fixture(autouse=True)
def _mc_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MC_FAST", "1")


def test_exit_quickcount_runs(fixture_raw_polls_csv: Path) -> None:
    raw = load_raw_polls_csv(fixture_raw_polls_csv)
    _, exit_df = clean_raw_polls(raw, "A")
    summary, idata = fit_exit_quickcount(exit_df, calibration_series="A")
    assert len(summary) >= 1
    if idata is not None:
        assert "intercept" in idata.posterior
