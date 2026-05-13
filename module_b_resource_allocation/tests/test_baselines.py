"""Cap-only water-fill baseline vs optimized MILP (portfolio transparency)."""

from __future__ import annotations

from module_b_resource_allocation.models.allocation import build_problem, solve
from module_b_resource_allocation.reporting.baselines import (
    build_baseline_comparison_for_run,
    cap_waterfill_vs_optimized_ratio,
    linear_cap_waterfill_persuasion,
    linear_department_uniform_naive_persuasion,
    linear_persuasion_from_milp_allocation,
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


def test_department_uniform_naive_respects_national_envelope() -> None:
    p = build_problem(solver_seed=20180422)
    _, spent = linear_department_uniform_naive_persuasion(p)
    assert spent > 0.0
    assert spent <= p.budget_usd * 1.0001


def test_milp_linear_proxy_weakly_dominates_department_naive_on_baseline() -> None:
    p = build_problem(scenario_id="baseline", solver_seed=20180422)
    naive_p, _ = linear_department_uniform_naive_persuasion(p)
    result = solve(p)
    opt_lin = linear_persuasion_from_milp_allocation(p, result)
    assert opt_lin >= naive_p * 0.999


def test_build_baseline_comparison_for_run_shape() -> None:
    p = build_problem(scenario_id="baseline", solver_seed=20180422)
    result = solve(p)
    payload = build_baseline_comparison_for_run(p, result)
    assert "definitions" in payload
    assert "department_uniform_naive" in payload
    assert "cap_waterfill_relaxation" in payload
    assert "milp_optimized" in payload
    assert "efficiency_vs_department_uniform_naive" in payload
    du = payload["department_uniform_naive"]
    assert "persuasion_proxy_linearized" in du
    assert "total_usd_spent" in du
    eff = payload["efficiency_vs_department_uniform_naive"]
    assert "linearized_lift_pct_milp_vs_naive" in eff
