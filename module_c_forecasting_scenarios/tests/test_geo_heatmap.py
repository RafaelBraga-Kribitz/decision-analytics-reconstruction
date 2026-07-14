"""Battleground export — contract + choropleth GeoJSON tests."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from module_b_resource_allocation.constants import DEPARTMENTS

from module_c_forecasting_scenarios.data.contract_validate import validate_dataframe_contract
from module_c_forecasting_scenarios.geo.heatmap import export_battleground_department_table

_PKG_GEO = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "module_c_forecasting_scenarios"
    / "geo"
    / "paraguay_departments.geojson"
)

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
    df = export_battleground_department_table(
        daily_fixture, out, calibration_series="A", primary=True
    )
    validate_dataframe_contract(df, "battleground_department_probability")
    assert out.with_suffix(".geojson").exists()


def test_battleground_heatmap_geojson_written(daily_fixture: pd.DataFrame, tmp_path: Path) -> None:
    out = tmp_path / "bg.parquet"
    export_battleground_department_table(daily_fixture, out, calibration_series="A", primary=True)
    heatmap_path = tmp_path / "battleground_probability_heatmap.geojson"
    assert heatmap_path.exists(), "choropleth GeoJSON not written"


def test_battleground_heatmap_has_18_features(daily_fixture: pd.DataFrame, tmp_path: Path) -> None:
    out = tmp_path / "bg.parquet"
    export_battleground_department_table(daily_fixture, out, calibration_series="A", primary=True)
    geo = json.loads((tmp_path / "battleground_probability_heatmap.geojson").read_text())
    assert len(geo["features"]) == 18


def test_battleground_heatmap_polygon_geometry(daily_fixture: pd.DataFrame, tmp_path: Path) -> None:
    out = tmp_path / "bg.parquet"
    export_battleground_department_table(daily_fixture, out, calibration_series="A", primary=True)
    geo = json.loads((tmp_path / "battleground_probability_heatmap.geojson").read_text())
    for feat in geo["features"]:
        assert feat["geometry"] is not None, f"{feat['properties']['department']} has null geometry"
        assert feat["geometry"]["type"] in {"Polygon", "MultiPolygon"}


def test_committed_paraguay_departments_geojson_covers_all_departments() -> None:
    """Package geometry must map 1:1 to DEPARTMENTS (geoBoundaries ADM1, Exterior excluded)."""
    geo = json.loads(_PKG_GEO.read_text(encoding="utf-8"))
    assert len(geo["features"]) == len(DEPARTMENTS)
    depts = {f["properties"]["department"] for f in geo["features"]}
    assert depts == set(DEPARTMENTS)
    note = geo.get("_note", "")
    assert "geoBoundaries" in note
    for feat in geo["features"]:
        assert feat["geometry"]["type"] in {"Polygon", "MultiPolygon"}
        assert feat["properties"].get("geoboundaries_shape_name")


def test_committed_paraguay_departments_source_sidecar_exists() -> None:
    source = _PKG_GEO.with_suffix(".SOURCE.md")
    assert source.is_file()
    text = source.read_text(encoding="utf-8")
    assert "geoBoundaries" in text
    assert "geoBoundaries-PRY-ADM1_simplified.geojson" in text


def test_battleground_heatmap_posterior_win_prob_range(
    daily_fixture: pd.DataFrame, tmp_path: Path
) -> None:
    out = tmp_path / "bg.parquet"
    export_battleground_department_table(daily_fixture, out, calibration_series="A", primary=True)
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
    export_battleground_department_table(daily_fixture, out_a, calibration_series="A", primary=True)
    export_battleground_department_table(daily_fixture, out_b, calibration_series="A", primary=True)
    geo_a = json.loads((tmp_path / "a" / "battleground_probability_heatmap.geojson").read_text())
    geo_b = json.loads((tmp_path / "b" / "battleground_probability_heatmap.geojson").read_text())
    probs_a = [f["properties"]["posterior_win_prob"] for f in geo_a["features"]]
    probs_b = [f["properties"]["posterior_win_prob"] for f in geo_b["features"]]
    assert probs_a == probs_b


def test_battleground_recovers_real_ganar_strongholds(tmp_path: Path) -> None:
    """F-070 calibration gate: at the verified 2018 national candidate margin, the
    four GANAR-winning departments that have polygon geometry (Concepción,
    Cordillera, Alto Paraná, Central) must yield P(Abdo wins) < 0.5 — the model is
    derived from real TSJE returns, not a fabricated formula. The fifth GANAR
    stronghold, Exterior, has no ADM1 polygon and is omitted from the choropleth."""
    # Verified national candidate margin (Abdo 1,206,067 vs Alegre 1,110,464).
    nat_margin_pp = (1_206_067 - 1_110_464) / (1_206_067 + 1_110_464) * 100.0
    daily = pd.DataFrame(
        {
            "date": [pd.Timestamp("2018-04-22")],
            "calibration_series": ["A"],
            "series_tag": ["A"],
            "posterior_mean_preference_margin_pp": [nat_margin_pp],
            "posterior_hdi_low_pp": [nat_margin_pp - 1.0],
            "posterior_hdi_high_pp": [nat_margin_pp + 1.0],
            "model_version": ["t"],
        }
    )
    out = tmp_path / "bg.parquet"
    df = export_battleground_department_table(daily, out, calibration_series="A", anchored=True)
    win = dict(zip(df["department"], df["win_probability_a"], strict=True))
    ganar_with_polygons = ["Concepcion", "Cordillera", "Alto Parana", "Central"]
    for dept in ganar_with_polygons:
        assert win[dept] < 0.5, (
            f"{dept} was a GANAR stronghold in 2018 but the model gives "
            f"P(Abdo)={win[dept]:.3f} ≥ 0.5 — calibration to real returns broken"
        )
    # And a known Abdo landslide (Asunción) must be near-certain for Candidate A.
    assert win["Asuncion"] > 0.9, f"Asuncion P(Abdo)={win['Asuncion']:.3f} too low"


def test_battleground_interval_brackets_point_estimate(
    daily_fixture: pd.DataFrame, tmp_path: Path
) -> None:
    """IMP-C05: every exported row carries 0 <= hdi_low <= p <= hdi_high <= 1."""
    df = export_battleground_department_table(
        daily_fixture, tmp_path / "bg.parquet", calibration_series="A", primary=True
    )
    assert {"estimand", "hdi_low", "hdi_high"} <= set(df.columns)
    assert (df["hdi_low"] >= 0).all() and (df["hdi_high"] <= 1).all()
    assert (df["hdi_low"] <= df["win_probability_a"]).all()
    assert (df["win_probability_a"] <= df["hdi_high"]).all()
    assert (df["estimand"] == "poll_implied").all()


def test_battleground_percentile_hdi_has_visible_width(
    daily_fixture: pd.DataFrame, tmp_path: Path
) -> None:
    """F-079: percentile HDI must spread on at least several departments."""
    df = export_battleground_department_table(
        daily_fixture, tmp_path / "bg.parquet", calibration_series="A", primary=True
    )
    widths = df["hdi_high"] - df["hdi_low"]
    assert (
        widths >= 0.05
    ).sum() >= 5, f"expected ≥5 departments with HDI width ≥0.05, got {(widths >= 0.05).sum()}"


def test_battleground_manifest_records_sigma_provenance(
    daily_fixture: pd.DataFrame, tmp_path: Path
) -> None:
    export_battleground_department_table(
        daily_fixture, tmp_path / "bg.parquet", calibration_series="A", primary=True
    )
    manifest = json.loads((tmp_path / "bg_manifest.json").read_text())
    assert manifest["model_version"] == "c_battleground_v0.5"
    assert manifest["mapping"] == "v0.5_decoupled_sigma"
    assert "sigma_idio_provenance" in manifest
    assert manifest["estimand"] == "poll_implied"
    assert len(manifest["tsje_input_sha256"]) == 64
    assert len(manifest["outcome_data_entry_points"]) == 2


def test_v05_decoupled_sigma_differentiates_large_swings() -> None:
    """F-081: equal sigma_idio + different swings must yield different win probs."""
    from module_c_forecasting_scenarios.geo.heatmap import _win_prob_hdi

    m, sig_n, sig_i = 5.0, 2.0, 5.7
    p12, _, _ = _win_prob_hdi(1.2, m, m - 1, m + 1, sig_n, sig_i)
    p15, _, _ = _win_prob_hdi(1.5, m, m - 1, m + 1, sig_n, sig_i)
    assert p12 != pytest.approx(p15, abs=0.01)


def test_v05_model_version_on_export(daily_fixture: pd.DataFrame, tmp_path: Path) -> None:
    df = export_battleground_department_table(
        daily_fixture, tmp_path / "bg.parquet", calibration_series="A", primary=True
    )
    assert (df["model_version"] == "c_battleground_v0.5").all()


def test_retrodiction_companion_labeled_and_no_choropleth_clobber(
    daily_fixture: pd.DataFrame, tmp_path: Path
) -> None:
    df = export_battleground_department_table(
        daily_fixture,
        tmp_path / "bg_retrodiction.parquet",
        calibration_series="A",
        anchored=True,
        primary=False,
    )
    assert (df["estimand"] == "retrodiction").all()
    assert not (tmp_path / "battleground_probability_heatmap.geojson").exists()


def test_anchor_comparison_flip_list_and_divergence_guard(
    daily_fixture: pd.DataFrame, tmp_path: Path
) -> None:
    from module_c_forecasting_scenarios.geo.heatmap import write_anchor_comparison

    poll_implied = export_battleground_department_table(
        daily_fixture, tmp_path / "p.parquet", calibration_series="A", primary=True
    )
    negative = daily_fixture.copy()
    negative["posterior_mean_preference_margin_pp"] = [-4.0, -4.5]
    negative["posterior_hdi_low_pp"] = [-6.0, -6.5]
    negative["posterior_hdi_high_pp"] = [-2.0, -2.5]
    retrodiction = export_battleground_department_table(
        negative, tmp_path / "r.parquet", calibration_series="A", anchored=True
    )
    cmp_df = write_anchor_comparison(poll_implied, retrodiction, tmp_path / "cmp.md")
    assert cmp_df[
        "classification_flip"
    ].any(), "national margin sign change must flip at least one department classification"
    text = (tmp_path / "cmp.md").read_text()
    assert "flip" in text and "retrodiction" in text

    with pytest.raises(ValueError, match="identical"):
        write_anchor_comparison(poll_implied, poll_implied.copy(), tmp_path / "cmp2.md")
