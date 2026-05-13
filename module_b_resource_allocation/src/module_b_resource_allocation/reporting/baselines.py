"""Cap-only linearized baselines for portfolio benchmarks (relaxation vs full MILP).

The canonical solver (:func:`module_b_resource_allocation.models.allocation.solve`)
maximizes a **piecewise-linearized** persuasion objective under bundle MILP logic.
This module exposes a **cap-only, continuous** relaxation helper: same per-cell
linear persuasion coefficients and per-cell spend ceilings as in ``solve``, but
**without** bundle binaries, coverage coupling, or national budget tolerance
semantics. It is useful for sanity checks and CSV narrative rows — not a lower
bound on the MILP optimum.
"""

from __future__ import annotations

import math

from module_b_resource_allocation.constants import CHANNEL_NAMES, DEPARTMENTS, WEEK_LABELS
from module_b_resource_allocation.models import allocation as _alloc


def _water_fill(caps: list[float], budget: float) -> list[float]:
    """Split ``budget`` across cells, each capped by ``caps[i]``, greedy uniform."""
    n = len(caps)
    if n == 0:
        return []
    x = [0.0] * n
    rem = float(budget)
    alive = set(range(n))
    while rem > 1e-6 and alive:
        per = rem / len(alive)
        slack = min(max(0.0, caps[i] - x[i]) for i in alive)
        take = min(per, slack)
        if take <= 0:
            break
        for i in alive:
            x[i] += take
        rem -= take * len(alive)
        for i in list(alive):
            if x[i] >= caps[i] - 1e-9:
                alive.remove(i)
    return x


def _linear_cell_specs(
    problem: _alloc.AllocationProblem,
) -> list[tuple[str, int, str, float, float]]:
    """Feasible LP cells: (department, week_index, channel, max_spend_usd, linear_coef).

    Uses the same linearized marginal persuasion-per-USD slopes and per-cell spend
    ceilings as :func:`module_b_resource_allocation.models.allocation.solve`, but
    does **not** encode bundle binaries, national coverage coupling, or national
    budget forcing — those are MILP-only.
    """
    layer = problem.fx_layer
    caps_lookup = problem.reach_caps.set_index(["department", "channel"], drop=False)
    rows: list[tuple[str, int, str, float, float]] = []

    for d in DEPARTMENTS:
        for c in CHANNEL_NAMES:
            cap_row = caps_lookup.loc[(d, c)]
            audience = float(cap_row["reachable_audience"])
            tier = str(cap_row["department_tier"])
            attention = float(cap_row["attention_multiplier"])
            salience = float(cap_row["salience_multiplier"])
            hostility = float(cap_row["network_hostility"])
            inflection = float(cap_row["diminishing_returns_inflection_pct"])
            k_dim = float(cap_row["diminishing_returns_k"])
            avg_residual = (1.0 - math.exp(-k_dim * 0.5)) / 0.5
            avg_residual = max(min(avg_residual, 1.0), 0.0)

            for wi, w in enumerate(WEEK_LABELS, start=1):
                uc_usd = _alloc._unit_cost_usd(cap_row, layer, w)
                if uc_usd <= 0:
                    continue
                if c == "tv_spots" and d not in _alloc._PAY_TV_ELIGIBLE:
                    continue
                max_spend = audience * uc_usd
                contacts_per_unit_below = 1.0 / uc_usd
                contacts_per_unit_above = avg_residual / uc_usd
                contacts_per_unit_eff = (
                    inflection * contacts_per_unit_below
                    + (1.0 - inflection) * contacts_per_unit_above
                )
                scenario_w = _alloc._scenario_week_weight(problem.scenario_id, wi)
                tier_w = _alloc._tier_penalty(tier)
                persuasion_per_unit = (
                    contacts_per_unit_eff * attention * salience * hostility * scenario_w * tier_w
                )
                rows.append((d, wi, c, max_spend, persuasion_per_unit))

    return rows


