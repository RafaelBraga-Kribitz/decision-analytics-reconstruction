"""Tests for dual CSV export."""

from __future__ import annotations

from pathlib import Path

from module_b_resource_allocation.models.allocation import build_problem, solve
from module_b_resource_allocation.reporting.duals_export import (
    write_budget_dual_csv,
    write_reach_cap_duals_csv,
)


def test_write_budget_dual_csv_roundtrip(tmp_path: Path) -> None:
    problem = build_problem(
        scenario_id="baseline",
        fx_series_id="series_b_weekly",
        solver_seed=20180422,
    )
    result = solve(problem)
    path = write_budget_dual_csv(result, tmp_path, "baseline")
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "budget_upper" in text
    assert "budget_lower" in text


def test_reach_cap_duals_csv_has_top5_or_empty(tmp_path: Path) -> None:
    problem = build_problem(
        scenario_id="baseline",
        fx_series_id="series_b_weekly",
        solver_seed=20180422,
    )
    result = solve(problem)
    path = write_reach_cap_duals_csv(result, tmp_path, "baseline")
    assert path.exists()
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 1
