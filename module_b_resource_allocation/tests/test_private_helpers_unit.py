"""Unit tests for selected private helpers in Module B (line 79 continuation).

Pure logic with no YAML/network; complements integration tests elsewhere.
"""

from __future__ import annotations

import math
import random

import numpy as np
import pandas as pd
import pytest
from module_b_resource_allocation.api.app import _frame_to_records
from module_b_resource_allocation.constants import CAMPAIGN_BUDGET_USD, WEEK_LABELS
from module_b_resource_allocation.data.cleaner import (
    _canonical_channel,
    _canonical_currency,
    _canonical_department,
    _parse_locale_number,
    _strip_accents,
    _valid_week,
)
from module_b_resource_allocation.data.dirty_generator import (
    _maybe_swap_locale,
    _maybe_with_noise,
    _pick,
)
from module_b_resource_allocation.data.fx import FxLayer, _monthly_to_weekly
from module_b_resource_allocation.features.diminishing_returns import _build_breakpoints
from module_b_resource_allocation.features.reach_caps import _fta_tv_cap, _internet_cap, _mobile_cap
from module_b_resource_allocation.models.allocation import (
    _expected_contacts,
    _load_bundles,
    _scenario_week_weight,
    _tier_penalty,
    _unit_cost_usd,
)
from module_b_resource_allocation.models.allocation_lp import (
    _infer_bundle_active,
    _scenario_id_from_fx_path,
)
from module_b_resource_allocation.models.counterfactual import _routing_feasible_in_week
from module_b_resource_allocation.reporting.baselines import _water_fill
from module_b_resource_allocation.routing.cost_matrix import (
    SurfaceMix,
    _great_circle_km,
    _region_pair,
    _surface_class_for,
    _surface_mix,
    _time_multiplier,
    _weather_p_fail,
)
from module_b_resource_allocation.routing.nearest_insertion import _tour_length
from module_b_resource_allocation.routing.two_opt import _tour_length as _tour_length_two_opt


def test_great_circle_km_same_point_zero() -> None:
    p = (-25.30, -57.63)
    assert _great_circle_km(p, p) == pytest.approx(0.0, abs=1e-9)


def test_great_circle_km_asuncion_to_central_positive() -> None:
    """Smoke: two anchored centroids in ``cost_matrix`` yield a plausible road-scale km."""
    d = _great_circle_km((-25.30, -57.63), (-25.40, -57.45))
    assert 10.0 < d < 50.0


@pytest.mark.parametrize(
    ("caps", "budget", "expected_sum"),
    [
        ([], 100.0, 0.0),
        ([10.0, 10.0], 5.0, 5.0),
        ([2.0, 3.0], 10.0, 5.0),
    ],
)
def test_water_fill_budget_respects_caps_and_sum(
    caps: list[float], budget: float, expected_sum: float
) -> None:
    out = _water_fill(caps, budget)
    assert sum(out) == pytest.approx(expected_sum, abs=1e-5)
    for x, cap in zip(out, caps, strict=True):
        assert x <= cap + 1e-6


def test_monthly_to_weekly_expands_all_campaign_weeks() -> None:
    monthly = {
        "2018-01": 0.01,
        "2018-02": 0.02,
        "2018-03": 0.03,
        "2018-04": 0.04,
    }
    weekly = _monthly_to_weekly(monthly)
    assert set(weekly.keys()) == {f"2018-W{i:02d}" for i in range(1, 15)}
    for w in ["2018-W01", "2018-W02", "2018-W03", "2018-W04"]:
        assert weekly[w] == pytest.approx(0.01)
    assert weekly["2018-W14"] == pytest.approx(0.04)


def test_monthly_to_weekly_missing_month_keyerror() -> None:
    with pytest.raises(KeyError, match="2018-01"):
        _monthly_to_weekly({"2018-02": 0.1, "2018-03": 0.1, "2018-04": 0.1})


@pytest.mark.parametrize(
    ("tier", "expected"),
    [
        ("stronghold", 1.00),
        ("swing", 1.10),
        ("opposition", 0.85),
        ("negligible", 0.55),
    ],
)
def test_tier_penalty_known_tiers(tier: str, expected: float) -> None:
    assert _tier_penalty(tier) == pytest.approx(expected)


