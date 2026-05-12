"""Benchmark rows: scenario timing variants on the same envelope."""

from __future__ import annotations

from pathlib import Path

from module_b_resource_allocation.reporting.scenario_benchmark import (
    compute_scenario_benchmark_rows,
    write_scenario_benchmark_csv,
)


def test_scenario_benchmark_has_three_rows() -> None:
    rows = compute_scenario_benchmark_rows(
        fx_series_id="series_b_weekly",
        solver_seed=42,
    )
    assert len(rows) == 3
    ids = {r["scenario_id"] for r in rows}
    assert ids == {"baseline", "early_lock", "late_flex"}
    for r in rows:
        assert r["solver_status"] == "OPTIMAL"
        assert float(r["total_persuasion_adjusted_contacts"]) > 0


def test_write_scenario_benchmark_csv(tmp_path: Path) -> None:
    p = tmp_path / "bench.csv"
    out = write_scenario_benchmark_csv(p, fx_series_id="series_b_weekly", solver_seed=1)
    assert out.exists()
    assert "baseline" in out.read_text(encoding="utf-8")
