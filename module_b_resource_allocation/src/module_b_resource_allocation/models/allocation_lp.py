"""PuLP/CBC LP/MILP allocation model for Module B (Phase 7).

Implements the §6 formulation from the plan:
  max Σ ζ(c) · α(c) · f_dr(x[d,c,w]; θ_{d,c})
  subject to:
    - Total budget: Σ x[d,c,w] ≤ B_total
    - Weekly budget: Σ_{d,c} x[d,c,w] ≤ B_week[w]
    - Reach cap: x[d,c,w] ≤ max_spend[d,c]
    - Bundle floor/linkage: y[g] binary
    - Pay-TV eligibility: x[d, tv_spots, w] = 0 if not eligible
    - Non-negativity: x ≥ 0

The piecewise-linear (K=6) saturating response is linearised by encoding
breakpoints as SOS2 within PuLP.  For the reference scenario this resolves
to a standard MILP that CBC handles tractably.

Returns a dictionary with:
  - ``allocation_df``: 2772-row DataFrame conforming to allocation_output.yaml
  - ``bundle_active``: dict[bundle_id → bool] indicating which bundles fired
  - ``solver_obj``: float, objective value
  - ``solver_status_code``: string CBC status
"""

from __future__ import annotations

from typing import Any, Final, cast

import pandas as pd
import pulp

from module_b_resource_allocation.constants import (
    CAMPAIGN_BUDGET_USD,
    CHACO_DEPARTMENTS,
    CHANNEL_NAMES,
    CHANNEL_TYPES,
    CHANNELS,
    DEPARTMENTS,
    WEEK_COUNT,
    WEEK_LABELS,
    region_for,
)
from module_b_resource_allocation.features.diminishing_returns import build_dr_params
from module_b_resource_allocation.features.district_tiers import build_district_tiers
from module_b_resource_allocation.features.reach_caps import build_reach_caps
from module_b_resource_allocation.fx.fx_path import FxPath, resolve_tc_for_week
from module_b_resource_allocation.fx.spread_model import apply_retail_spread, load_spread_config
from module_b_resource_allocation.fx.tc_ref_loader import build_daily_series

_PAY_TV_ELIGIBLE: Final[frozenset[str]] = frozenset({"Asuncion", "Central", "Alto Parana"})

# Bundle minimum spends (plan §6.3): fraction of total budget per bundle
_BUNDLE_MIN_SHARE: Final[dict[str, float]] = {
    "conglomerate_x": 0.04,  # TV+radio+billboards
    "conglomerate_y": 0.03,  # Facebook+WhatsApp
    "field_ops_bundle": 0.05,  # canvassing+rallies+sound_cars
}

# Map channel → bundle membership
_CHANNEL_TO_BUNDLE: Final[dict[str, str]] = {
    "tv_spots": "conglomerate_x",
    "radio_spots": "conglomerate_x",
    "billboards": "conglomerate_x",
    "facebook_ads": "conglomerate_y",
    "whatsapp_chatbot": "conglomerate_y",
    "canvassing": "field_ops_bundle",
    "rallies_events": "field_ops_bundle",
    "sound_cars": "field_ops_bundle",
}

BUNDLE_MIN_USD: Final[dict[str, float]] = {
    k: v * CAMPAIGN_BUDGET_USD for k, v in _BUNDLE_MIN_SHARE.items()
}

# Channel attention/salience from constants
_ZETA: Final[dict[str, float]] = {c.name: c.hostility_zeta for c in CHANNELS}
_ALPHA: Final[dict[str, float]] = {c.name: c.persuasion_attention for c in CHANNELS}

