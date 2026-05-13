"""Contract validation tests for allocation_output schema (plan §7.2)."""

from __future__ import annotations

import pytest
from module_b_resource_allocation.constants import ALLOCATION_ROWS, CAMPAIGN_BUDGET_USD


@pytest.fixture(scope="module")
def allocation_df():
    from module_b_resource_allocation.models.allocation_lp import run_allocation

    result = run_allocation(
        total_budget_usd=CAMPAIGN_BUDGET_USD,
        weeks=14,
        seed=42,
        fx_path="early_lock",
    )
    return result["allocation_df"]


def test_allocation_row_count_equals_2772(allocation_df) -> None:
    assert len(allocation_df) == ALLOCATION_ROWS


def test_solver_status_only_optimal_or_feasible(allocation_df) -> None:
    """Contract gate: solver_status must ∈ {OPTIMAL, FEASIBLE} (plan §5.1)."""
    bad = allocation_df[~allocation_df["solver_status"].isin({"OPTIMAL", "FEASIBLE"})]
    assert len(bad) == 0, f"Bad solver statuses: {bad['solver_status'].unique()}"


def test_unique_key_d_c_w(allocation_df) -> None:
    assert not allocation_df.duplicated(["department", "channel", "week_index"]).any()


def test_week_index_range(allocation_df) -> None:
    assert allocation_df["week_index"].between(1, 14).all()


def test_channel_values_canonical(allocation_df) -> None:
    from module_b_resource_allocation.constants import CHANNEL_NAMES

    assert set(allocation_df["channel"].unique()) == set(CHANNEL_NAMES)


def test_department_values_canonical(allocation_df) -> None:
    from module_b_resource_allocation.constants import DEPARTMENTS

    assert set(allocation_df["department"].unique()) == set(DEPARTMENTS)