def linear_cap_waterfill_persuasion(problem: _alloc.AllocationProblem) -> tuple[float, float]:
    """Return (persuasion_score, total_usd_spent) for cap-only water-fill on LP slopes.

    Uses the same blended ``contacts_per_unit_eff`` and persuasion weights as
    :func:`module_b_resource_allocation.models.allocation.solve` when constructing
    objective terms, but allocates budget by :func:`_water_fill` only against
    per-cell ``max_spend = audience * unit_cost``.

    Args:
        problem: Frozen allocation inputs describing caps and unit costs.

    Returns:
        Tuple ``(persuasion_score, total_usd_spent)`` for the relaxed water-fill.

    Raises:
        None: This helper does not raise beyond empty ``specs`` (returns zeros).

    Example:
        Called from :func:`build_baseline_comparison_for_run` as the cap-only baseline.
    """
    specs = _linear_cell_specs(problem)
    if not specs:
        return 0.0, 0.0
    caps_list = [s[3] for s in specs]
    coef_list = [s[4] for s in specs]
    spend = _water_fill(caps_list, problem.budget_usd)
    persuasion = sum(c * s for c, s in zip(coef_list, spend, strict=True))
    return float(persuasion), float(sum(spend))


def linear_department_uniform_naive_persuasion(
    problem: _alloc.AllocationProblem,
) -> tuple[float, float]:
    """Operational naive: equal USD budget per geographic unit, then uniform water-fill.

    Splits ``problem.budget_usd`` evenly across :const:`DEPARTMENTS`, then within
    each department runs :func:`_water_fill` across that unit's feasible
    (channel × week) cells at the same per-cell caps as :func:`_linear_cell_specs`.

    This matches the business narrative of geographically undifferentiated budgets
    without solver-driven reallocation. It intentionally **ignores** MILP-only
    feasibility (bundles, coverage floors, pay-TV locks beyond the ineligible
    departments already excluded here).

    Args:
        problem: Frozen allocation inputs describing caps and unit costs.

    Returns:
        Tuple ``(persuasion_score, total_usd_spent)`` for the naive policy.

    Raises:
        None: This helper returns zeros when no feasible specs exist.

    Example:
        Baseline narrative block inside :func:`build_baseline_comparison_for_run`.
    """
    specs = _linear_cell_specs(problem)
    if not specs:
        return 0.0, 0.0

    by_dept: dict[str, list[tuple[float, float]]] = {d: [] for d in DEPARTMENTS}
    for d, _wi, _c, cap, coef in specs:
        by_dept[d].append((cap, coef))

    budget_per_dept = problem.budget_usd / float(len(DEPARTMENTS))
    total_p = 0.0
    total_usd = 0.0
    for d in DEPARTMENTS:
        pairs = by_dept[d]
        if not pairs:
            continue
        caps_u = [p[0] for p in pairs]
        coef_u = [p[1] for p in pairs]
        spend = _water_fill(caps_u, budget_per_dept)
        total_usd += float(sum(spend))
        total_p += float(sum(c * s for c, s in zip(coef_u, spend, strict=True)))

    return float(total_p), float(total_usd)


def linear_persuasion_from_milp_allocation(
    problem: _alloc.AllocationProblem,
    result: _alloc.AllocationResult,
) -> float:
    """Linearized persuasion proxy Σ (coef * USD) evaluated on a MILP allocation.

    Args:
        problem: Problem used to rebuild linearized marginal coefficients.
        result: Solved allocation containing ``budget_allocation_usd`` by cell.

    Returns:
        Scalar linearized persuasion score matching the MILP slopes.

    Raises:
        None: Unknown cells are skipped silently.

    Example:
        ``build_baseline_comparison_for_run`` uses this for apples-to-apples MILP comparisons.
    """
    lut: dict[tuple[str, str, int], float] = {}
    for d, wi, c, _cap, coef in _linear_cell_specs(problem):
        lut[(d, c, wi)] = coef

    total = 0.0
    for _, row in result.allocation.iterrows():
        key = (str(row["department"]), str(row["channel"]), int(row["week_index"]))
        coef = lut.get(key)
        if coef is None:
            continue
        total += coef * float(row["budget_allocation_usd"])
    return float(total)


