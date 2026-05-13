"""Module B FastAPI weekly-replay API.

Endpoints
---------

* ``GET /healthz`` — liveness probe.
* ``GET /allocation/{scenario_id}`` — solve and return the full allocation
  table as JSON (one row per ``(department, channel, week_index)``).
* ``GET /allocation/{scenario_id}/week/{week_index}`` — narrowed slice for
  a single ISO week.
* ``GET /counterfactual/broadcast_to_direct`` — broadcast-to-direct
  reallocation snapshot with deltas vs. the baseline.
* ``GET /fx/{series_id}`` — Jan–Apr 2018 tiered FX layer for that series.
* ``GET /reach_caps`` — denormalized (department, channel) feature frame.

All endpoints are read-only and stateless; each call re-solves the LP with
the requested seed (default ``20180422``).
"""

from __future__ import annotations

from typing import Literal

import pandas as pd
from fastapi import FastAPI, HTTPException

from module_b_resource_allocation.constants import (
    SCENARIO_BROADCAST_TO_DIRECT,
    VALID_SCENARIOS,
    WEEK_COUNT,
)
from module_b_resource_allocation.data.fx import fx_layer_to_frame, load_fx_layer
from module_b_resource_allocation.models.allocation import build_problem, solve
from module_b_resource_allocation.models.counterfactual import run_broadcast_to_direct
from module_b_resource_allocation.models.feature_join import build_allocation_features
from module_b_resource_allocation.routing.cost_matrix import build_cost_matrix

app = FastAPI(title="Module B Resource Allocation API", version="0.1.0")


