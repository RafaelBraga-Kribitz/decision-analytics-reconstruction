"""Cap-only water-fill baseline vs optimized MILP (portfolio transparency)."""

from __future__ import annotations

from module_b_resource_allocation.models.allocation import build_problem, solve
from module_b_resource_allocation.reporting.baselines import (
    cap_waterfill_vs_optimized_ratio,
    linear_cap_waterfill_persuasion,
)


def test_linear_cap_waterfill_spends_near_budget() -> None:
    p = build_problem(solver_seed=42)
    _, spent = linear_cap_waterfill_persuasion(p)
    assert spent > 0.0
    assert spent <= p.budget_usd * 1.01


def test_cap_waterfill_ratio_dict_has_expected_keys() -> None:
    p = build_problem(solver_seed=20180422)
    d = cap_waterfill_vs_optimized_ratio(p)
    assert set(d.keys()) == {
        "waterfill_persuasion_adjusted_contacts",
        "waterfill_total_usd",
        "optimized_persuasion_adjusted_contacts",
        "ratio_waterfill_to_optimized",
    }
    assert d["optimized_persuasion_adjusted_contacts"] > 0.0


def test_optimized_milp_at_least_as_good_as_cap_only_waterfill_heuristic() -> None:
    """MILP optimum should dominate a naive cap-only linear spend (same coefficients).

    The water-fill ignores bundle / coverage MILP structure, so it is not a
    theoretically guaranteed lower bound; empirically on the default fixtures
    the solver objective strictly exceeds the cap-only construction.
    """
    p = build_problem(solver_seed=20180422)
    wf, _ = linear_cap_waterfill_persuasion(p)
    opt = solve(p).total_persuasion_adjusted_contacts
    assert opt >= wf * 0.999
