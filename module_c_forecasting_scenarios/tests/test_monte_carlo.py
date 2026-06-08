"""Monte Carlo catalog + draws."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from module_c_forecasting_scenarios.data.cleaning_pipeline import clean_raw_polls
from module_c_forecasting_scenarios.data.raw_loader import load_raw_polls_csv
from module_c_forecasting_scenarios.scenarios.monte_carlo import run_monte_carlo_scenarios


@pytest.fixture(autouse=True)
def _mc_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MC_FAST", "1")


def test_monte_carlo_shock_catalog_unique_ids(
    fixture_raw_polls_csv: Path, tmp_path: Path, minimal_allocation_parquet: Path
) -> None:
    raw = load_raw_polls_csv(fixture_raw_polls_csv)
    tracking, _ = clean_raw_polls(raw, "A")
    run_monte_carlo_scenarios(tracking, minimal_allocation_parquet, out_dir=tmp_path)
    cat = yaml.safe_load((tmp_path / "monte_carlo_shock_catalog.yaml").read_text())
    shocks = cat["shocks"]
    ids = [s["shock_id"] for s in shocks]
    assert len(ids) == len(set(ids))
    for s in shocks:
        assert s["scenario_bucket"] in {"baseline", "extreme_tracker", "compounded_herd"}


def test_monte_carlo_baseline_zero(tmp_path: Path, fixture_raw_polls_csv: Path) -> None:
    raw = load_raw_polls_csv(fixture_raw_polls_csv)
    tracking, _ = clean_raw_polls(raw, "A")
    run_monte_carlo_scenarios(
        tracking,
        None,
        out_dir=tmp_path,
        baseline_shock_zero=True,
    )
    cat = yaml.safe_load((tmp_path / "monte_carlo_shock_catalog.yaml").read_text())
    for s in cat["shocks"]:
        assert s["shock_score_s"] == 0.0
