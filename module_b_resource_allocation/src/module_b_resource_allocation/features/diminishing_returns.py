"""Diminishing returns (DR) curve parameters for Module B (Phase 6).

Each (department, channel) pair gets a piecewise-linear saturating response
with K=6 breakpoints (plan §6.2). The breakpoints are expressed in USD and
span from zero to the saturation spend, which is anchored to the department
population proxy and the reach-cap-based ceiling.

Curve shape parameters:
- ``k_shape``:         log-linear shaping exponent (higher → slower saturation).
- ``inflection_pct``:  fraction of max spend at which marginal returns halve.
- ``breakpoints_usd``: tuple of K=6 spend-axis breakpoints for the linearisation.
"""

from __future__ import annotations

import math
from typing import Final

import pandas as pd

from module_b_resource_allocation.constants import (
    CAMPAIGN_BUDGET_USD,
    CHANNEL_NAMES,
    DEPARTMENTS,
    N_DEPARTMENTS,
)

_K_BREAKPOINTS: Final[int] = 6

# Share of total budget that saturates each (dept, channel) cell.
# Broadcast channels saturate faster (higher spend/reach efficiency per GRP)
# In-person channels saturate due to volunteer capacity.
_SAT_SHARE: dict[str, float] = {
    "whatsapp_chatbot": 0.04,
    "messenger_chatbot": 0.03,
    "facebook_ads": 0.05,
    "sms": 0.03,
    "email": 0.02,
    "tv_spots": 0.10,
    "radio_spots": 0.08,
    "billboards": 0.06,
    "rallies_events": 0.05,
    "canvassing": 0.06,
    "sound_cars": 0.03,
}

_INFLECTION_PCT: dict[str, float] = {
    "whatsapp_chatbot": 0.40,
    "messenger_chatbot": 0.40,
    "facebook_ads": 0.45,
    "sms": 0.45,
    "email": 0.35,
    "tv_spots": 0.50,
    "radio_spots": 0.50,
    "billboards": 0.55,
    "rallies_events": 0.40,
    "canvassing": 0.35,
    "sound_cars": 0.40,
}

_K_SHAPE: dict[str, float] = {
    "whatsapp_chatbot": 1.2,
    "messenger_chatbot": 1.2,
    "facebook_ads": 1.0,
    "sms": 1.1,
    "email": 0.9,
    "tv_spots": 0.8,
    "radio_spots": 0.9,
    "billboards": 0.7,
    "rallies_events": 1.3,
    "canvassing": 1.4,
    "sound_cars": 0.8,
}


def _build_breakpoints(max_usd: float, k: int = _K_BREAKPOINTS) -> list[float]:
    """Return k spend-axis breakpoints in [0, max_usd] on a log-spaced grid."""
    if max_usd <= 0:
        return [0.0] * k
    return [round(math.expm1(i * math.log(max_usd + 1) / (k - 1)), 2) for i in range(k)]


def build_dr_params() -> pd.DataFrame:
    """Build the 198-row (dept × channel) diminishing-returns parameter table.

    Args:
        None.

    Returns
    -------
    pd.DataFrame
        Columns: department, channel, k_shape, inflection_pct, breakpoints_usd,
        saturation_spend_usd.

    Raises:
        None: This builder does not raise for canonical configuration inputs.

    Example:
        Consumed by :func:`build_allocation_features` before MILP assembly.
    """
    # Equal budget weight per department (naive prior — LP will reallocate)
    dept_budget = CAMPAIGN_BUDGET_USD / N_DEPARTMENTS

    rows = []
    for dept in DEPARTMENTS:
        for channel in CHANNEL_NAMES:
            sat_share = _SAT_SHARE.get(channel, 0.05)
            max_usd = dept_budget * sat_share
            bps = _build_breakpoints(max_usd, k=_K_BREAKPOINTS)
            rows.append(
                {
                    "department": dept,
                    "channel": channel,
                    "k_shape": _K_SHAPE.get(channel, 1.0),
                    "inflection_pct": _INFLECTION_PCT.get(channel, 0.45),
                    "breakpoints_usd": bps,
                    "saturation_spend_usd": max_usd,
                }
            )
    return pd.DataFrame(rows)
