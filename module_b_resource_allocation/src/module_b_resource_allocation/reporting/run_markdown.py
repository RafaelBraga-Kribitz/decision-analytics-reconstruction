"""Render a short Markdown run report for portfolio evidence."""

from __future__ import annotations

from typing import Any

from module_b_resource_allocation.models.allocation import AllocationResult


def render_allocation_run_markdown(
    result: AllocationResult,
    *,
    scenario_id: str,
    fx_series_id: str,
    routing_scenario: str,
    sensitivity_run: bool,
    baseline_comparison: dict[str, Any] | None = None,
) -> str:
    """Render a Markdown evidence bundle for a single allocation solve.

    Args:
        result: Solved allocation including diagnostics used in tables.
        scenario_id: Scenario label for the title block.
        fx_series_id: FX series label displayed in the header table.
        routing_scenario: Routing scenario label for context.
        sensitivity_run: Whether dual/sensitivity artifacts were collected.
        baseline_comparison: Optional payload from :func:`build_baseline_comparison_for_run`.

    Returns:
        Multi-line Markdown string suitable for version control or email.

    Raises:
        None: Assumes ``result`` fields referenced in the template exist.

    Example:
        Written beside CSV artifacts when operators request narrative output.
    """
    diag = result.lp_diagnostics or {}
    dual5 = diag.get("reach_cap_duals_top5") or []
    lines = [
        f"# Module B allocation run — `{scenario_id}`",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| FX series | `{fx_series_id}` |",
        f"| Routing scenario | `{routing_scenario}` |",
        f"| Solver status | `{result.solver_status}` |",
        f"| CBC status code | `{diag.get('pulp_status_code', '')}` |",
        f"| Total spend USD | {result.total_budget_usd:,.2f} |",
        f"| Persuasion-adjusted contacts | {result.total_persuasion_adjusted_contacts:,.2f} |",
        f"| Sensitivity bundle | `{'yes' if sensitivity_run else 'no'}` |",
        "",
    ]
    if baseline_comparison:
        eff = baseline_comparison.get("efficiency_vs_department_uniform_naive") or {}
        naive = baseline_comparison.get("department_uniform_naive") or {}
        milp = baseline_comparison.get("milp_optimized") or {}
        lines.extend(
            [
                "## Baseline comparison (business framing)",
                "",
                "| Baseline | Linearized persuasion proxy | Spend USD |",
                "|----------|----------------------------:|----------:|",
                f"| Department-uniform naive | {naive.get('persuasion_proxy_linearized', '')} | "
                f"{naive.get('total_usd_spent', '')} |",
                f"| MILP (this run) | {milp.get('persuasion_proxy_linearized', '')} | "
                f"{milp.get('total_budget_usd_allocated', '')} |",
                "",
                f"- Linearized lift vs department-uniform naive (%): "
                f"`{eff.get('linearized_lift_pct_milp_vs_naive', '')}`",
                f"- Unspent under naive (USD): `{eff.get('naive_budget_left_unspent_usd', '')}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Budget envelope duals (CBC `pi`)",
            "",
            f"- `budget_upper`: {diag.get('budget_upper_pi')}",
            f"- `budget_lower`: {diag.get('budget_lower_pi')}",
            "",
            "## Top reach-cap dual magnitudes",
            "",
        ]
    )
    if not dual5:
        lines.append("_No cap duals returned (solver may omit shadow prices)._")
    else:
        lines.append("| Constraint | pi |")
        lines.append("|------------|-----|")
        for row in dual5:
            lines.append(f"| `{row.get('constraint','')}` | {row.get('pi')} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "_Reconstruction artifact: numbers trace to `solve` in "
        "`module_b_resource_allocation.models.allocation`._"
    )
    return "\n".join(lines)
