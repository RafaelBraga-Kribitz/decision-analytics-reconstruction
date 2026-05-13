"""TDD tests for the FX normalization layer (Phase 5).

Tests are written test-first per plan §7 and are expected to FAIL until
module_b_resource_allocation/fx/tc_ref_loader.py and friends are implemented.
"""

from __future__ import annotations

import pandas as pd
import pytest
from module_b_resource_allocation.fx.fx_path import (
    FxPath,
    resolve_tc_for_week,
)
from module_b_resource_allocation.fx.spread_model import (
    apply_retail_spread,
    load_spread_config,
)
from module_b_resource_allocation.fx.tc_ref_loader import (
    TC_REF_COLUMNS,
    build_daily_series,
    load_weekly_prior,
    validate_daily_series,
)

# ---------------------------------------------------------------------------
# tc_ref_loader
# ---------------------------------------------------------------------------


def test_load_weekly_prior_returns_14_rows() -> None:
    prior = load_weekly_prior()
    assert len(prior) == 14, f"Expected 14 weekly rows, got {len(prior)}"


def test_build_daily_series_columns() -> None:
    df = build_daily_series()
    for col in TC_REF_COLUMNS:
        assert col in df.columns, f"Missing column: {col}"


def test_build_daily_series_date_range() -> None:
    df = build_daily_series()
    assert df["date"].min() >= pd.Timestamp("2018-01-01")
    assert df["date"].max() <= pd.Timestamp("2018-04-30")


def test_march_floor_enforced() -> None:
    """Every 2018-03-* row must have TC_Ref >= 5500.0 (plan §7.2 gate)."""
    df = build_daily_series()
    march = df[df["date"].dt.month == 3]
    assert len(march) > 0, "No March rows in daily series"
    violators = march[march["tc_ref"] < 5500.0]
    assert len(violators) == 0, (
        f"March floor violation: {len(violators)} rows below 5500. "
        f"Min={march['tc_ref'].min():.1f}"
    )


def test_april_band_enforced() -> None:
    """Every 2018-04-* row must have 5550 <= TC_Ref <= 5750 (plan §7.2 gate)."""
    df = build_daily_series()
    april = df[df["date"].dt.month == 4]
    assert len(april) > 0, "No April rows in daily series"
    low = april[april["tc_ref"] < 5550.0]
    high = april[april["tc_ref"] > 5750.0]
    assert len(low) == 0, f"{len(low)} April rows below 5550. Min={april['tc_ref'].min():.1f}"
    assert len(high) == 0, f"{len(high)} April rows above 5750. Max={april['tc_ref'].max():.1f}"


def test_weekend_holiday_forward_fill_flagged() -> None:
    """All imputed (weekend/holiday) rows must have tc_ref_imputed_flag=True."""
    df = build_daily_series()
    imputed = df[df["tc_ref_imputed_flag"]]
    # Weekends should be imputed; at minimum Jan 2018 has Sat/Sun entries
    assert len(imputed) > 0, "No imputed rows found; expected weekends to be flagged"
    # Every non-imputed row must be a business day
    non_imputed = df[~df["tc_ref_imputed_flag"]]
    assert (non_imputed["date"].dt.dayofweek < 5).all(), "Non-imputed rows include weekends"


def test_validate_daily_series_raises_on_march_violation() -> None:
    df = build_daily_series().copy()
    # Corrupt a March row
    march_idx = df[df["date"].dt.month == 3].index[0]
    df.loc[march_idx, "tc_ref"] = 5490.0
    with pytest.raises(ValueError, match="March floor"):
        validate_daily_series(df)


def test_validate_daily_series_raises_on_april_violation() -> None:
    df = build_daily_series().copy()
    april_idx = df[df["date"].dt.month == 4].index[0]
    df.loc[april_idx, "tc_ref"] = 5800.0
    with pytest.raises(ValueError, match="April band"):
        validate_daily_series(df)


# ---------------------------------------------------------------------------
# spread_model
# ---------------------------------------------------------------------------


def test_load_spread_config_returns_weekly_keys() -> None:
    cfg = load_spread_config()
    assert "series_b_weekly" in cfg
    assert len(cfg["series_b_weekly"]) == 14


def test_retail_equals_ref_plus_spread() -> None:
    """RETAIL = REF * (1 + spread_pct) per the spec Δ_spread rule (plan §7.2)."""
    df = build_daily_series()
    cfg = load_spread_config()
    df2 = apply_retail_spread(df, cfg)
    assert "tc_retail" in df2.columns
    # Spot-check: retail should exceed ref by a positive spread
    assert (df2["tc_retail"] > df2["tc_ref"]).all(), "tc_retail must always exceed tc_ref"


def test_retail_spread_default_positive() -> None:
    from module_b_resource_allocation.fx.spread_model import DEFAULT_SPREAD_PYG_PER_USD

    assert DEFAULT_SPREAD_PYG_PER_USD > 0


# ---------------------------------------------------------------------------
# fx_path
# ---------------------------------------------------------------------------


def test_fx_path_enum_has_two_scenarios() -> None:
    assert {FxPath.EARLY_LOCK, FxPath.LATE_FLEX} == set(FxPath)


def test_resolve_tc_early_lock_returns_locked_rate() -> None:
    df = build_daily_series()
    cfg = load_spread_config()
    df2 = apply_retail_spread(df, cfg)
    rate = resolve_tc_for_week(df2, "2018-W04", fx_path=FxPath.EARLY_LOCK, tier="REF")
    lock_rate = resolve_tc_for_week(df2, "2018-W01", fx_path=FxPath.EARLY_LOCK, tier="REF")
    # Under early_lock, all weeks should return the same locked rate (W01 anchor)
    rate2 = resolve_tc_for_week(df2, "2018-W10", fx_path=FxPath.EARLY_LOCK, tier="REF")
    assert rate == lock_rate == rate2, "early_lock must return the same rate for all weeks"


def test_resolve_tc_late_flex_varies_by_week() -> None:
    df = build_daily_series()
    cfg = load_spread_config()
    df2 = apply_retail_spread(df, cfg)
    early = resolve_tc_for_week(df2, "2018-W01", fx_path=FxPath.LATE_FLEX, tier="REF")
    late = resolve_tc_for_week(df2, "2018-W14", fx_path=FxPath.LATE_FLEX, tier="REF")
    # Jan W01 is weaker Guaraní (higher TC) than end-of-March → should differ
    assert early != late, "late_flex rates should vary by week"


def test_resolve_tc_retail_exceeds_ref() -> None:
    df = build_daily_series()
    cfg = load_spread_config()
    df2 = apply_retail_spread(df, cfg)
    ref_rate = resolve_tc_for_week(df2, "2018-W05", fx_path=FxPath.LATE_FLEX, tier="REF")
    retail_rate = resolve_tc_for_week(df2, "2018-W05", fx_path=FxPath.LATE_FLEX, tier="RETAIL")
    assert retail_rate > ref_rate, "RETAIL tier must exceed REF tier"
