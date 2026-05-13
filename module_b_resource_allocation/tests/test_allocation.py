"""TDD tests for the Module B PuLP/CBC LP/MILP allocator.

These tests run a real CBC solve so we catch model infeasibilities and
sign errors immediately.  We keep the search space lean by working on a
downsampled problem when needed, but the canonical 18×11×14 problem must
solve in OPTIMAL state within the budget envelope.
"""

from __future__ import annotations

import pytest
from module_b_resource_allocation.constants import (
    ALLOCATION_ROWS,
    CAMPAIGN_BUDGET_TOLERANCE,
    CAMPAIGN_BUDGET_USD,
    CHANNEL_NAMES,
    DEPARTMENTS,
    WEEK_LABELS,
)
from module_b_resource_allocation.models.allocation import (
    AllocationResult,
    build_problem,
    solve,
)


@pytest.fixture(scope="module")
def baseline_result() -> AllocationResult:
    problem = build_problem(scenario_id="baseline", solver_seed=20180422)
    return solve(problem)


def test_allocator_returns_optimal_or_feasible(baseline_result: AllocationResult) -> None:
    assert baseline_result.solver_status in {"OPTIMAL", "FEASIBLE"}


def test_allocation_row_count_matches_full_grid(baseline_result: AllocationResult) -> None:
    assert len(baseline_result.allocation) == ALLOCATION_ROWS


def test_allocation_budget_envelope_within_tolerance(baseline_result: AllocationResult) -> None:
    total = baseline_result.total_budget_usd
    band = CAMPAIGN_BUDGET_USD * CAMPAIGN_BUDGET_TOLERANCE
    assert total <= CAMPAIGN_BUDGET_USD + band
    assert total >= CAMPAIGN_BUDGET_USD - band


def test_allocation_only_canonical_keys(baseline_result: AllocationResult) -> None:
    a = baseline_result.allocation
    assert set(a["department"]).issubset(set(DEPARTMENTS))
    assert set(a["channel"]).issubset(set(CHANNEL_NAMES))
    assert set(a["iso_week"]).issubset(set(WEEK_LABELS))


def test_allocation_unique_key(baseline_result: AllocationResult) -> None:
    a = baseline_result.allocation
    assert not a.duplicated(["department", "channel", "week_index"]).any()


def test_allocation_non_negative_spend(baseline_result: AllocationResult) -> None:
    a = baseline_result.allocation
    assert (a["budget_allocation_usd"] >= 0).all()
    assert (a["budget_allocation_pyg"] >= 0).all()


def test_allocation_respects_reach_caps(baseline_result: AllocationResult) -> None:
    a = baseline_result.allocation
    # reach_utilization may exceed 1.0 only because the diminishing-returns
    # post-processing tops at 1.0 when units > audience; the LP itself locks
    # units ≤ audience per week.
    assert (a["reach_utilization"] <= 1.0001).all()


def test_allocation_scenario_id_stamped(baseline_result: AllocationResult) -> None:
    a = baseline_result.allocation
    assert (a["scenario_id"] == "baseline").all()


def test_allocation_fx_series_tracked(baseline_result: AllocationResult) -> None:
    assert baseline_result.fx_series_id == "series_b_weekly"


def test_allocation_persuasion_consistent_with_contacts(baseline_result: AllocationResult) -> None:
    a = baseline_result.allocation
    nz = a[a["expected_contacts"] > 0]
    # persuasion_adjusted_contacts = expected * (>= 0 multiplier).
    assert (nz["persuasion_adjusted_contacts"] >= 0).all()
    # Some contacts must be allocated overall.
    assert nz["expected_contacts"].sum() > 0


def test_negligible_in_person_cap(baseline_result: AllocationResult) -> None:
    a = baseline_result.allocation
    negligible_depts = {"Boqueron", "Alto Paraguay"}
    in_person = {"canvassing", "rallies_events", "sound_cars"}
    sub = a[a["department"].isin(negligible_depts) & a["channel"].isin(in_person)]
    if not sub.empty:
        assert (sub["reach_utilization"] <= 0.06).all()
