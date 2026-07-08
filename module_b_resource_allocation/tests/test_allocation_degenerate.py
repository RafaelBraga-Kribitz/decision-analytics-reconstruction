"""Degenerate-input coverage for the Module B MILP solver (IMP-B03).

These tests exercise the failure/edge paths that ``test_allocation.py``'s
baseline fixture never reaches: a zero-budget envelope that the per-department
coverage floor (``COVERAGE_LOWER_BOUND_PCT``) guarantees is infeasible, an
empty ``reach_caps`` frame that would otherwise crash with an opaque
``KeyError``, and a single all-zero-audience (department, channel) cell that
must contribute nothing without breaking the department's coverage
constraint.
"""

from __future__ import annotations

import pandas as pd
import pytest
from module_b_resource_allocation.models.allocation import (
    EmptyReachCapsError,
    build_problem,
    solve,
)
from module_b_resource_allocation.models.feature_join import build_allocation_features


def test_degenerate_zero_budget_is_infeasible() -> None:
    """A zero-USD envelope can never clear the 80% coverage floor per department."""
    problem = build_problem(budget_usd=0.0, budget_tolerance=0.0, solver_seed=1)
    with pytest.raises(RuntimeError, match="Infeasible"):
        solve(problem)


def test_degenerate_empty_reach_caps_raises_named_exception() -> None:
    """An empty reach_caps frame must fail with a specific, documented exception.

    Not a bare ``KeyError`` surfaced from deep inside decision-variable
    construction.
    """
    empty = build_allocation_features().iloc[0:0]
    problem = build_problem(reach_caps=empty, solver_seed=1)
    with pytest.raises(EmptyReachCapsError):
        solve(problem)


def test_degenerate_all_zero_audience_cell_contributes_nothing_and_stays_feasible() -> None:
    """Zeroing one (department, channel) cell's audience must not crash the
    solve, must yield zero spend/contacts for that cell, and must not by
    itself make the department's coverage constraint infeasible so long as
    other channels in that department can cover it.
    """
    caps = build_allocation_features().copy()
    mask = (caps["department"] == "Asuncion") & (caps["channel"] == "whatsapp_chatbot")
    assert mask.any(), "fixture assumption: Asuncion/whatsapp_chatbot row must exist"
    caps.loc[mask, "reachable_audience"] = 0
    caps.loc[mask, "reach_cap_share"] = 0.0

    problem = build_problem(reach_caps=caps, solver_seed=1)
    result = solve(problem)

    assert result.solver_status in {"OPTIMAL", "FEASIBLE"}

    zeroed = result.allocation[
        (result.allocation["department"] == "Asuncion")
        & (result.allocation["channel"] == "whatsapp_chatbot")
    ]
    assert not zeroed.empty
    assert (zeroed["budget_allocation_usd"] == 0).all()
    assert (zeroed["expected_contacts"] == 0).all()

    # The department-wide coverage floor is not itself broken by the zeroed
    # cell: it does not appear as an infeasible/binding failure surfaced via
    # a RuntimeError (solve() would have raised above), and other channels
    # still contribute non-zero contacts to Asuncion.
    dept_rows = result.allocation[result.allocation["department"] == "Asuncion"]
    assert dept_rows["expected_contacts"].sum() > 0


def test_degenerate_empty_reach_caps_message_is_specific() -> None:
    """The exception message names the offending field, not a bare KeyError repr."""
    empty = pd.DataFrame(columns=build_allocation_features().columns)
    problem = build_problem(reach_caps=empty, solver_seed=1)
    with pytest.raises(EmptyReachCapsError, match="reach_caps"):
        solve(problem)
