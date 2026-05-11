"""Module B allocation_output handshake columns for Module C."""

from __future__ import annotations

import pandas as pd

from module_c_forecasting_scenarios.data.cleaning_pipeline import clean_raw_polls
from module_c_forecasting_scenarios.data.raw_loader import load_raw_polls_csv
from module_c_forecasting_scenarios.scenarios.monte_carlo import run_monte_carlo_scenarios


def test_handshake_columns_on_allocation(minimal_allocation_parquet: Path) -> None:
    df = pd.read_parquet(minimal_allocation_parquet)
    for col in (
        "persuasion_adjusted_contacts",
        "expected_contacts",
        "scenario_id",
        "department",
        "channel",
        "week_index",
    ):
        assert col in df.columns


def test_monte_carlo_reads_allocation_mean(
    fixture_raw_polls_csv: Path, tmp_path: Path, minimal_allocation_parquet: Path
) -> None:
    raw = load_raw_polls_csv(fixture_raw_polls_csv)
    tracking, _ = clean_raw_polls(raw, "A")
    run_monte_carlo_scenarios(tracking, minimal_allocation_parquet, out_dir=tmp_path)
    draws = pd.read_parquet(tmp_path / "monte_carlo_draws.parquet")
    assert draws["alloc_mean_persuasion_contacts"].iloc[0] > 0
