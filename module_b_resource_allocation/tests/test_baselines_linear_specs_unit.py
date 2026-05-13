"""Unit tests for ``reporting.baselines._linear_cell_specs``."""

from __future__ import annotations

from module_b_resource_allocation.models.allocation import build_problem
from module_b_resource_allocation.reporting.baselines import _linear_cell_specs


def test_linear_cell_specs_nonempty_matches_solver_inputs() -> None:
    problem = build_problem()
    specs = _linear_cell_specs(problem)
    assert len(specs) >= 1
    dept, week_idx, channel, max_spend, coef = specs[0]
    assert isinstance(dept, str)
    assert isinstance(week_idx, int) and week_idx >= 1
    assert isinstance(channel, str)
    assert max_spend >= 0.0
    assert coef >= 0.0
