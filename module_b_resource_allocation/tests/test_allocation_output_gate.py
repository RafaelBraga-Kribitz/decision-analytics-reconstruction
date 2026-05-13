"""Tests for post-solve allocation_output contract gate."""

from __future__ import annotations

import pytest
from module_b_resource_allocation.models.allocation import build_problem, solve
from module_b_resource_allocation.utils.allocation_output_gate import (
    validate_allocation_output_df,
)


def test_validate_passes_on_canonical_solve() -> None:
    r = solve(build_problem(scenario_id="baseline", solver_seed=20180422))
    validate_allocation_output_df(r.allocation)


def test_validate_rejects_wrong_row_count() -> None:
    r = solve(build_problem(scenario_id="baseline", solver_seed=20180422))
    bad = r.allocation.head(10)
    with pytest.raises(ValueError, match="row_count"):
        validate_allocation_output_df(bad)