def test_tier_penalty_unknown_raises() -> None:
    with pytest.raises(KeyError):
        _tier_penalty("unknown_tier")


def test_tour_length_closed_loop() -> None:
    dist = {
        ("A", "B"): 1.0,
        ("B", "A"): 1.0,
        ("A", "A"): 0.0,
        ("B", "B"): 0.0,
    }
    assert _tour_length(["A", "B"], dist) == pytest.approx(2.0)
    assert _tour_length_two_opt(["A", "B"], dist) == pytest.approx(2.0)


def test_tour_length_short_tour() -> None:
    assert _tour_length(["A"], {("A", "A"): 0.0}) == 0.0


@pytest.mark.parametrize(
    ("audience", "used", "expected"),
    [
        (0.0, 0.5, 0.0),
        (100.0, 0.0, 0.0),
        (100.0, 0.5, 50.0),
    ],
)
def test_expected_contacts_edge_linear_region(
    audience: float, used: float, expected: float
) -> None:
    out = _expected_contacts(audience, used, k=2.0, inflection_pct=0.5)
    assert out == pytest.approx(expected, rel=0, abs=1e-9)


def test_expected_contacts_saturates_above_inflection() -> None:
    out = _expected_contacts(100.0, 1.0, k=2.0, inflection_pct=0.2)
    linear = 100.0 * 0.2
    residual = 100.0 * 0.8
    saturation = 1.0 - math.exp(-2.0 * (1.0 - 0.2))
    assert out == pytest.approx(linear + residual * saturation)


@pytest.mark.parametrize(
    ("scenario_id", "week_idx", "expected"),
    [
        ("early_lock", 1, 1.15),
        ("early_lock", 10, 0.95),
        ("late_flex", 3, 0.92),
        ("late_flex", 10, 1.20),
        ("baseline", 7, 1.0),
    ],
)
def test_scenario_week_weight(scenario_id: str, week_idx: int, expected: float) -> None:
    assert _scenario_week_weight(scenario_id, week_idx) == pytest.approx(expected)


def test_scenario_id_from_fx_path() -> None:
    assert _scenario_id_from_fx_path("baseline") == "baseline"
    assert _scenario_id_from_fx_path("not_a_real_scenario") == "baseline"


def test_infer_bundle_active_empty_vs_funded() -> None:
    empty = pd.DataFrame(columns=["channel", "budget_allocation_usd"])
    out_empty = _infer_bundle_active(empty)
    assert all(v is False for v in out_empty.values())

    big = CAMPAIGN_BUDGET_USD * 0.1
    funded = pd.DataFrame({"channel": ["tv_spots"], "budget_allocation_usd": [big]})
    out_f = _infer_bundle_active(funded)
    assert out_f.get("conglomerate_x") is True


@pytest.mark.parametrize(
    ("mix", "expected"),
    [
        (SurfaceMix(0.9, 0.08, 0.02), "paved"),
        (SurfaceMix(0.2, 0.5, 0.3), "unpaved_tertiary"),
        (SurfaceMix(0.1, 0.2, 0.7), "earth_track"),
    ],
)
def test_surface_class_for(mix: SurfaceMix, expected: str) -> None:
    assert _surface_class_for(mix) == expected


def test_time_multiplier_wet_penalises_non_paved() -> None:
    base_p = _time_multiplier("paved", "wet_election_week")
    base_u = _time_multiplier("unpaved_tertiary", "wet_election_week")
    assert base_p == pytest.approx(1.0)
    assert base_u == pytest.approx(3.0 * 1.15)


@pytest.mark.parametrize(
    ("origin", "dest", "scenario", "chaco_multiplier"),
    [
        ("Asuncion", "Central", "dry_standard", 0.50),
        ("Presidente Hayes", "Boqueron", "dry_standard", 1.20),
    ],
)
def test_weather_p_fail_scales_chaco(
    origin: str, dest: str, scenario: str, chaco_multiplier: float
) -> None:
    base = 70.0 / 365.0
    p = _weather_p_fail(origin, dest, scenario)
    assert p == pytest.approx(base * chaco_multiplier)


def test_region_pair_labels() -> None:
    assert _region_pair("Asuncion", "Asuncion") == "SELF"
    assert _region_pair("Asuncion", "Central") == "ORIENTAL_ORIENTAL"
    assert _region_pair("Presidente Hayes", "Boqueron") == "CHACO_CHACO"
    assert _region_pair("Asuncion", "Presidente Hayes") == "ORIENTAL_CHACO"


