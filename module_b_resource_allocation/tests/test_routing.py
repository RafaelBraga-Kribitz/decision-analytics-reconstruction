"""TDD tests for the routing realism layer (Phase 8).

Tests per plan §7.2. Must FAIL before routing modules are implemented.
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Cost matrix
# ---------------------------------------------------------------------------


def test_cost_matrix_returns_dataframe() -> None:
    from module_b_resource_allocation.routing.cost_matrix import build_cost_matrix

    df = build_cost_matrix(scenario="dry_standard", seed=42)
    assert len(df) > 0


def test_cost_matrix_has_required_columns() -> None:
    from module_b_resource_allocation.routing.cost_matrix import build_cost_matrix

    df = build_cost_matrix(scenario="dry_standard", seed=42)
    required = [
        "origin_department",
        "destination_department",
        "scenario_id",
        "surface_class",
        "travel_time_minutes",
        "time_multiplier",
        "weather_p_fail",
        "tau_walk_minutes_mean",
        "edge_feasible",
    ]
    for col in required:
        assert col in df.columns, f"Missing column: {col}"


def test_cost_matrix_self_loops_zero_distance() -> None:
    from module_b_resource_allocation.routing.cost_matrix import build_cost_matrix

    df = build_cost_matrix(scenario="dry_standard", seed=42)
    self_loops = df[df["origin_department"] == df["destination_department"]]
    assert (self_loops["travel_time_minutes"] == 0.0).all()


def test_chaco_unpaved_share_above_90_pct() -> None:
    """Under chaco_stress, >= 90% of Chaco edges must be unpaved (plan §7.2 gate)."""
    from module_b_resource_allocation.routing.cost_matrix import build_cost_matrix

    df = build_cost_matrix(scenario="chaco_stress", seed=42)
    chaco = {"Presidente Hayes", "Boqueron", "Alto Paraguay"}
    chaco_edges = df[df["origin_department"].isin(chaco) | df["destination_department"].isin(chaco)]
    unpaved_share = (chaco_edges["surface_class"].isin(["unpaved_tertiary", "earth_track"])).mean()
    assert unpaved_share >= 0.90, f"Chaco unpaved share {unpaved_share:.2f} < 0.90"


def test_oriente_paved_vmax_above_70_kmh() -> None:
    """For paved Oriente edges, implied speed >= 70 km/h (plan §7.2 gate)."""
    from module_b_resource_allocation.routing.cost_matrix import build_cost_matrix

    df = build_cost_matrix(scenario="dry_standard", seed=42)
    oriente_paved = df[
        (df["surface_class"] == "paved")
        & (~df["origin_department"].isin(["Presidente Hayes", "Boqueron", "Alto Paraguay"]))
        & (~df["destination_department"].isin(["Presidente Hayes", "Boqueron", "Alto Paraguay"]))
        & (df["origin_department"] != df["destination_department"])
    ]
    if len(oriente_paved) == 0:
        pytest.skip("No paved Oriente edges to test")
    speeds = oriente_paved["base_distance_km"] / (oriente_paved["travel_time_minutes"] / 60.0)
    assert (
        speeds >= 70.0
    ).all(), f"Some Oriente paved edges have speed < 70 km/h. Min={speeds.min():.1f}"


def test_shift_cap_enforced() -> None:
    """No feasible route should exceed 8 hours total time (plan §4.6 guard)."""
    from module_b_resource_allocation.routing.cost_matrix import build_cost_matrix

    df = build_cost_matrix(scenario="dry_standard", seed=42)
    shift_cap_minutes = 8 * 60
    feasible = df[df["edge_feasible"]]
    assert (feasible["travel_time_minutes"] <= shift_cap_minutes).all()


# ---------------------------------------------------------------------------
# Routing heuristic
# ---------------------------------------------------------------------------


def test_nearest_insertion_returns_tour() -> None:
    from module_b_resource_allocation.routing.nearest_insertion import nearest_insertion_tour

    # Small 5-node test
    dist = {(i, j): abs(i - j) * 10.0 for i in range(5) for j in range(5)}
    tour, length = nearest_insertion_tour(nodes=list(range(5)), dist=dist, seed=42)
    assert len(tour) == 5
    assert length > 0


def test_2opt_improves_or_preserves_tour_length() -> None:
    """2-opt tour length must be <= nearest-insertion length (plan §7.2 gate)."""
    import random

    from module_b_resource_allocation.routing.nearest_insertion import nearest_insertion_tour
    from module_b_resource_allocation.routing.two_opt import two_opt_improve

    rng = random.Random(42)
    n = 10
    nodes = list(range(n))
    dist = {}
    for i in nodes:
        for j in nodes:
            if i != j:
                dist[i, j] = rng.uniform(10, 100)

    tour_ni, len_ni = nearest_insertion_tour(nodes, dist, seed=42)
    tour_2opt, len_2opt = two_opt_improve(tour_ni, dist)

    assert (
        len_2opt <= len_ni + 1e-6
    ), f"2-opt length {len_2opt:.2f} > nearest-insertion {len_ni:.2f}"


def test_scenarios_produce_different_matrices() -> None:
    from module_b_resource_allocation.routing.cost_matrix import build_cost_matrix

    df_dry = build_cost_matrix(scenario="dry_standard", seed=42)
    df_wet = build_cost_matrix(scenario="wet_election_week", seed=42)
    # Wet scenario should have more infeasible edges or different timings
    assert not (df_dry["travel_time_minutes"].values == df_wet["travel_time_minutes"].values).all()