def _frame_to_records(df: pd.DataFrame) -> list[dict]:
    return df.to_dict(orient="records")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness probe for orchestration and smoke tests.

    Args:
        None.

    Returns:
        Dict with ``status``, ``module``, and API ``version`` strings.

    Raises:
        None: This handler does not raise.

    Example:
        ``curl -s http://127.0.0.1:8000/healthz`` during deploy checks.
    """
    return {"status": "ok", "module": "module_b_resource_allocation", "version": "0.1.0"}


@app.get("/allocation/{scenario_id}")
def get_allocation(scenario_id: str, seed: int = 20180422) -> dict:
    """Solve the MILP for ``scenario_id`` and return JSON allocation rows.

    Args:
        scenario_id: Canonical scenario label (see ``VALID_SCENARIOS``).
        seed: Deterministic CBC seed forwarded to :func:`build_problem`.

    Returns:
        Dict with solver metadata plus ``rows`` as record dictionaries.

    Raises:
        HTTPException: If ``scenario_id`` is unknown or reserved for the
            counterfactual endpoint.

    Example:
        ``GET /allocation/baseline?seed=20180422`` for a full-table replay.
    """
    if scenario_id not in VALID_SCENARIOS:
        raise HTTPException(
            status_code=404,
            detail=f"unknown scenario_id; valid={sorted(VALID_SCENARIOS)}",
        )
    if scenario_id == SCENARIO_BROADCAST_TO_DIRECT:
        raise HTTPException(
            status_code=400,
            detail="use /counterfactual/broadcast_to_direct for this scenario",
        )
    problem = build_problem(scenario_id=scenario_id, solver_seed=seed)
    result = solve(problem)
    return {
        "scenario_id": scenario_id,
        "solver_status": result.solver_status,
        "fx_series_id": result.fx_series_id,
        "total_budget_usd": round(result.total_budget_usd, 4),
        "row_count": int(len(result.allocation)),
        "rows": _frame_to_records(result.allocation),
    }


@app.get("/allocation/{scenario_id}/week/{week_index}")
def get_allocation_week(scenario_id: str, week_index: int, seed: int = 20180422) -> dict:
    """Return allocation rows filtered to a single ISO week index.

    Args:
        scenario_id: Scenario label passed through to :func:`get_allocation`.
        week_index: 1-based week index constrained to ``1..WEEK_COUNT``.
        seed: Deterministic seed forwarded to the solver stack.

    Returns:
        Same shape as :func:`get_allocation`, but ``rows`` only include the
        requested ``week_index`` and ``row_count`` is updated.

    Raises:
        HTTPException: If ``week_index`` is outside the allowed range.

    Example:
        ``GET /allocation/baseline/week/3`` for a narrow dashboard slice.
    """
    if not 1 <= week_index <= WEEK_COUNT:
        raise HTTPException(status_code=400, detail=f"week_index out of range 1..{WEEK_COUNT}")
    full = get_allocation(scenario_id, seed=seed)
    full["rows"] = [r for r in full["rows"] if r["week_index"] == week_index]
    full["row_count"] = len(full["rows"])
    full["week_index"] = week_index
    return full


@app.get("/counterfactual/broadcast_to_direct")
def get_counterfactual(
    seed: int = 20180422,
    routing_scenario: str = "dry_standard",
    shift_share: float = 0.30,
) -> dict:
    """Compare baseline allocation to a broadcast-to-direct counterfactual.

    Args:
        seed: Deterministic seed for baseline solve and routing matrices.
        routing_scenario: Label passed to :func:`build_cost_matrix`.
        shift_share: Fraction of broadcast spend reallocated toward bilateral channels.

    Returns:
        Dict with counterfactual rows, deltas vs. baseline, and budget totals.

    Raises:
        HTTPException: If downstream builders cannot produce feasible routing
            inputs (surfaced via standard FastAPI error handling).

    Example:
        ``GET /counterfactual/broadcast_to_direct?shift_share=0.25`` for what-if
        budgeting.
    """
    baseline = solve(build_problem(scenario_id="baseline", solver_seed=seed))
    routing = build_cost_matrix(scenario=routing_scenario, seed=seed)
    cf = run_broadcast_to_direct(baseline, routing, shift_share=shift_share)
    return {
        "scenario_id": SCENARIO_BROADCAST_TO_DIRECT,
        "shift_share": shift_share,
        "routing_scenario": routing_scenario,
        "routing_feasible_share": round(cf.routing_feasible_share, 4),
        "total_budget_usd_baseline": round(
            float(cf.baseline_allocation["budget_allocation_usd"].sum()), 2
        ),
        "total_budget_usd_counterfactual": round(
            float(cf.counterfactual_allocation["budget_allocation_usd"].sum()), 2
        ),
        "row_count": int(len(cf.counterfactual_allocation)),
        "rows": _frame_to_records(cf.counterfactual_allocation),
        "deltas": _frame_to_records(cf.deltas),
    }


@app.get("/fx/{series_id}")
def get_fx(series_id: Literal["series_a_monthly", "series_b_weekly"] = "series_b_weekly") -> dict:
    """Expose the tiered FX layer used by allocation as JSON records.

    Args:
        series_id: Which calibrated FX series to materialize.

    Returns:
        Dict with ``series_id`` and ``rows`` suitable for dashboards.

    Raises:
        OSError: If the backing FX artifacts cannot be read from disk.

    Example:
        ``GET /fx/series_b_weekly`` to inspect the default weekly path.
    """
    layer = load_fx_layer(series_id)
    return {
        "series_id": series_id,
        "rows": _frame_to_records(fx_layer_to_frame(layer)),
    }


@app.get("/reach_caps")
def get_reach_caps() -> dict:
    """Return the denormalized (department, channel) reach-cap feature frame.

    Args:
        None.

    Returns:
        Dict with ``row_count`` and ``rows`` records from
        :func:`build_allocation_features`.

    Raises:
        KeyError: If required upstream columns are missing when building features.

    Example:
        ``GET /reach_caps`` before comparing MILP inputs to raw survey tables.
    """
    df = build_allocation_features()
    return {"row_count": int(len(df)), "rows": _frame_to_records(df)}


@app.get("/routing/cost_matrix")
def get_routing_cost(scenario: str = "dry_standard", seed: int = 42) -> dict:
    """Materialize the routing cost matrix for a dry-run scenario.

    Args:
        scenario: Routing scenario label passed to :func:`build_cost_matrix`.
        seed: RNG seed for stochastic tie breaks inside routing heuristics.

    Returns:
        Dict with ``scenario_id``, ``row_count``, and edge ``rows``.

    Raises:
        ValueError: If ``scenario`` is not recognized by the routing builder.

    Example:
        ``GET /routing/cost_matrix?scenario=dry_standard`` when debugging tours.
    """
    df = build_cost_matrix(scenario=scenario, seed=seed)
    return {
        "scenario_id": scenario,
        "row_count": int(len(df)),
        "rows": _frame_to_records(df),
    }
