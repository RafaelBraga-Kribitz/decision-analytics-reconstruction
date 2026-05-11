"""Battleground export."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from module_c_forecasting_scenarios.data.contract_validate import validate_dataframe_contract
from module_c_forecasting_scenarios.geo.heatmap import export_battleground_department_table


def test_battleground_table_contract(tmp_path: Path) -> None:
    daily = pd.DataFrame(
        {
            "date": [pd.Timestamp("2018-04-20"), pd.Timestamp("2018-04-21")],
            "calibration_series": ["A", "A"],
            "series_tag": ["A", "A"],
            "posterior_mean_preference_margin_pp": [3.5, 3.8],
            "posterior_hdi_low_pp": [2.0, 2.5],
            "posterior_hdi_high_pp": [5.0, 5.2],
            "model_version": ["t", "t"],
        }
    )
    out = tmp_path / "bg.parquet"
    df = export_battleground_department_table(daily, out, calibration_series="A")
    validate_dataframe_contract(df, "battleground_department_probability")
    assert out.with_suffix(".geojson").exists()
