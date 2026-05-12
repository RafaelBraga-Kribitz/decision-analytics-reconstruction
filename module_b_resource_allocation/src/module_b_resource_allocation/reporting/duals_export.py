"""Write dual-value CSV artifacts after a successful allocation solve."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from module_b_resource_allocation.models.allocation import AllocationResult


def write_budget_dual_csv(result: AllocationResult, out_dir: Path, scenario_id: str) -> Path:
    """Single-row shadow prices on the global budget envelope (upper / lower rows)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    diag = result.lp_diagnostics or {}
    path = out_dir / f"dual_budget_envelope_{scenario_id}.csv"
    df = pd.DataFrame(
        [
            {
                "scenario_id": scenario_id,
                "constraint": "budget_upper",
                "pi": diag.get("budget_upper_pi"),
            },
            {
                "scenario_id": scenario_id,
                "constraint": "budget_lower",
                "pi": diag.get("budget_lower_pi"),
            },
        ]
    )
    df.to_csv(path, index=False)
    return path


def write_reach_cap_duals_csv(result: AllocationResult, out_dir: Path, scenario_id: str) -> Path:
    """Top reach-cap shadow prices (see SPECIFICATION.md sensitivity outputs)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    diag = result.lp_diagnostics or {}
    rows = list(diag.get("reach_cap_duals_top5") or [])
    path = out_dir / f"dual_reach_caps_{scenario_id}.csv"
    pd.DataFrame(rows).assign(scenario_id=scenario_id).to_csv(path, index=False)
    return path