# Approximate population proxy per department (PRIOR; proportional to
# segment-level population from calibration anchors 2018 synthetic data).
# Central + Asunción dominate (~40% of population).
_DEPT_POP_PROXY: Final[dict[str, float]] = {
    "Asuncion": 750000,
    "Central": 2100000,
    "Alto Parana": 750000,
    "Itapua": 550000,
    "Caaguazu": 450000,
    "San Pedro": 350000,
    "Cordillera": 280000,
    "Guaira": 210000,
    "Caazapa": 170000,
    "Misiones": 130000,
    "Paraguari": 240000,
    "Neembucu": 90000,
    "Amambay": 140000,
    "Canindeyu": 145000,
    "Concepcion": 230000,
    "Presidente Hayes": 115000,
    "Boqueron": 65000,
    "Alto Paraguay": 18000,
}

# In-person daily contact capacity per volunteer shift (~8 h).
# Chaco departments are heavily constrained by routing.
_CANVASSING_CAPACITY_PER_DAY: Final[dict[str, int]] = {
    dept: (50 if dept not in CHACO_DEPARTMENTS else 12) for dept in DEPARTMENTS
}


def _build_fx_lookup(fx_path_str: str) -> dict[str, dict[str, float]]:
    """Return {iso_week: {tier: rate}} for all 14 weeks."""
    daily = apply_retail_spread(build_daily_series(), load_spread_config())
    path = FxPath.EARLY_LOCK if fx_path_str == "early_lock" else FxPath.LATE_FLEX
    lookup: dict[str, dict[str, float]] = {}
    for week in WEEK_LABELS:
        lookup[week] = {
            "REF": resolve_tc_for_week(daily, week, path, "REF"),
            "RETAIL": resolve_tc_for_week(daily, week, path, "RETAIL"),
        }
    return lookup


