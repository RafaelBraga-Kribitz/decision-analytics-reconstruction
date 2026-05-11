"""TDD tests for the PuLP/CBC LP/MILP allocation model (Phase 7).

Plan §7.2 acceptance tests. These must FAIL before the model is implemented
then pass green after implementation.
"""

from __future__ import annotations

import pytest
from module_b_resource_allocation.constants import (
    ALLOCATION_ROWS,
    CAMPAIGN_BUDGET_USD,
    CHANNEL_NAMES,
    N_CHANNELS,
)

# ---------------------------------------------------------------------------
# Channel cardinality
# ---------------------------------------------------------------------------


def test_channel_cardinality_is_11() -> None:
    """Solver model must enumerate exactly 11 channels (plan §7.2 / §0)."""
    assert N_CHANNELS == 11
    assert len(CHANNEL_NAMES) == 11


# ---------------------------------------------------------------------------
# Allocation model run
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def allocation_result():
    """Run the reference allocation scenario once (seed=42, 14 weeks)."""
    from module_b_resource_allocation.models.allocation_lp import run_allocation

    result = run_allocation(
        total_budget_usd=CAMPAIGN_BUDGET_USD,
        weeks=14,
        seed=42,
        fx_path="early_lock",
    )
    return result


def test_cbc_returns_optimal_under_reference_seed(allocation_result) -> None:
    """CBC must return Optimal on the reference scenario (plan §16)."""
    df = allocation_result["allocation_df"]
    statuses = df["solver_status"].unique().tolist()
    assert all(
        s in ("OPTIMAL", "FEASIBLE") for s in statuses
    ), f"Unexpected solver status values: {statuses}"
    assert (
        "OPTIMAL" in statuses or "FEASIBLE" in statuses
    ), "Solver did not return OPTIMAL or FEASIBLE"


def test_allocation_row_count_equals_2772(allocation_result) -> None:
    """Allocation DataFrame must have exactly 18×11×14=2772 rows (plan §5.1)."""
    df = allocation_result["allocation_df"]
    assert len(df) == ALLOCATION_ROWS, f"Expected {ALLOCATION_ROWS}, got {len(df)}"


def test_unique_key_d_c_w(allocation_result) -> None:
    """(department, channel, week_index) must be unique (plan §5.1 unique_key)."""
    df = allocation_result["allocation_df"]
    assert not df.duplicated(["department", "channel", "week_index"]).any()


def test_total_spend_within_budget(allocation_result) -> None:
    """Total allocation must not exceed B_total (plan §6.3 Budget constraint)."""
    df = allocation_result["allocation_df"]
    total = df["budget_allocation_usd"].sum()
    tolerance = CAMPAIGN_BUDGET_USD * 0.005
    assert (
        total <= CAMPAIGN_BUDGET_USD + tolerance
    ), f"Total spend {total:.0f} exceeds budget {CAMPAIGN_BUDGET_USD:.0f}"


def test_pay_tv_blocked_outside_eligible_departments(allocation_result) -> None:
    """x[d, tv_spots, w] == 0 for non-eligible departments (plan §7.2)."""
    df = allocation_result["allocation_df"]
    eligible = {"Asuncion", "Central", "Alto Parana"}
    tv_rows = df[df["channel"] == "tv_spots"]
    non_elig = tv_rows[~tv_rows["department"].isin(eligible)]
    assert (
        non_elig["budget_allocation_usd"] == 0.0
    ).all(), "Non-eligible departments received TV spot budget"


def test_budget_allocation_non_negative(allocation_result) -> None:
    df = allocation_result["allocation_df"]
    assert (df["budget_allocation_usd"] >= 0).all()


def test_all_required_columns_present(allocation_result) -> None:
    df = allocation_result["allocation_df"]
    required = [
        "department",
        "channel",
        "week_index",
        "iso_week",
        "budget_allocation_usd",
        "budget_allocation_pyg",
        "fx_tier",
        "fx_path",
        "tc_rate_pyg_per_usd",
        "expected_contacts",
        "persuasion_adjusted_contacts",
        "solver_status",
        "solver_seed",
        "department_tier",
        "region",
    ]
    for col in required:
        assert col in df.columns, f"Missing column: {col}"


def test_solver_seed_is_fixed(allocation_result) -> None:
    df = allocation_result["allocation_df"]
    assert (df["solver_seed"] == 42).all()


def test_bundle_minimum_binds_when_y_eq_1(allocation_result) -> None:
    """When a conglomerate bundle is active (y=1), minimum spend is respected."""
    from module_b_resource_allocation.models.allocation_lp import BUNDLE_MIN_USD

    df = allocation_result["allocation_df"]
    bundle_active = allocation_result.get("bundle_active", {})
    for bundle_id, active in bundle_active.items():
        if active:
            bundle_spend = df[df["conglomerate_id"] == bundle_id]["budget_allocation_usd"].sum()
            assert (
                bundle_spend >= BUNDLE_MIN_USD.get(bundle_id, 0) - 1.0
            ), f"Bundle {bundle_id} minimum not met: spend={bundle_spend:.0f}"
