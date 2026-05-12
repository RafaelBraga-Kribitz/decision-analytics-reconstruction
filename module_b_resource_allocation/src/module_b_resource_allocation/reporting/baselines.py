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
from typing import Any

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


def linear_cap_waterfill_persuasion(problem: _alloc.AllocationProblem) -> tuple[float, float]:
    """Return (persuasion_score, total_usd_spent) for cap-only water-fill on LP slopes.

    Uses the same blended ``contacts_per_unit_eff`` and persuasion weights as
    :func:`module_b_resource_allocation.models.allocation.solve` when constructing
    objective terms, but allocates budget by :func:`_water_fill` only against
    per-cell ``max_spend = audience * unit_cost``.
    """
    layer = problem.fx_layer
    caps_lookup = problem.reach_caps.set_index(["department", "channel"], drop=False)
    caps_list: list[float] = []
    coef_list: list[float] = []

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
                caps_list.append(max_spend)
                coef_list.append(persuasion_per_unit)

    if not caps_list:
        return 0.0, 0.0
    spend = _water_fill(caps_list, problem.budget_usd)
    persuasion = sum(c * s for c, s in zip(coef_list, spend, strict=True))
    return float(persuasion), float(sum(spend))


def cap_waterfill_vs_optimized_ratio(problem: _alloc.AllocationProblem) -> dict[str, Any]:
    """Portfolio helper: water-fill vs MILP optimized totals (numeric transparency)."""
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
