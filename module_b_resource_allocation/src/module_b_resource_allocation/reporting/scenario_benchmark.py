"""Scenario comparison table for portfolio benchmarks (no extra MILP theory)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from module_b_resource_allocation.constants import VALID_SCENARIOS
from module_b_resource_allocation.models.allocation import build_problem, solve


def compute_scenario_benchmark_rows(
    *,
    fx_series_id: str,
    solver_seed: int,
    scenario_ids: tuple[str, ...] = ("baseline", "early_lock", "late_flex"),
) -> list[dict[str, object]]:
    """Run one solve per scenario and return comparable summary rows.

    Args:
        fx_series_id: FX calibration series forwarded to each :func:`build_problem` call.
        solver_seed: Shared deterministic seed across scenarios.
        scenario_ids: Iterable of scenario labels (unknown ids are skipped).

    Returns:
        List of dict rows with objective totals and solver metadata.

    Raises:
        None: Invalid scenario ids are skipped quietly.

    Example:
        ``compute_scenario_benchmark_rows(fx_series_id=\"series_b_weekly\", solver_seed=42)``.
    """
    rows: list[dict[str, object]] = []
    for sid in scenario_ids:
        if sid not in VALID_SCENARIOS:
            continue
        problem = build_problem(
            scenario_id=sid,
            fx_series_id=fx_series_id,  # type: ignore[arg-type]  # str passed to build_problem→load_fx_layer(SeriesId Literal); runtime-validated
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


def write_scenario_benchmark_csv(
    path: str | Path,
    *,
    fx_series_id: str,
    solver_seed: int,
    scenario_ids: tuple[str, ...] = ("baseline", "early_lock", "late_flex"),
) -> Path:
    """Write the scenario benchmark table to ``path``.

    Args:
        path: Destination CSV (``str`` or ``Path``).
        fx_series_id: Forwarded to :func:`compute_scenario_benchmark_rows`.
        solver_seed: Forwarded to :func:`compute_scenario_benchmark_rows`.
        scenario_ids: Forwarded to :func:`compute_scenario_benchmark_rows`.

    Returns:
        Resolved ``Path`` after writing.

    Raises:
        OSError: If parent directories cannot be created or the CSV cannot be written.

    Example:
        Call with a path string and keyword overrides, for example
        ``fx_series_id="series_b_weekly"`` and ``solver_seed=1``.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    rows = compute_scenario_benchmark_rows(
        fx_series_id=fx_series_id,
        solver_seed=solver_seed,
        scenario_ids=scenario_ids,
    )
    pd.DataFrame(rows).to_csv(p, index=False)
    return p
