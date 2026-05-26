"""Shared fixtures for Module C tests."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from module_b_resource_allocation.constants import CHANNEL_NAMES, DEPARTMENTS


@pytest.fixture
def fixture_raw_polls_csv() -> Path:
    p = Path(__file__).resolve().parent / "fixtures" / "polls_raw_fixture.csv"
    if not p.exists():
        pytest.skip("polls_raw_fixture.csv not found; run generate-fixtures first")
    return p


@pytest.fixture
def minimal_allocation_parquet(tmp_path: Path) -> Path:
    """Tiny allocation_output-shaped frame for handshake column checks."""
    rows = []
    for d in DEPARTMENTS[:3]:
        for c in CHANNEL_NAMES[:2]:
            for w in range(1, 3):
                rows.append(
                    {
                        "department": d,
                        "channel": c,
                        "week_index": w,
                        "iso_week": f"2018-W{w + 8:02d}",
                        "week_start_date": f"2018-02-{w + 5:02d}",
                        "department_tier": "swing",
                        "region": "ORIENTAL",
                        "budget_allocation_usd": 100.0,
                        "budget_allocation_pyg": 600000.0,
                        "fx_tier": "REF",
                        "tc_rate_pyg_per_usd": 5600.0,
                        "expected_contacts": 50.0,
                        "persuasion_adjusted_contacts": 48.0,
                        "reach_cap_population_proxy": 10000.0,
                        "reach_utilization": 0.01,
                        "binding_constraint": None,
                        "bundle_id": None,
                        "scenario_id": "baseline",
                        "solver_status": "OPTIMAL",
                        "solver_seed": 42,
                        "schema_version_used": "1.0.0",
                    }
                )
    df = pd.DataFrame(rows)
    p = tmp_path / "allocation_minimal.parquet"
    df.to_parquet(p, index=False)
    return p
