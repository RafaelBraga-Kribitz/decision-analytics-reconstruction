"""Tests for budget expansion sensitivity (reporting.budget_sensitivity)."""

from __future__ import annotations

import pytest
from module_b_resource_allocation.constants import CAMPAIGN_BUDGET_USD
from module_b_resource_allocation.models.allocation import build_problem, solve
from module_b_resource_allocation.reporting.budget_sensitivity import (
    BUDGET_EXPANSION_MULTIPLIERS,
    compute_budget_expansion_curve,
)


def test_compute_budget_expansion_curve_shape() -> None:
    curve = compute_budget_expansion_curve(
        scenario_id="baseline",
        fx_series_id="series_b_weekly",
        solver_seed=20180422,
    )
    assert len(curve) == len(BUDGET_EXPANSION_MULTIPLIERS)
    for row in curve:
        assert "budget_multiplier" in row
        assert "budget_target_usd" in row
        assert "total_persuasion_adjusted_contacts" in row
        assert "total_budget_usd" in row
        assert "solver_status" in row
        assert "pulp_status_code" in row
        assert row["budget_target_usd"] == pytest.approx(
            CAMPAIGN_BUDGET_USD * float(row["budget_multiplier"]), rel=0, abs=0.05
        )


def test_budget_expansion_matches_direct_solve_at_one_multiplier() -> None:
    m = 1.0
    problem = build_problem(
        scenario_id="baseline",
        fx_series_id="series_b_weekly",
        solver_seed=42,
        budget_usd=CAMPAIGN_BUDGET_USD * m,
    )
    direct = solve(problem)
    curve = compute_budget_expansion_curve(
        scenario_id="baseline",
        fx_series_id="series_b_weekly",
        solver_seed=42,
    )
    row1 = next(r for r in curve if abs(float(r["budget_multiplier"]) - m) < 1e-9)
    assert row1["total_persuasion_adjusted_contacts"] == pytest.approx(
        direct.total_persuasion_adjusted_contacts, rel=1e-6, abs=0.01
    )
    assert row1["total_budget_usd"] == pytest.approx(direct.total_budget_usd, rel=1e-6, abs=1.0)


def test_budget_expansion_objective_non_decreasing_when_optimal() -> None:
    curve = compute_budget_expansion_curve(
        scenario_id="baseline",
        fx_series_id="series_b_weekly",
        solver_seed=20180422,
    )
    import pulp

    contacts: list[float] = []
    for row in curve:
        if int(row["pulp_status_code"]) != pulp.LpStatusOptimal:
            continue
        contacts.append(float(row["total_persuasion_adjusted_contacts"]))
    assert len(contacts) >= 2
    assert contacts == sorted(contacts), "objective should not decrease with larger budget envelope"
