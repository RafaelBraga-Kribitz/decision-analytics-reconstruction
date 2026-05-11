"""FX path scenarios for Module B (Phase 5).

``FxPath.EARLY_LOCK`` — locks the TC_Ref at the opening rate of the campaign
    (2018-W01 anchor) for all weeks, capturing the cost of committing early
    under a strong-Guaraní leg.

``FxPath.LATE_FLEX`` — uses the rolling weekly TC_Ref (no lock), capturing
    the effect of Guaraní weakening in April on PYG-denominated costs.

Usage
-----
>>> from module_b_resource_allocation.fx.fx_path import FxPath, resolve_tc_for_week
>>> df = apply_retail_spread(build_daily_series(), load_spread_config())
>>> tc = resolve_tc_for_week(df, "2018-W10", FxPath.LATE_FLEX, tier="REF")
"""

from __future__ import annotations

from enum import Enum
from typing import Final

import pandas as pd

_EARLY_LOCK_WEEK: Final[str] = "2018-W01"


class FxPath(Enum):
    """Scenario tags for FX capitalisation timing."""

    EARLY_LOCK = "early_lock"
    LATE_FLEX = "late_flex"


def resolve_tc_for_week(
    daily_df: pd.DataFrame,
    iso_week: str,
    fx_path: FxPath,
    tier: str = "REF",
) -> float:
    """Return the single effective TC rate for a given week and scenario.

    Parameters
    ----------
    daily_df:
        DataFrame from ``apply_retail_spread()``; must have ``iso_week``,
        ``tc_ref``, and ``tc_retail`` columns.
    iso_week:
        Target ISO week label, e.g. ``"2018-W05"``.
    fx_path:
        ``FxPath.EARLY_LOCK`` — always returns the W01 anchor.
        ``FxPath.LATE_FLEX`` — returns the weekly mean for ``iso_week``.
    tier:
        ``"REF"`` (BCP reference) or ``"RETAIL"`` (casa venta).

    Returns
    -------
    float
        TC rate in PYG / USD.
    """
    col = "tc_ref" if tier == "REF" else "tc_retail"

    if col not in daily_df.columns:
        raise KeyError(
            f"Column '{col}' not in DataFrame; apply_retail_spread() first for RETAIL tier."
        )

    if fx_path is FxPath.EARLY_LOCK:
        locked_rows = daily_df[daily_df["iso_week"] == _EARLY_LOCK_WEEK]
        if locked_rows.empty:
            raise ValueError(f"Lock-week {_EARLY_LOCK_WEEK!r} not found in daily series")
        return float(locked_rows[col].mean())

    # LATE_FLEX: rolling weekly mean
    week_rows = daily_df[daily_df["iso_week"] == iso_week]
    if week_rows.empty:
        raise ValueError(f"Week {iso_week!r} not found in daily series")
    return float(week_rows[col].mean())
