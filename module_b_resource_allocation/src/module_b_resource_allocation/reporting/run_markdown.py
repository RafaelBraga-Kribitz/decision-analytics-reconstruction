"""Render a short Markdown run report for portfolio evidence."""

from __future__ import annotations

from module_b_resource_allocation.models.allocation import AllocationResult


def render_allocation_run_markdown(
    result: AllocationResult,
    *,
    scenario_id: str,
    fx_series_id: str,
    routing_scenario: str,
    sensitivity_run: bool,
) -> str:
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
        "## Budget envelope duals (CBC `pi`)",
        "",
        f"- `budget_upper`: {diag.get('budget_upper_pi')}",
        f"- `budget_lower`: {diag.get('budget_lower_pi')}",
        "",
        "## Top reach-cap dual magnitudes",
        "",
    ]
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
