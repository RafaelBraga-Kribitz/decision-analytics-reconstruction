"""Regression tests for ``tsp_router`` — NN + 2-opt across weather scenarios."""

from __future__ import annotations

import pandas as pd
import pytest
from module_b_resource_allocation.constants import DEPARTMENTS, WEEK_LABELS
from module_b_resource_allocation.routing.tsp_router import (
    WEATHER_SCENARIOS,
    build_routing_schedule_for_scenario,
    build_routing_schedules,
    write_routing_schedules,
)


def test_routing_schedule_shape_for_one_scenario() -> None:
    df = build_routing_schedule_for_scenario("dry_standard", seed=20180422)
    # Each week visits every department once.
    assert len(df) == len(WEEK_LABELS) * len(DEPARTMENTS)
    assert set(df["weather_scenario"].unique()) == {"dry_standard"}
    assert set(df["week_label"].unique()) == set(WEEK_LABELS)
    # Each (week, scenario) visits all 18 departments.
    counts = df.groupby("week_label")["department"].nunique()
    assert (counts == len(DEPARTMENTS)).all()


def test_all_three_weather_scenarios_present() -> None:
    df = build_routing_schedules(seed=20180422)
    assert set(df["weather_scenario"].unique()) == set(WEATHER_SCENARIOS)
    assert len(df) == len(WEATHER_SCENARIOS) * len(WEEK_LABELS) * len(DEPARTMENTS)


def test_routing_schedule_deterministic_under_fixed_seed() -> None:
    a = build_routing_schedules(seed=20180422)
    b = build_routing_schedules(seed=20180422)
    pd.testing.assert_frame_equal(a, b)


def test_wet_scenario_longer_routes_than_dry() -> None:
    """Wet edges add a 15% non-paved time penalty; total tour minutes must grow."""
    dry = build_routing_schedule_for_scenario("dry_standard", seed=20180422)
    wet = build_routing_schedule_for_scenario("wet_election_week", seed=20180422)
    dry_total = dry.groupby("week_label")["tour_total_travel_time_minutes"].first().sum()
    wet_total = wet.groupby("week_label")["tour_total_travel_time_minutes"].first().sum()
    assert wet_total > dry_total


def test_chaco_stress_longer_than_dry() -> None:
    """Chaco stress increases earth-track share on Chaco edges; expect longer than dry.

    NOTE: chaco_stress is scoped to Chaco-touching edges only (no global non-paved
    time penalty), so it does not strictly dominate wet_election_week which applies
    the +15% penalty to all non-paved edges. Compare only to the dry baseline.
    """
    dry = build_routing_schedule_for_scenario("dry_standard", seed=20180422)
    chaco = build_routing_schedule_for_scenario("chaco_stress", seed=20180422)
    dry_total = dry.groupby("week_label")["tour_total_travel_time_minutes"].first().sum()
    chaco_total = chaco.groupby("week_label")["tour_total_travel_time_minutes"].first().sum()
    assert chaco_total > dry_total


def test_cumulative_columns_monotonic() -> None:
    df = build_routing_schedule_for_scenario("dry_standard", seed=20180422)
    for _, grp in df.groupby("week_label"):
        cum_km = grp.sort_values("tour_position")["cumulative_km"].to_numpy()
        cum_min = grp.sort_values("tour_position")["cumulative_travel_time_minutes"].to_numpy()
        # Cumulative must be non-decreasing.
        assert (cum_km[1:] - cum_km[:-1] >= -1e-9).all()
        assert (cum_min[1:] - cum_min[:-1] >= -1e-9).all()


def test_write_routing_schedules_creates_parquet(tmp_path) -> None:
    out = write_routing_schedules(tmp_path, seed=20180422)
    assert out.exists()
    df = pd.read_parquet(out)
    assert len(df) == len(WEATHER_SCENARIOS) * len(WEEK_LABELS) * len(DEPARTMENTS)


def test_invalid_scenario_raises() -> None:
    with pytest.raises(ValueError):
        build_routing_schedule_for_scenario("invalid_scenario", seed=42)
