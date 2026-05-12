"""Cap-only water-fill baseline vs optimized MILP (portfolio transparency)."""

from __future__ import annotations

from module_b_resource_allocation.models.allocation import build_problem
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
