"""Scenario comparison table for portfolio benchmarks (no extra MILP theory)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from module_b_resource_allocation.constants import VALID_SCENARIOS
from module_b_resource_allocation.models.allocation import build_problem, solve


def compute_scenario_benchmark_rows(
    *,
    fx_series_id: str,
    solver_seed: int,
    scenario_ids: tuple[str, ...] = ("baseline", "early_lock", "late_flex"),
) -> list[dict[str, Any]]:
    """One solve per scenario; return comparable objective and budget rows."""
    rows: list[dict[str, Any]] = []
    for sid in scenario_ids:
        if sid not in VALID_SCENARIOS:
            continue
        problem = build_problem(
            scenario_id=sid,
            fx_series_id=fx_series_id,  # type: ignore[arg-type]
            solver_seed=solver_seed,
        )
        result = solve(problem)
        diag = result.lp_diagnostics or {}
        rows.append(
            {
                "scenario_id": sid,
                "solver_status": result.solver_status,
                "pulp_status_code": int(diag.get("pulp_status_code", -1)),
                "total_budget_usd": round(result.total_budget_usd, 2),
                "total_persuasion_adjusted_contacts": round(
                    result.total_persuasion_adjusted_contacts, 4
                ),
            }
        )
    return rows


def write_scenario_benchmark_csv(path: str | Path, **kwargs: Any) -> Path:
    """Write CSV; path may be str or Path."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    rows = compute_scenario_benchmark_rows(**kwargs)
    pd.DataFrame(rows).to_csv(p, index=False)
    return p
