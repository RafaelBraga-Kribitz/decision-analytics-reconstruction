"""TDD tests for the Jan–Apr 2018 tiered FX layer."""

from __future__ import annotations

import pandas as pd
import pytest
from module_b_resource_allocation.constants import (
    BCP_CORRIDOR_MAX_PCT,
    FX_BAND_MAX_PCT_VS_BCP,
    WEEK_COUNT,
    WEEK_LABELS,
)
from module_b_resource_allocation.data.fx import (
    FxLayer,
    convert_budget_lines_to_usd,
    enforce_bcp_corridor,
    enforce_fx_band,
    fx_layer_to_frame,
    load_fx_layer,
)


def test_load_default_series_b_weekly_covers_all_weeks() -> None:
    layer = load_fx_layer("series_b_weekly")
    assert layer.series_id == "series_b_weekly"
    assert set(layer.ref_by_week) == set(WEEK_LABELS)
    assert set(layer.retail_by_week) == set(WEEK_LABELS)
    assert set(layer.spread_by_week) == set(WEEK_LABELS)


def test_load_series_a_monthly_projected_to_14_weeks() -> None:
    layer = load_fx_layer("series_a_monthly")
    assert layer.series_id == "series_a_monthly"
    assert set(layer.spread_by_week) == set(WEEK_LABELS)
    # All weeks in January (W01–W04) must share the January monthly spread.
    jan_weeks = ["2018-W01", "2018-W02", "2018-W03", "2018-W04"]
    jan_spreads = [layer.spread_by_week[w] for w in jan_weeks]
    assert len(set(jan_spreads)) == 1


def test_retail_is_ref_times_one_plus_spread() -> None:
    layer = load_fx_layer("series_b_weekly")
    for w in WEEK_LABELS:
        expected = layer.ref_by_week[w] * (1.0 + layer.spread_by_week[w])
        assert abs(layer.retail_by_week[w] - expected) < 1e-6


def test_bcp_corridor_allows_default_prior_series() -> None:
    layer = load_fx_layer("series_b_weekly")
    enforce_bcp_corridor(layer, max_pct=BCP_CORRIDOR_MAX_PCT)


def test_bcp_corridor_rejects_outlier_jump() -> None:
    layer = load_fx_layer("series_b_weekly")
    bad_ref = dict(layer.ref_by_week)
    bad_ref[WEEK_LABELS[5]] *= 1.20  # 20% jump → must trip the corridor
    bad = FxLayer(
        series_id=layer.series_id,
        ref_by_week=bad_ref,
        retail_by_week=layer.retail_by_week,
        spread_by_week=layer.spread_by_week,
    )
    with pytest.raises(ValueError, match="corridor"):
        enforce_bcp_corridor(bad, max_pct=BCP_CORRIDOR_MAX_PCT)


def test_fx_band_allows_non_negative_spreads() -> None:
    layer = load_fx_layer("series_b_weekly")
    enforce_fx_band(layer, max_pct=FX_BAND_MAX_PCT_VS_BCP)


def test_fx_band_rejects_retail_below_reference() -> None:
    layer = load_fx_layer("series_b_weekly")
    bad_retail = dict(layer.retail_by_week)
    bad_retail[WEEK_LABELS[2]] = layer.ref_by_week[WEEK_LABELS[2]] * 0.95
    bad = FxLayer(
        series_id=layer.series_id,
        ref_by_week=layer.ref_by_week,
        retail_by_week=bad_retail,
        spread_by_week=layer.spread_by_week,
    )
    with pytest.raises(ValueError, match="undercuts"):
        enforce_fx_band(bad, max_pct=FX_BAND_MAX_PCT_VS_BCP)


def test_fx_layer_frame_shape() -> None:
    layer = load_fx_layer("series_b_weekly")
    df = fx_layer_to_frame(layer)
    assert len(df) == WEEK_COUNT
    assert set(df.columns) == {
        "iso_week",
        "series_id",
        "tc_ref_pyg_per_usd",
        "retail_spread_pct",
        "tc_retail_pyg_per_usd",
    }


def test_convert_budget_lines_pyg_to_usd_uses_correct_tier() -> None:
    layer = load_fx_layer("series_b_weekly")
    budget = pd.DataFrame(
        {
            "row_id": ["B-1", "B-2"],
            "currency": ["PYG", "PYG"],
            "amount_native": [5_700_000.0, 5_700_000.0],
            "iso_week": ["2018-W07", "2018-W07"],
            "fx_tier": ["REF", "RETAIL"],
        }
    )
    out = convert_budget_lines_to_usd(budget, layer)
    ref_rate = layer.ref_by_week["2018-W07"]
    retail_rate = layer.retail_by_week["2018-W07"]
    assert abs(out.loc[0, "amount_usd"] - 5_700_000.0 / ref_rate) < 1e-6
    assert abs(out.loc[1, "amount_usd"] - 5_700_000.0 / retail_rate) < 1e-6
    # Retail tier yields fewer USD per PYG amount than REF tier.
    assert out.loc[1, "amount_usd"] < out.loc[0, "amount_usd"]


def test_convert_budget_lines_usd_passthrough() -> None:
    layer = load_fx_layer("series_b_weekly")
    budget = pd.DataFrame(
        {
            "row_id": ["B-1"],
            "currency": ["USD"],
            "amount_native": [1234.56],
            "iso_week": ["2018-W01"],
            "fx_tier": ["REF"],
        }
    )
    out = convert_budget_lines_to_usd(budget, layer)
    assert abs(out.loc[0, "amount_usd"] - 1234.56) < 1e-6


def test_unknown_currency_raises() -> None:
    layer = load_fx_layer("series_b_weekly")
    with pytest.raises(ValueError):
        layer.to_usd(100.0, "EUR", "2018-W01", "REF")
