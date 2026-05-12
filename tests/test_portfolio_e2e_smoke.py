"""Cross-module smoke checks (fixtures only; no large data)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from module_b_resource_allocation.models.allocation import build_problem, solve


def test_module_b_baseline_optimal() -> None:
    r = solve(build_problem(solver_seed=20180422))
    assert r.solver_status == "OPTIMAL"
    assert len(r.allocation) > 100


def test_module_c_fixture_csv_readable() -> None:
    p = Path("module_c_forecasting_scenarios/tests/fixtures/polls_raw_fixture.csv")
    assert p.is_file()
    df = pd.read_csv(p)
    assert "preference_proxy_a_pct" in df.columns
    assert len(df) >= 3
