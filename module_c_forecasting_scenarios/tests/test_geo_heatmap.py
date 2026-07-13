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


def _feature_bbox(feat: dict) -> tuple[float, float, float, float]:
    ring = feat["geometry"]["coordinates"][0]
    lons = [pt[0] for pt in ring]
    lats = [pt[1] for pt in ring]
    return min(lons), min(lats), max(lons), max(lats)


def _bbox_overlap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    """True when closed-axis bounding boxes share interior area (edge-sharing is OK)."""
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1


def test_battleground_department_polygons_do_not_overlap(
    daily_fixture: pd.DataFrame, tmp_path: Path
) -> None:
    """Choropleth cells must not overlap — overlapping placeholder boxes hid low-P depts."""
    out = tmp_path / "bg.parquet"
    export_battleground_department_table(daily_fixture, out, calibration_series="A")
    geo = json.loads((tmp_path / "battleground_probability_heatmap.geojson").read_text())
    features = geo["features"]
    bboxes = [_feature_bbox(f) for f in features]
    for i, a in enumerate(bboxes):
        for j, b in enumerate(bboxes):
            if i >= j:
                continue
            assert not _bbox_overlap(a, b), (
                f"{features[i]['properties']['department']} overlaps "
                f"{features[j]['properties']['department']}"
            )


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
    df = export_battleground_department_table(daily, out, calibration_series="A")
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
        daily_fixture, tmp_path / "bg.parquet", calibration_series="A"
    )
    assert {"estimand", "hdi_low", "hdi_high"} <= set(df.columns)
    assert (df["hdi_low"] >= 0).all() and (df["hdi_high"] <= 1).all()
    assert (df["hdi_low"] <= df["win_probability_a"]).all()
    assert (df["win_probability_a"] <= df["hdi_high"]).all()
    assert (df["estimand"] == "retrodiction").all()


def test_battleground_manifest_records_sigma_provenance(
    daily_fixture: pd.DataFrame, tmp_path: Path
) -> None:
    export_battleground_department_table(
        daily_fixture, tmp_path / "bg.parquet", calibration_series="A"
    )
    manifest = json.loads((tmp_path / "bg_manifest.json").read_text())
    assert manifest["sigma_idio_provenance"] == "illustrative_assumption_not_estimated"
    assert manifest["estimand"] == "retrodiction"
    assert len(manifest["tsje_input_sha256"]) == 64
    assert len(manifest["outcome_data_entry_points"]) == 2


def test_unanchored_companion_labeled_and_no_choropleth_clobber(
    daily_fixture: pd.DataFrame, tmp_path: Path
) -> None:
    df = export_battleground_department_table(
        daily_fixture, tmp_path / "bg_unanchored.parquet", calibration_series="A", anchored=False
    )
    assert (df["estimand"] == "unanchored_retrodiction").all()
    # the stable-name choropleth belongs to the anchored run only
    assert not (tmp_path / "battleground_probability_heatmap.geojson").exists()


def test_anchor_comparison_flip_list_and_divergence_guard(
    daily_fixture: pd.DataFrame, tmp_path: Path
) -> None:
    from module_c_forecasting_scenarios.geo.heatmap import write_anchor_comparison

    anchored = export_battleground_department_table(
        daily_fixture, tmp_path / "a.parquet", calibration_series="A"
    )
    shifted = daily_fixture.copy()
    shifted["posterior_mean_preference_margin_pp"] = [-1.0, -1.2]
    shifted["posterior_hdi_low_pp"] = [-2.5, -2.7]
    shifted["posterior_hdi_high_pp"] = [0.5, 0.3]
    unanchored = export_battleground_department_table(
        shifted, tmp_path / "u.parquet", calibration_series="A", anchored=False
    )
    cmp_df = write_anchor_comparison(anchored, unanchored, tmp_path / "cmp.md")
    # a sign flip of the national margin must flip departments that move with it
    assert cmp_df["classification_flip"].any()
    text = (tmp_path / "cmp.md").read_text()
    assert "flip" in text and "retrodiction" in text

    # silent re-anchoring guard: identical tables must raise
    with pytest.raises(ValueError, match="identical"):
        write_anchor_comparison(anchored, anchored.copy(), tmp_path / "cmp2.md")
