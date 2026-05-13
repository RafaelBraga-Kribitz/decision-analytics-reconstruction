"""Facade over the canonical PuLP allocator in ``models.allocation``.

The MILP is implemented only in :mod:`module_b_resource_allocation.models.allocation`.
This module preserves the legacy ``run_allocation`` dict API (tests, notebooks)
without duplicating solver logic.
"""

from __future__ import annotations

from typing import Any, cast

import pandas as pd

from module_b_resource_allocation.bundle_definitions import (
    _CHANNEL_TO_BUNDLE,
    BUNDLE_MIN_USD,
    CHANNEL_TO_BUNDLE,
)
from module_b_resource_allocation.constants import (
    CAMPAIGN_BUDGET_USD,
    VALID_SCENARIOS,
    WEEK_COUNT,
)
from module_b_resource_allocation.models.allocation import build_problem, solve


def _scenario_id_from_fx_path(fx_path: str) -> str:
    if fx_path in VALID_SCENARIOS:
        return fx_path
    return "baseline"


def _infer_bundle_active(df: pd.DataFrame) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for bundle_id in BUNDLE_MIN_USD:
        chans = [c for c, b in CHANNEL_TO_BUNDLE.items() if b == bundle_id]
        spend = float(df[df["channel"].isin(chans)]["budget_allocation_usd"].sum())
        bmin = BUNDLE_MIN_USD.get(bundle_id, 0.0)
        out[bundle_id] = spend >= max(bmin - 1.0, 0.0)
    return out


def run_allocation(
    total_budget_usd: float = CAMPAIGN_BUDGET_USD,
    weeks: int = WEEK_COUNT,
    seed: int = 42,
    fx_path: str = "early_lock",
    fx_series_id: str = "series_b_weekly",
) -> dict[str, Any]:
    """Run allocation via the canonical solver; return legacy dict shape.

    Parameters
    ----------
    total_budget_usd:
        Campaign budget envelope.
    weeks:
        Truncate output to the first ``weeks`` ISO weeks (1..14).
    seed:
        CBC random seed forwarded to :func:`build_problem` as ``solver_seed``.
        With identical arguments, the same ``seed`` yields the same solver
        inputs; allocation outputs are reproducible for a fixed PuLP/CBC build.
    fx_path:
        Scenario / FX narrative tag (``early_lock``, ``late_flex``, ``baseline``, …).
    fx_series_id:
        FX layer series passed to :func:`build_problem`.

    Returns
    -------
    dict
        Legacy keys ``allocation_df``, ``bundle_active``, ``solver_obj``, and
        ``solver_status_code`` for notebook compatibility.

    Raises
    ------
    ValueError
        Propagated from :func:`build_problem` when inputs are inconsistent.

    Examples
    --------
    ``run_allocation(total_budget_usd=1.5e6, weeks=14)`` in older integration tests.
    """
    scenario_id = _scenario_id_from_fx_path(fx_path)
    problem = build_problem(
        scenario_id=scenario_id,
        fx_series_id=fx_series_id,  # type: ignore[arg-type]  # str passed to build_problem→load_fx_layer(SeriesId Literal); runtime-validated
        solver_seed=seed,
        budget_usd=float(total_budget_usd),
    )
    result = solve(problem)
    df = result.allocation.copy()
    if weeks < WEEK_COUNT:
        df = df[df["week_index"] <= weeks].copy()

    # Legacy column names expected by contract tests.
    df["fx_path"] = fx_path
    if "bundle_id" in df.columns:
        df = df.assign(conglomerate_id=df["bundle_id"])
    else:
        channel_col = cast(pd.Series, df["channel"])
        df = df.assign(conglomerate_id=channel_col.map(CHANNEL_TO_BUNDLE))

    solver_obj = float(df["persuasion_adjusted_contacts"].sum())
    bundle_active = _infer_bundle_active(df)

    return {
        "allocation_df": df.reset_index(drop=True),
        "bundle_active": bundle_active,
        "solver_obj": solver_obj,
        "solver_status_code": result.solver_status,
    }


# Re-export for ``from module_b_resource_allocation.models.allocation_lp import X``
__all__ = [
    "BUNDLE_MIN_USD",
    "CHANNEL_TO_BUNDLE",
    "_CHANNEL_TO_BUNDLE",
    "run_allocation",
]
