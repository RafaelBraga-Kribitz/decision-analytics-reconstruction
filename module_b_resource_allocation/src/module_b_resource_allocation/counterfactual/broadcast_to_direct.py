"""Broadcast-to-direct reallocation counterfactual engine (Phase 9).

Plan §7.2 specification:
  - Baseline: allocation from run_allocation() (broadcast-heavy channels)
  - Counterfactual: reallocate broadcast budget to direct/field channels
  - Apply bundle-release penalty for any y[g] that flips 1→0
  - Compute delta_contacts = CF_contacts - baseline_contacts (int64, signed)
  - Emit reallocation_counterfactuals.parquet with full scenario metadata

Broadcast channels:  tv_spots, radio_spots, newspaper_inserts
Direct channels:     canvassing, rallies_events, sound_cars, sms_blasts

Bundle-release penalty per bundle (USD): a fraction of the bundle minimum
commitment absorbed as sunk cost / logistical penalty.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from module_b_resource_allocation.constants import CAMPAIGN_BUDGET_USD
from module_b_resource_allocation.models.allocation_lp import BUNDLE_MIN_USD

# Channels reclassified as "broadcast" in this counterfactual
_BROADCAST_CHANNELS: frozenset[str] = frozenset({"tv_spots", "radio_spots", "newspaper_inserts"})

# Channels that receive the reallocated budget
_DIRECT_CHANNELS: list[str] = ["canvassing", "rallies_events", "sound_cars", "sms_blasts"]

# Bundle release penalty: 15% of bundle minimum commitment (sunk logistics cost)
_BUNDLE_RELEASE_PENALTY_RATE: float = 0.15

# Bundles that include broadcast channels; releasing them triggers a penalty
_BROADCAST_BUNDLES: frozenset[str] = frozenset({"conglomerate_x"})


def _unpack_triple_index(idx_raw: object) -> tuple[str, str, int]:
    if not isinstance(idx_raw, tuple) or len(idx_raw) != 3:
        msg = f"expected 3-tuple index key, got {type(idx_raw)!r}"
        raise TypeError(msg)
    return str(idx_raw[0]), str(idx_raw[1]), int(idx_raw[2])


def _bundle_release_penalty(bundle_id: str) -> float:
    """Return the USD penalty for releasing (flipping 0) a bundle."""
    return BUNDLE_MIN_USD.get(bundle_id, 0.0) * _BUNDLE_RELEASE_PENALTY_RATE


def run_counterfactual(
    baseline_result: dict[str, Any],
    seed: int = 42,
    total_budget_usd: float = CAMPAIGN_BUDGET_USD,
) -> dict[str, Any]:
    """Generate the broadcast-to-direct reallocation counterfactual.

    Parameters
    ----------
    baseline_result:
        Dict returned by ``run_allocation()``.
    seed:
        Random seed for within-department reallocation proportions (determinism).
    total_budget_usd:
        Total budget ceiling to respect when reallocating.

    Returns
    -------
    dict with keys:
        counterfactual_df     – per-(dept, channel, week) scenario DataFrame
        any_bundle_flipped    – bool, True if conglomerate_x flipped 0
        total_penalty_usd     – total bundle-release penalty applied
        scenario_id           – "broadcast_to_direct"
    """
    rng = np.random.default_rng(seed)
    baseline_df: pd.DataFrame = baseline_result["allocation_df"].copy()
    baseline_bundle_active: dict[str, bool] = baseline_result.get("bundle_active", {})

    # Determine which broadcast-bundle is being released
    any_bundle_flipped = False
    total_penalty_usd = 0.0

    for bundle_id in _BROADCAST_BUNDLES:
        if baseline_bundle_active.get(bundle_id, False):
            any_bundle_flipped = True
            total_penalty_usd += _bundle_release_penalty(bundle_id)

    # Build a lookup: (dept, channel, week_index) → baseline row
    baseline_lookup = baseline_df.set_index(["department", "channel", "week_index"])

    # Compute broadcast budget freed per (dept, week)
    broadcast_freed: dict[tuple[str, int], float] = {}
    for idx_raw, row in baseline_lookup.iterrows():
        dept, ch, wi = _unpack_triple_index(idx_raw)
        if ch in _BROADCAST_CHANNELS:
            key = (dept, wi)
            broadcast_freed[key] = broadcast_freed.get(key, 0.0) + float(
                row["budget_allocation_usd"]
            )

    # Subtract total penalty from freed budget (applied globally once, spread proportionally)
    total_freed = sum(broadcast_freed.values())
    penalty_share = total_penalty_usd / max(total_freed, 1.0)

    # Build counterfactual rows
    cf_rows = []
    for idx_raw, row in baseline_lookup.iterrows():
        dept, ch, wi = _unpack_triple_index(idx_raw)
        baseline_spend = float(row["budget_allocation_usd"])
        baseline_contacts = int(row["expected_contacts"])
        baseline_persuasion = float(row["persuasion_adjusted_contacts"])

        # Allocate freed broadcast budget to direct channels proportionally
        if ch in _BROADCAST_CHANNELS:
            # Broadcast channels go to zero in counterfactual
            cf_spend = 0.0
        elif ch in _DIRECT_CHANNELS:
            freed = broadcast_freed.get((dept, wi), 0.0)
            # Split freed budget across direct channels with random Dirichlet weights
            weights = rng.dirichlet(np.ones(len(_DIRECT_CHANNELS)))
            ch_idx = _DIRECT_CHANNELS.index(ch)
            extra = freed * weights[ch_idx] * (1.0 - penalty_share)
            cf_spend = baseline_spend + extra
        else:
            cf_spend = baseline_spend

        # Counterfactual contacts: use same per-contact efficiency
        if baseline_spend > 0:
            cf_contacts = int(round(baseline_contacts * (cf_spend / baseline_spend)))
            cf_persuasion = baseline_persuasion * (cf_spend / max(baseline_spend, 1e-9))
        else:
            # For channels with zero baseline, use linear proxy
            sat_spend = cf_spend * 2.0 if cf_spend > 0 else 1.0
            cap_pop = max(baseline_contacts, 100)
            cf_contacts = int(round(cap_pop * (1.0 - 1.0 / (1.0 + cf_spend / sat_spend))))
            prior_p = row.get("persuasion_adjusted_contacts")
            prior_f = float(prior_p) if prior_p is not None else 0.0
            cf_persuasion = cf_contacts * prior_f / max(baseline_contacts, 1)

        delta_contacts = cf_contacts - baseline_contacts

        # Bundle flip flag: only broadcast-bundle channels are affected
        ch_bundle = None
        for bundle_id in _BROADCAST_BUNDLES:
            from module_b_resource_allocation.models.allocation_lp import _CHANNEL_TO_BUNDLE

            if _CHANNEL_TO_BUNDLE.get(ch) == bundle_id and any_bundle_flipped:
                ch_bundle = bundle_id
                break
        bundle_flipped = ch_bundle is not None

        penalty_for_row = _bundle_release_penalty(ch_bundle) if ch_bundle is not None else 0.0

        cf_rows.append(
            {
                "department": dept,
                "channel": ch,
                "week_index": wi,
                "iso_week": row["iso_week"],
                "channel_type": row["channel_type"],
                "scenario_id": "broadcast_to_direct",
                "baseline_budget_usd": round(baseline_spend, 4),
                "reallocated_budget_usd": round(cf_spend, 4),
                "baseline_contacts": baseline_contacts,
                "counterfactual_contacts": cf_contacts,
                "delta_contacts": int(delta_contacts),
                "bundle_flipped_to_zero": bundle_flipped,
                "bundle_release_penalty_usd": round(penalty_for_row, 4),
                "baseline_persuasion_contacts": round(baseline_persuasion, 2),
                "cf_persuasion_contacts": round(cf_persuasion, 2),
            }
        )

    cf_df = pd.DataFrame(cf_rows)
    # Enforce int64 dtype for delta_contacts
    cf_df["delta_contacts"] = cf_df["delta_contacts"].astype("int64")

    return {
        "counterfactual_df": cf_df,
        "any_bundle_flipped": any_bundle_flipped,
        "total_penalty_usd": total_penalty_usd,
        "scenario_id": "broadcast_to_direct",
    }