def test_surface_mix_corridor_deterministic() -> None:
    rng = random.Random(0)
    mix = _surface_mix("Asuncion", "Central", "dry_standard", rng)
    assert mix.paved == pytest.approx(0.90)
    assert mix.unpaved_tertiary == pytest.approx(0.08)
    assert mix.earth_track == pytest.approx(0.02)


def test_strip_accents_removes_combining_marks() -> None:
    assert _strip_accents("José") == "Jose"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("TV Spot", "tv_spots"),
        ("tv", "tv_spots"),
        ("  ", None),
        (None, None),
    ],
)
def test_canonical_channel(raw: str | None, expected: str | None) -> None:
    assert _canonical_channel(raw) == expected


def test_canonical_department_accent_alias() -> None:
    assert _canonical_department("Asunción") == "Asuncion"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("usd", "USD"),
        ("₲", "PYG"),
        ("xx", None),
    ],
)
def test_canonical_currency(raw: str | None, expected: str | None) -> None:
    assert _canonical_currency(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1.234,56", 1234.56),
        ("1,234.56", 1234.56),
        ("Gs. 1000", 1000.0),
    ],
)
def test_parse_locale_number_parses_numeric(raw: str, expected: float) -> None:
    assert _parse_locale_number(raw) == pytest.approx(expected)


def test_parse_locale_number_none_on_invalid() -> None:
    assert _parse_locale_number(None) is None


def test_valid_week() -> None:
    assert _valid_week(WEEK_LABELS[0]) == WEEK_LABELS[0]
    assert _valid_week("nope") is None


def test_build_breakpoints_zero_and_positive() -> None:
    z = _build_breakpoints(0.0, k=6)
    assert len(z) == 6
    assert all(x == 0.0 for x in z)
    b = _build_breakpoints(1000.0, k=6)
    assert len(b) == 6
    assert b[0] == pytest.approx(0.0, abs=1e-6)
    assert b[-1] <= 1000.0
    assert all(b[i] <= b[i + 1] for i in range(len(b) - 1))


def test_reach_cap_helpers_in_range() -> None:
    assert 0.0 <= _internet_cap("Central") <= 1.0
    assert 0.0 <= _fta_tv_cap("Asuncion") <= 1.0
    assert _mobile_cap("Central") == pytest.approx(1.0)


def test_dirty_generator_helpers_deterministic() -> None:
    rng = np.random.default_rng(0)
    assert _maybe_with_noise("hello", rng, p=0.0) == "hello"
    assert _maybe_swap_locale(1234.5, rng, rate=0.0) == "1,234.50"
    assert _pick(["only"], rng) == "only"


def test_frame_to_records_roundtrip_shape() -> None:
    df = pd.DataFrame({"a": [1], "b": ["x"]})
    recs = _frame_to_records(df)
    assert recs == [{"a": 1, "b": "x"}]


def test_routing_feasible_in_week_smoke() -> None:
    rc = pd.DataFrame(
        {
            "origin_department": ["Central", "Central"],
            "destination_department": ["Asuncion", "Central"],
            "edge_feasible": [True, False],
        }
    )
    assert _routing_feasible_in_week(rc, week_index=1, department="Central") is True


def test_unit_cost_usd_ref_and_retail() -> None:
    layer = FxLayer(
        series_id="series_b_weekly",
        ref_by_week={"2018-W01": 5600.0},
        retail_by_week={"2018-W01": 6020.0},
        spread_by_week={"2018-W01": 0.05},
    )
    row_ref = pd.Series({"fx_tier_default": "REF", "unit_cost_pyg": 5600.0})
    assert _unit_cost_usd(row_ref, layer, "2018-W01") == pytest.approx(1.0)
    row_rt = pd.Series({"fx_tier_default": "RETAIL", "unit_cost_pyg": 6020.0})
    assert _unit_cost_usd(row_rt, layer, "2018-W01") == pytest.approx(1.0)


def test_load_bundles_returns_non_empty_dict() -> None:
    bundles = _load_bundles()
    assert isinstance(bundles, dict)
    assert len(bundles) >= 1
