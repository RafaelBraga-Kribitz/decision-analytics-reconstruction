"""Write dual-value CSV artifacts after a successful allocation solve."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from module_b_resource_allocation.models.allocation import AllocationResult


def write_budget_dual_csv(result: AllocationResult, out_dir: Path, scenario_id: str) -> Path:
    """Persist single-row shadow prices for the global budget envelope.

    Args:
        result: Solved allocation containing ``lp_diagnostics`` dual entries.
        out_dir: Directory that will receive ``dual_budget_envelope_<scenario>.csv``.
        scenario_id: Scenario label embedded in the filename and rows.

    Returns:
        Path to the written CSV.

    Raises:
        OSError: If ``out_dir`` cannot be created or the CSV cannot be written.

    Example:
        ``write_budget_dual_csv(result, out_dir, \"baseline\")`` during sensitivity bundles.
    """
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
    """Write the top reach-cap shadow prices returned by CBC.

    Args:
        result: Solved allocation whose diagnostics include ``reach_cap_duals_top5``.
        out_dir: Output directory for ``dual_reach_caps_<scenario>.csv``.
        scenario_id: Scenario label embedded in the filename and rows.

    Returns:
        Path to the written CSV.

    Raises:
        OSError: If ``out_dir`` cannot be created or the CSV cannot be written.

    Example:
        Paired with :func:`write_budget_dual_csv` when ``--sensitivity`` is enabled.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    diag = result.lp_diagnostics or {}
    rows = list(diag.get("reach_cap_duals_top5") or [])
    path = out_dir / f"dual_reach_caps_{scenario_id}.csv"
    pd.DataFrame(rows).assign(scenario_id=scenario_id).to_csv(path, index=False)
    return path
