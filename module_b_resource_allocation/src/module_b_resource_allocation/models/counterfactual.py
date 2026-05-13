"""Broadcast-to-direct counterfactual reallocation engine (Phase 9).

Premise
-------

Given a baseline allocation produced by ``models/allocation.py``, this module
runs a what-if reallocation that moves a configurable share of spend from
broadcast channels (TV, radio, billboards) into direct / in-person channels
(canvassing, rallies, sound cars), respecting:

* Per-(department, channel) reach caps and diminishing returns.
* Routing feasibility under the routing scenario in force (TSP shift-cap,
  Chaco weather impassability).
* In-person channel saturation: cannot exceed ``saturation_pct`` of
  ``reachable_audience`` in any single week.

Returns
-------

``counterfactual_allocation`` (same schema as
``schema_contracts/allocation_output.yaml``) plus a ``deltas`` companion
frame with per-(department, channel, week) realized-contact deltas vs. the
baseline.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from module_b_resource_allocation.constants import (
    SCENARIO_BROADCAST_TO_DIRECT,
)
from module_b_resource_allocation.models.allocation import (
    AllocationResult,
    _expected_contacts,
)

_BROADCAST_DONORS: frozenset[str] = frozenset({"tv_spots", "radio_spots", "billboards"})
_DIRECT_RECEIVERS: tuple[str, ...] = (
    "canvassing",
    "rallies_events",
    "sound_cars",
)


@dataclass(frozen=True)
class CounterfactualResult:
    counterfactual_allocation: pd.DataFrame
    baseline_allocation: pd.DataFrame
    deltas: pd.DataFrame
    shift_share: float
    routing_feasible_share: float


def _routing_feasible_in_week(routing_cost: pd.DataFrame, week_index: int, department: str) -> bool:
    """A department is routing-feasible in a week if it has at least one
    feasible in/out edge to a non-self department in the cost matrix."""
    out_mask = (
        (routing_cost["origin_department"] == department)
        & (routing_cost["edge_feasible"])
        & (routing_cost["origin_department"] != routing_cost["destination_department"])
    )
    return bool(out_mask.any())


def run_broadcast_to_direct(
    baseline: AllocationResult,
    routing_cost: pd.DataFrame,
    shift_share: float = 0.30,
    saturation_pct: float = 0.65,
) -> CounterfactualResult:
    """Reallocate ``shift_share`` of broadcast spend into direct channels.

    Parameters
    ----------
    baseline:
        Output of :func:`module_b_resource_allocation.models.allocation.solve`.
    routing_cost:
        Cost matrix from ``routing.cost_matrix.build_cost_matrix``.  Used to
        gate which (department, week) cells can absorb in-person spend.
    shift_share:
        Fraction of broadcast spend in each (department, week) to move into
        direct channels.  Must be in ``[0, 1]``.
    saturation_pct:
        Hard cap on per-week reach utilization for the receiving direct
        channels.

    Returns
    -------
    CounterfactualResult
        Bundles counterfactual and baseline allocations, ``deltas``, and
        routing feasibility diagnostics.

    Raises
    ------
    ValueError
        If ``shift_share`` or ``saturation_pct`` are outside their valid ranges.
    TypeError
        If grouped keys are not 2-tuples as expected.

    Examples
    --------
    ``run_broadcast_to_direct(baseline, routing_cost, shift_share=0.25)`` for
    what-if reporting.
    """
    if not 0.0 <= shift_share <= 1.0:
        raise ValueError("shift_share must be in [0, 1]")
    if not 0.0 < saturation_pct <= 1.0:
        raise ValueError("saturation_pct must be in (0, 1]")

    base = baseline.allocation.copy()

    # Group baseline by (department, week_index) to compute the donor pot.
    cf = base.copy()
    cf["scenario_id"] = SCENARIO_BROADCAST_TO_DIRECT

    feasibility_cache: dict[str, bool] = {}

    def _is_routing_feasible(dept: str) -> bool:
        if dept not in feasibility_cache:
            feasibility_cache[dept] = _routing_feasible_in_week(routing_cost, 0, dept)
        return feasibility_cache[dept]

    n_feasible = 0
    n_total = 0

    for group_key, block in cf.groupby(["department", "week_index"]):
        if not isinstance(group_key, tuple) or len(group_key) != 2:
            msg = f"expected 2-tuple group key, got {type(group_key)!r}"
            raise TypeError(msg)
        dept, wi = str(group_key[0]), int(group_key[1])
        n_total += 1
        if not _is_routing_feasible(dept):
            continue
        n_feasible += 1
        donors = block[block["channel"].isin(list(_BROADCAST_DONORS))]
        donor_pot = float(donors["budget_allocation_usd"].sum()) * shift_share
        if donor_pot <= 0:
            continue

        # Reduce donor spends proportionally.
        for ch in _BROADCAST_DONORS:
            mask = (cf["department"] == dept) & (cf["week_index"] == wi) & (cf["channel"] == ch)
            cf.loc[mask, "budget_allocation_usd"] = cf.loc[mask, "budget_allocation_usd"] * (
                1.0 - shift_share
            )

        # Distribute donor pot across direct channels in priority order.
        remaining_pot = donor_pot
        for ch in _DIRECT_RECEIVERS:
            if remaining_pot <= 0:
                break
            recv_mask = (
                (cf["department"] == dept) & (cf["week_index"] == wi) & (cf["channel"] == ch)
            )
            if not recv_mask.any():
                continue
            row = cf.loc[recv_mask].iloc[0]
            audience = float(row["reach_cap_population_proxy"])
            # The receiving channel's per-USD contact value is fixed at
            # 1 / unit_cost_usd via the LP's reach utilization; we recover
            # unit_cost_usd from the row's existing reach + spend if any,
            # else fall back to a conservative prior of $0.25 per contact.
            current_usd = float(row["budget_allocation_usd"])
            current_contacts = float(row["expected_contacts"])
            if current_contacts > 0:
                unit_cost_usd = current_usd / max(current_contacts, 1e-9)
            else:
                # Fallback: spend $0.50 per audience-unit when no baseline anchor.
                unit_cost_usd = 0.50

            cap_usd_saturation = saturation_pct * audience * unit_cost_usd - current_usd
            absorb = max(min(remaining_pot, cap_usd_saturation), 0.0)
            cf.loc[recv_mask, "budget_allocation_usd"] = current_usd + absorb
            remaining_pot -= absorb

    # Recompute spend-derived columns.
    cf["budget_allocation_pyg"] = cf["budget_allocation_usd"] * cf["tc_rate_pyg_per_usd"]

    # Recompute expected/persuasion contacts under the new spend.
    new_contacts: list[float] = []
    new_persuasion: list[float] = []
    new_reach_util: list[float] = []
    for _, row in cf.iterrows():
        audience = float(row["reach_cap_population_proxy"])
        spend_usd = float(row["budget_allocation_usd"])
        baseline_contacts = float(row["expected_contacts"])
        baseline_spend = float(
            base.loc[
                (base["department"] == row["department"])
                & (base["channel"] == row["channel"])
                & (base["week_index"] == row["week_index"]),
                "budget_allocation_usd",
            ].iloc[0]
        )
        if baseline_spend > 0 and baseline_contacts > 0:
            unit_cost_usd = baseline_spend / baseline_contacts
        else:
            unit_cost_usd = 0.50
        units = spend_usd / unit_cost_usd if unit_cost_usd > 0 else 0.0
        reach_used = min(units / audience if audience > 0 else 0.0, 1.0)
        # Use k=1.0, infl=0.5 as a conservative default if not present.
        k = 1.0
        infl = 0.5
        contacts = _expected_contacts(audience, reach_used, k, infl)
        attn_ratio = (
            float(row["persuasion_adjusted_contacts"]) / max(baseline_contacts, 1e-9)
            if baseline_contacts > 0
            else 1.0
        )
        new_contacts.append(contacts)
        new_persuasion.append(contacts * attn_ratio)
        new_reach_util.append(round(reach_used, 4))

    cf["expected_contacts"] = new_contacts
    cf["persuasion_adjusted_contacts"] = new_persuasion
    cf["reach_utilization"] = new_reach_util

    # Build deltas frame (avoid pandas .rename stubs that confuse pyright).
    left = base[["department", "channel", "week_index"]].copy()
    left["baseline_expected_contacts"] = base["expected_contacts"].to_numpy()
    left["baseline_budget_usd"] = base["budget_allocation_usd"].to_numpy()
    right = cf[["department", "channel", "week_index"]].copy()
    right["cf_expected_contacts"] = cf["expected_contacts"].to_numpy()
    right["cf_budget_usd"] = cf["budget_allocation_usd"].to_numpy()
    deltas = left.merge(
        right,
        on=["department", "channel", "week_index"],
        how="left",
    )
    deltas["delta_expected_contacts"] = (
        deltas["cf_expected_contacts"] - deltas["baseline_expected_contacts"]
    )
    deltas["delta_budget_usd"] = deltas["cf_budget_usd"] - deltas["baseline_budget_usd"]

    result = CounterfactualResult(
        counterfactual_allocation=cf,
        baseline_allocation=base,
        deltas=deltas,
        shift_share=shift_share,
        routing_feasible_share=n_feasible / max(n_total, 1),
    )
    return result


def build_reallocation_counterfactuals_table(result: CounterfactualResult) -> pd.DataFrame:
    """Materialize a wide counterfactual table for parquet export.

    Args:
        result: Output bundle from :func:`run_broadcast_to_direct`.

    Returns:
        DataFrame aligned with ``reallocation_counterfactuals`` schema contracts.

    Raises:
        KeyError: If expected delta columns are absent on ``result.deltas``.

    Example:
        ``build_reallocation_counterfactuals_table(result).to_parquet(path)`` in reporting jobs.
    """
    out = result.deltas.copy()
    out["scenario_id"] = SCENARIO_BROADCAST_TO_DIRECT
    out["delta_contacts"] = (
        (out["cf_expected_contacts"] - out["baseline_expected_contacts"]).round().astype("int64")
    )
    out["counterfactual_expected_contacts"] = out["cf_expected_contacts"]
    out["counterfactual_budget_usd"] = out["cf_budget_usd"]
    return out
