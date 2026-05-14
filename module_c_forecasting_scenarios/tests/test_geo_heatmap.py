"""Battleground export — contract + choropleth GeoJSON tests."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from module_c_forecasting_scenarios.data.contract_validate import validate_dataframe_contract
from module_c_forecasting_scenarios.geo.heatmap import export_battleground_department_table


@pytest.fixture()
def daily_fixture() -> pd.DataFrame:
    return pd.DataFrame(
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


def test_battleground_table_contract(daily_fixture: pd.DataFrame, tmp_path: Path) -> None:
    out = tmp_path / "bg.parquet"
    df = export_battleground_department_table(daily_fixture, out, calibration_series="A")
    validate_dataframe_contract(df, "battleground_department_probability")
    assert out.with_suffix(".geojson").exists()


def test_battleground_heatmap_geojson_written(daily_fixture: pd.DataFrame, tmp_path: Path) -> None:
    out = tmp_path / "bg.parquet"
    export_battleground_department_table(daily_fixture, out, calibration_series="A")
    heatmap_path = tmp_path / "battleground_probability_heatmap.geojson"
    assert heatmap_path.exists(), "choropleth GeoJSON not written"


def test_battleground_heatmap_has_18_features(daily_fixture: pd.DataFrame, tmp_path: Path) -> None:
    out = tmp_path / "bg.parquet"
    export_battleground_department_table(daily_fixture, out, calibration_series="A")
    geo = json.loads((tmp_path / "battleground_probability_heatmap.geojson").read_text())
    assert len(geo["features"]) == 18


def test_battleground_heatmap_polygon_geometry(daily_fixture: pd.DataFrame, tmp_path: Path) -> None:
    out = tmp_path / "bg.parquet"
    export_battleground_department_table(daily_fixture, out, calibration_series="A")
    geo = json.loads((tmp_path / "battleground_probability_heatmap.geojson").read_text())
    for feat in geo["features"]:
        assert feat["geometry"] is not None, f"{feat['properties']['department']} has null geometry"
        assert feat["geometry"]["type"] == "Polygon"


def test_battleground_heatmap_posterior_win_prob_range(
    daily_fixture: pd.DataFrame, tmp_path: Path
) -> None:
    out = tmp_path / "bg.parquet"
    export_battleground_department_table(daily_fixture, out, calibration_series="A")
    geo = json.loads((tmp_path / "battleground_probability_heatmap.geojson").read_text())
    for feat in geo["features"]:
        props = feat["properties"]
        assert "posterior_win_prob" in props
        assert "hdi_low" in props
        assert "hdi_high" in props
        assert 0.0 <= props["posterior_win_prob"] <= 1.0
        assert 0.0 <= props["hdi_low"] <= props["hdi_high"] <= 1.0


def test_battleground_heatmap_deterministic(daily_fixture: pd.DataFrame, tmp_path: Path) -> None:
    out_a = tmp_path / "a" / "bg.parquet"
    out_b = tmp_path / "b" / "bg.parquet"
    export_battleground_department_table(daily_fixture, out_a, calibration_series="A")
    export_battleground_department_table(daily_fixture, out_b, calibration_series="A")
    geo_a = json.loads((tmp_path / "a" / "battleground_probability_heatmap.geojson").read_text())
    geo_b = json.loads((tmp_path / "b" / "battleground_probability_heatmap.geojson").read_text())
    probs_a = [f["properties"]["posterior_win_prob"] for f in geo_a["features"]]
    probs_b = [f["properties"]["posterior_win_prob"] for f in geo_b["features"]]
    assert probs_a == probs_b