def build_baseline_comparison_for_run(
    problem: _alloc.AllocationProblem,
    result: _alloc.AllocationResult,
) -> dict[str, object]:
    """Structured baseline rows for manifests and portfolio CFO narratives.

    Args:
        problem: Allocation inputs shared across naive and MILP comparisons.
        result: Solved MILP output used for optimized rows.

    Returns:
        JSON-serializable dict with definitions and numeric comparisons.

    Raises:
        None: Assumes ``problem`` and ``result`` are internally consistent.

    Example:
        Attached to ``run_manifest_<scenario>.json`` by the Module B CLI.
    """

    dept_p, dept_usd = linear_department_uniform_naive_persuasion(problem)
    wf_p, wf_usd = linear_cap_waterfill_persuasion(problem)
    opt_nl = float(result.total_persuasion_adjusted_contacts)
    opt_lin = linear_persuasion_from_milp_allocation(problem, result)
    envelope = problem.budget_usd

    def lift_pct(naive: float, opt: float) -> float:
        if naive <= 0.0:
            return float("nan")
        return (opt - naive) / naive * 100.0

    budget_use_pct = (dept_usd / envelope * 100.0) if envelope > 0 else float("nan")

    return {
        "definitions": {
            "department_uniform_naive": (
                "Equal USD per geographic unit (18 departments); within each unit, "
                "uniform water-fill across feasible channel×week cells at "
                "per-cell caps (reachable audience × unit cost USD). Uses the MILP "
                "linearized marginal persuasion-per-USD slopes; excludes bundle "
                "binaries and coverage coupling present in full solve."
            ),
            "cap_waterfill_relaxation": (
                "Single pooled national water-fill across all feasible cells at the "
                "same caps and slopes — cap-only relaxation, not guaranteed feasible "
                "for the MILP's discrete bundle structure."
            ),
            "milp_optimized_linearized": (
                "Σ (linearized_coef × allocated_USD) on the solved MILP spend vector."
            ),
            "milp_optimized_reported_nonlinear": (
                "Sum of reported persuasion_adjusted_contacts on solver output "
                "(diminishing-returns curve), not identical to MILP LP objective."
            ),
        },
        "department_uniform_naive": {
            "persuasion_proxy_linearized": round(dept_p, 6),
            "total_usd_spent": round(dept_usd, 6),
            "budget_utilization_pct_vs_envelope": round(budget_use_pct, 6),
        },
        "cap_waterfill_relaxation": {
            "persuasion_proxy_linearized": round(wf_p, 6),
            "total_usd_spent": round(wf_usd, 6),
            "budget_utilization_pct_vs_envelope": round(
                (wf_usd / envelope * 100.0) if envelope > 0 else float("nan"), 6
            ),
            "ratio_waterfill_linear_to_milp_nonlinear_proxy": round(
                (wf_p / opt_nl) if opt_nl > 0 else float("nan"), 6
            ),
        },
        "milp_optimized": {
            "persuasion_proxy_linearized": round(opt_lin, 6),
            "persuasion_reported_nonlinear_sum": round(opt_nl, 6),
            "total_budget_usd_allocated": round(result.total_budget_usd, 6),
        },
        "efficiency_vs_department_uniform_naive": {
            "linearized_lift_pct_milp_vs_naive": round(lift_pct(dept_p, opt_lin), 6),
            "naive_budget_left_unspent_usd": round(max(0.0, envelope - dept_usd), 6),
        },
    }


def cap_waterfill_vs_optimized_ratio(problem: _alloc.AllocationProblem) -> dict[str, object]:
    """Portfolio helper: water-fill vs MILP optimized totals (numeric transparency).

    Args:
        problem: Allocation inputs used to re-solve both relaxed and MILP paths.

    Returns:
        Dict summarizing persuasion scores and their ratio.

    Raises:
        RuntimeError: Propagated if the MILP solver
        :func:`~module_b_resource_allocation.models.allocation.solve` fails.

    Example:
        ``cap_waterfill_vs_optimized_ratio(problem)`` in investor-facing QA notebooks.
    """
    wf_p, wf_usd = linear_cap_waterfill_persuasion(problem)
    opt = _alloc.solve(problem)
    opt_p = opt.total_persuasion_adjusted_contacts
    ratio = wf_p / opt_p if opt_p > 0 else float("nan")
    return {
        "waterfill_persuasion_adjusted_contacts": wf_p,
        "waterfill_total_usd": wf_usd,
        "optimized_persuasion_adjusted_contacts": opt_p,
        "ratio_waterfill_to_optimized": ratio,
    }
