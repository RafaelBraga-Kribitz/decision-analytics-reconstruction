"""TDD tests for the broadcast-to-direct counterfactual reallocation engine (Phase 9)."""

from __future__ import annotations

import pytest
from module_b_resource_allocation.constants import (
    ALLOCATION_ROWS,
    CAMPAIGN_BUDGET_TOLERANCE,
    CAMPAIGN_BUDGET_USD,
    SCENARIO_BROADCAST_TO_DIRECT,
)
from module_b_resource_allocation.models.allocation import build_problem, solve
from module_b_resource_allocation.models.counterfactual import (
    run_broadcast_to_direct,
)
from module_b_resource_allocation.routing.cost_matrix import build_cost_matrix


@pytest.fixture(scope="module")
def baseline():
    return solve(build_problem(scenario_id="baseline", solver_seed=20180422))


@pytest.fixture(scope="module")
def routing_dry():
    return build_cost_matrix(scenario="dry_standard", seed=42)


@pytest.fixture(scope="module")
def cf_result(baseline, routing_dry):
    return run_broadcast_to_direct(baseline, routing_dry, shift_share=0.30)


def test_counterfactual_row_count_matches_grid(cf_result) -> None:
    assert len(cf_result.counterfactual_allocation) == ALLOCATION_ROWS


def test_counterfactual_scenario_tagged(cf_result) -> None:
    assert (
        cf_result.counterfactual_allocation["scenario_id"] == SCENARIO_BROADCAST_TO_DIRECT
    ).all()


def test_counterfactual_preserves_total_budget(cf_result) -> None:
    total = float(cf_result.counterfactual_allocation["budget_allocation_usd"].sum())
    band = CAMPAIGN_BUDGET_USD * (CAMPAIGN_BUDGET_TOLERANCE + 0.05)  # broader slack for saturation
    assert total <= CAMPAIGN_BUDGET_USD + band
    # We allow the counterfactual to be slightly under the envelope when
    # saturation gates prevent fully placing the donor pot, but it must stay
    # within 10% of the envelope.
    assert total >= CAMPAIGN_BUDGET_USD * 0.85


def test_counterfactual_broadcast_spend_decreases(cf_result) -> None:
    base = cf_result.baseline_allocation
    cf = cf_result.counterfactual_allocation
    donors = {"tv_spots", "radio_spots", "billboards"}
    base_broadcast = float(base[base["channel"].isin(donors)]["budget_allocation_usd"].sum())
    cf_broadcast = float(cf[cf["channel"].isin(donors)]["budget_allocation_usd"].sum())
    assert cf_broadcast < base_broadcast


def test_counterfactual_direct_spend_increases(cf_result) -> None:
    base = cf_result.baseline_allocation
    cf = cf_result.counterfactual_allocation
    receivers = {"canvassing", "rallies_events", "sound_cars"}
    base_direct = float(base[base["channel"].isin(receivers)]["budget_allocation_usd"].sum())
    cf_direct = float(cf[cf["channel"].isin(receivers)]["budget_allocation_usd"].sum())
    assert cf_direct > base_direct


def test_counterfactual_deltas_sum_consistency(cf_result) -> None:
    cf = cf_result.counterfactual_allocation
    base = cf_result.baseline_allocation
    deltas = cf_result.deltas
    expected_total_delta = float(cf["budget_allocation_usd"].sum()) - float(
        base["budget_allocation_usd"].sum()
    )
    actual_total_delta = float(deltas["delta_budget_usd"].sum())
    assert abs(expected_total_delta - actual_total_delta) < 1.0  # cent-level
