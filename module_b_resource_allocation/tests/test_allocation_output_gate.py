"""Tests for post-solve allocation_output contract gate."""

from __future__ import annotations

import pytest
from module_b_resource_allocation.constants import COVERAGE_LOWER_BOUND_PCT
from module_b_resource_allocation.models.allocation import build_problem, solve
from module_b_resource_allocation.utils.allocation_output_gate import (
    validate_allocation_output_df,
)


@pytest.fixture(scope="module")
def baseline_result():
    return solve(build_problem(scenario_id="baseline", solver_seed=20180422))


def test_validate_passes_on_canonical_solve(baseline_result) -> None:
    validate_allocation_output_df(baseline_result.allocation)


def test_validate_rejects_wrong_row_count(baseline_result) -> None:
    bad = baseline_result.allocation.head(10)
    with pytest.raises(ValueError, match="row_count"):
        validate_allocation_output_df(bad)


def test_validate_rejects_budget_envelope_breach(baseline_result) -> None:
    bad = baseline_result.allocation.copy()
    bad["budget_allocation_usd"] = bad["budget_allocation_usd"] * 2.0
    with pytest.raises(ValueError, match="budget_envelope"):
        validate_allocation_output_df(bad)


def test_validate_rejects_coverage_floor_breach(baseline_result) -> None:
    bad = baseline_result.allocation.copy()
    dept = bad["department"].iloc[0]
    bad.loc[bad["department"] == dept, "expected_contacts"] = 0.0
    with pytest.raises(ValueError, match="coverage"):
        validate_allocation_output_df(bad)


def test_coverage_gate_can_be_disabled_for_counterfactuals(baseline_result) -> None:
    bad = baseline_result.allocation.copy()
    dept = bad["department"].iloc[0]
    bad.loc[bad["department"] == dept, "expected_contacts"] = 0.0
    validate_allocation_output_df(bad, enforce_coverage=False)


def test_solver_coverage_floor_is_real_80_pct(baseline_result) -> None:
    """Regression for the silent `* 0.05` bug: the enforced floor must be the
    contract's 80%, measured against the department population proxy."""
    df = baseline_result.allocation
    grouped = df.groupby("department")
    contacts = grouped["expected_contacts"].sum()
    pop_proxy = grouped["reach_cap_population_proxy"].max()
    for dept in contacts.index:
        assert contacts[dept] >= COVERAGE_LOWER_BOUND_PCT * pop_proxy[dept], dept


def test_binding_constraints_populated(baseline_result) -> None:
    """The solver must report which global constraints are binding (the budget
    band is always tight at optimum) and per-row binding caps."""
    assert any(name.startswith("budget_") for name in baseline_result.binding_constraints)
    per_row = baseline_result.allocation["binding_constraint"]
    assert per_row.notna().any()
    allowed = {"reach_cap", "paytv_block", "neg_tier_cap"}
    assert set(per_row.dropna().unique()) <= allowed
