"""Budget envelope sensitivity: re-solve at multiple budget multiples."""

from __future__ import annotations

from typing import Any

from module_b_resource_allocation.constants import CAMPAIGN_BUDGET_USD
from module_b_resource_allocation.models.allocation import build_problem, solve

# Matches module_b_resource_allocation/SPECIFICATION.md §Mandatory sensitivity outputs.
BUDGET_EXPANSION_MULTIPLIERS: tuple[float, ...] = (0.25, 0.5, 0.75, 1.0, 1.5, 2.0)


def compute_budget_expansion_curve(
    *,
    scenario_id: str,
    fx_series_id: str,
    solver_seed: int,
) -> list[dict[str, Any]]:
    """Re-solve the MILP at each budget multiple; return JSON-serializable rows.

    Each row includes CBC/PuLP status codes so callers can filter to optimal runs
    when checking monotonicity of the objective in the campaign budget.
    """
    base = float(CAMPAIGN_BUDGET_USD)
    rows: list[dict[str, Any]] = []
    for m in BUDGET_EXPANSION_MULTIPLIERS:
        problem = build_problem(
            scenario_id=scenario_id,
            fx_series_id=fx_series_id,  # type: ignore[arg-type]
            solver_seed=int(solver_seed),
            budget_usd=base * float(m),
        )
        try:
            result = solve(problem)
        except RuntimeError:
            rows.append(
                {
                    "budget_multiplier": float(m),
                    "budget_target_usd": round(base * float(m), 2),
                    "solver_status": "INFEASIBLE",
                    "pulp_status_code": -1,
                    "pulp_status_label": "INFEASIBLE",
                    "total_budget_usd": 0.0,
                    "total_persuasion_adjusted_contacts": 0.0,
                    "budget_upper_pi": None,
                    "budget_lower_pi": None,
                }
            )
            continue
        diag = result.lp_diagnostics or {}
        rows.append(
            {
                "budget_multiplier": float(m),
                "budget_target_usd": round(base * float(m), 2),
                "solver_status": result.solver_status,
                "pulp_status_code": int(diag.get("pulp_status_code", -99)),
                "pulp_status_label": str(diag.get("pulp_status_label", "")),
                "total_budget_usd": round(result.total_budget_usd, 2),
                "total_persuasion_adjusted_contacts": round(
                    result.total_persuasion_adjusted_contacts, 4
                ),
                "budget_upper_pi": diag.get("budget_upper_pi"),
                "budget_lower_pi": diag.get("budget_lower_pi"),
            }
        )
    return rows