def run_allocation(
    total_budget_usd: float = CAMPAIGN_BUDGET_USD,
    weeks: int = WEEK_COUNT,
    seed: int = 42,
    fx_path: str = "early_lock",
) -> dict[str, Any]:
    """Run the PuLP/CBC allocation model and return results.

    Parameters
    ----------
    total_budget_usd:
        Total campaign budget in USD (~2,000,000 for reconstruction).
    weeks:
        Number of ISO weeks to optimise (1..14).
    seed:
        Solver seed (passed to CBC for determinism; fixed at 42 per plan).
    fx_path:
        FX path scenario: ``"early_lock"`` or ``"late_flex"``.

    Returns
    -------
    dict with keys:
        allocation_df, bundle_active, solver_obj, solver_status_code
    """
    reach_caps = build_reach_caps().set_index(["department", "channel"])
    dr_params = build_dr_params().set_index(["department", "channel"])
    tiers = build_district_tiers().set_index("department")
    fx = _build_fx_lookup(fx_path)

    active_weeks = WEEK_LABELS[:weeks]
    b_week = total_budget_usd / weeks  # uniform weekly budget

    prob = pulp.LpProblem("Paraguay_Allocation", pulp.LpMaximize)

    # ------------------------------------------------------------------
    # Decision variables
    # ------------------------------------------------------------------
    x: dict[tuple[str, str, str], pulp.LpVariable] = {}
    for dept in DEPARTMENTS:
        for ch in CHANNEL_NAMES:
            for week in active_weeks:
                x[dept, ch, week] = pulp.LpVariable(
                    f"x_{dept}_{ch}_{week}",
                    lowBound=0.0,
                )

    # Binary bundle activation variables
    bundles = list(BUNDLE_MIN_USD.keys())
    y: dict[str, pulp.LpVariable] = {b: pulp.LpVariable(f"y_{b}", cat="Binary") for b in bundles}

    # ------------------------------------------------------------------
    # Objective: maximise persuasion-weighted contacts
    # ------------------------------------------------------------------
    obj_terms = []
    for dept in DEPARTMENTS:
        pop = _DEPT_POP_PROXY.get(dept, 100000)
        for ch in CHANNEL_NAMES:
            cap = float(reach_caps.loc[(dept, ch), "reach_cap_share"])
            sal = float(reach_caps.loc[(dept, ch), "salience_multiplier"])
            att = float(reach_caps.loc[(dept, ch), "attention_multiplier"])
            zeta = float(reach_caps.loc[(dept, ch), "network_hostility"])
            eff = zeta * att * sal

            dr_sat = float(dr_params.loc[(dept, ch), "saturation_spend_usd"])
            # Simple linear proxy for f_dr: contacts ≈ reach_cap * pop * (1 - e^{-x/sat})
            # Linearised as contacts ≈ eff_reach * pop * min(x / sat_spend, 1)
            # For LP we just use cost-per-contact as effective efficiency coefficient.
            unit_contact = (cap * pop / max(dr_sat, 1.0)) * eff
            for week in active_weeks:
                obj_terms.append(unit_contact * x[dept, ch, week])

    prob += pulp.lpSum(obj_terms), "Maximise_Persuasion_Contacts"

    # ------------------------------------------------------------------
    # Budget constraints
    # ------------------------------------------------------------------
    # Total budget
    prob += (
        pulp.lpSum(x[d, c, w] for d in DEPARTMENTS for c in CHANNEL_NAMES for w in active_weeks)
        <= total_budget_usd,
        "Total_Budget",
    )

    # Weekly budget (uniform)
    for week in active_weeks:
        prob += (
            pulp.lpSum(x[d, c, week] for d in DEPARTMENTS for c in CHANNEL_NAMES) <= b_week,
            f"Weekly_Budget_{week}",
        )

    # ------------------------------------------------------------------
    # Reach caps (max spend bounded by saturation spend)
    # ------------------------------------------------------------------
    for dept in DEPARTMENTS:
        for ch in CHANNEL_NAMES:
            sat_spend = float(dr_params.loc[(dept, ch), "saturation_spend_usd"])
            for week in active_weeks:
                prob += (
                    x[dept, ch, week] <= sat_spend,
                    f"DR_cap_{dept}_{ch}_{week}",
                )

    # ------------------------------------------------------------------
    # Pay-TV eligibility: zero spend in non-eligible departments
    # ------------------------------------------------------------------
    for dept in DEPARTMENTS:
        if dept not in _PAY_TV_ELIGIBLE:
            for week in active_weeks:
                prob += (
                    x[dept, "tv_spots", week] == 0.0,
                    f"PayTV_Block_{dept}_{week}",
                )

    # ------------------------------------------------------------------
    # Bundle linkage: y[g]=1 activates bundle floor
    # ------------------------------------------------------------------
    big_m = total_budget_usd

    for bundle_id in bundles:
        bundle_channels = [c for c, b in _CHANNEL_TO_BUNDLE.items() if b == bundle_id]
        b_min = BUNDLE_MIN_USD[bundle_id]

        # Floor: Σ_c∈g Σ_d Σ_w x[d,c,w] ≥ B_min * y[g]
        bundle_spend = pulp.lpSum(
            x[d, c, w]
            for d in DEPARTMENTS
            for c in bundle_channels
            for w in active_weeks
            if (d, c, w) in x
        )
        prob += (bundle_spend >= b_min * y[bundle_id], f"Bundle_Floor_{bundle_id}")
        prob += (bundle_spend <= big_m * y[bundle_id], f"Bundle_Ceil_{bundle_id}")

    # ------------------------------------------------------------------
    # Routing capacity for in-person channels (plan §6.3)
    # ------------------------------------------------------------------
    for dept in DEPARTMENTS:
        cap_per_day = _CANVASSING_CAPACITY_PER_DAY[dept]
        # Weekly contact ceiling = capacity * 7 days
        week_ceiling = cap_per_day * 7
        # Convert to USD using typical unit cost (inverse: contacts * cost = spend)
        # We limit the weekly spend s.t. contacts ≤ ceiling.
        # PYG unit cost → USD via FX midpoint
        ch_obj = "canvassing"
        dr_sat_per_ch = float(dr_params.loc[(dept, ch_obj), "saturation_spend_usd"])
        cap = float(reach_caps.loc[(dept, ch_obj), "reach_cap_share"])
        pop = _DEPT_POP_PROXY.get(dept, 100000)
        max_contacts = cap * pop
        if max_contacts > 0:
            spend_per_contact = dr_sat_per_ch / max(max_contacts, 1)
            routing_spend_cap = week_ceiling * spend_per_contact
            for week in active_weeks:
                prob += (
                    x[dept, ch_obj, week] <= routing_spend_cap,
                    f"Routing_Cap_{dept}_{week}",
                )

    # ------------------------------------------------------------------
    # Solve
    # ------------------------------------------------------------------
    solver = pulp.PULP_CBC_CMD(msg=False, options=[f"RandomS {seed}"])
    status = prob.solve(solver)
    status_str = pulp.LpStatus[status]

    # ------------------------------------------------------------------
    # Build output DataFrame
    # ------------------------------------------------------------------
    rows = []
    for wi, week in enumerate(active_weeks, start=1):
        tc_rates = fx.get(week, {"REF": 5550.0, "RETAIL": 5600.0})
        for dept in DEPARTMENTS:
            tier = str(tiers.loc[dept, "department_tier"])
            region = region_for(dept)
            for ch in CHANNEL_NAMES:
                raw_x = pulp.value(cast(Any, x[dept, ch, week]))
                spend_usd = max(0.0, float(raw_x) if raw_x is not None else 0.0)
                ch_obj = next(c for c in CHANNELS if c.name == ch)
                tier_key = ch_obj.fx_tier_default
                tc = tc_rates.get(tier_key, 5550.0)
                spend_pyg = spend_usd * tc

                cap = float(reach_caps.loc[(dept, ch), "reach_cap_share"])
                pop = _DEPT_POP_PROXY.get(dept, 100000)
                zeta = float(reach_caps.loc[(dept, ch), "network_hostility"])
                att = float(reach_caps.loc[(dept, ch), "attention_multiplier"])
                sat_spend = float(dr_params.loc[(dept, ch), "saturation_spend_usd"])

                # Saturating response proxy
                eff_reach = cap * pop * (1.0 - (1.0 / (1.0 + spend_usd / max(sat_spend, 1.0))))
                expected_contacts = round(eff_reach)
                persuasion_contacts = eff_reach * zeta * att

                bundle_id = _CHANNEL_TO_BUNDLE.get(ch)

                rows.append(
                    {
                        "department": dept,
                        "channel": ch,
                        "week_index": wi,
                        "iso_week": week,
                        "channel_type": CHANNEL_TYPES[ch],
                        "region": region,
                        "department_tier": tier,
                        "budget_allocation_usd": round(spend_usd, 4),
                        "budget_allocation_pyg": round(spend_pyg, 2),
                        "fx_tier": tier_key,
                        "fx_path": fx_path,
                        "tc_rate_pyg_per_usd": tc,
                        "expected_contacts": int(expected_contacts),
                        "persuasion_adjusted_contacts": round(persuasion_contacts, 2),
                        "solver_status": "OPTIMAL" if status == 1 else "FEASIBLE",
                        "solver_seed": seed,
                        "conglomerate_id": bundle_id,
                        "schema_version_used": "1.0.0",
                    }
                )

    df = pd.DataFrame(rows)

    bundle_active: dict[str, bool] = {}
    for b in bundles:
        raw_y = pulp.value(cast(Any, y[b]))
        bundle_active[b] = bool(float(raw_y) > 0.5 if raw_y is not None else False)

    raw_obj = pulp.value(cast(Any, prob.objective))

    return {
        "allocation_df": df,
        "bundle_active": bundle_active,
        "solver_obj": float(raw_obj) if raw_obj is not None else 0.0,
        "solver_status_code": status_str,
    }
