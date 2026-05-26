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

import logging
import time
from typing import Literal

import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from module_b_resource_allocation.constants import (
    SCENARIO_BROADCAST_TO_DIRECT,
    SEED_MAX,
    SEED_MIN,
    SHIFT_SHARE_MAX,
    SHIFT_SHARE_MIN,
    VALID_FX_SERIES,
    VALID_ROUTING_SCENARIOS,
    VALID_SCENARIOS,
    WEEK_COUNT,
)
from module_b_resource_allocation.data.fx import fx_layer_to_frame, load_fx_layer
from module_b_resource_allocation.models.allocation import build_problem, solve
from module_b_resource_allocation.models.counterfactual import run_broadcast_to_direct
from module_b_resource_allocation.models.feature_join import build_allocation_features
from module_b_resource_allocation.routing.cost_matrix import build_cost_matrix

# Configure structured logging
logger = logging.getLogger("module_b_api")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


app = FastAPI(title="Module B Resource Allocation API", version="0.1.0")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log incoming requests and responses with timing."""
    start_time = time.time()
    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            f"endpoint={request.url.path} method={request.method} "
            f"status_code={response.status_code} duration_ms={duration_ms:.2f}"
        )
        return response
    except Exception as exc:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            f"endpoint={request.url.path} method={request.method} "
            f"error={type(exc).__name__} duration_ms={duration_ms:.2f}"
        )
        raise


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError) -> JSONResponse:
    """Handle solver infeasibility and other runtime errors gracefully.

    Returns 503 Service Unavailable with error details to indicate the solver
    encountered constraints that cannot be satisfied simultaneously.
    """
    return JSONResponse(
        status_code=503,
        content={
            "error": "Allocation solver failed",
            "details": str(exc),
            "message": (
                "Allocation constraints are infeasible for this scenario. "
                "Check budget, reach caps, or department-channel constraints."
            ),
        },
    )


def _frame_to_records(df: pd.DataFrame) -> list[dict]:
    return df.to_dict(orient="records")


def _validate_seed(seed: int) -> None:
    """Validate solver seed is in valid range."""
    if not SEED_MIN <= seed <= SEED_MAX:
        raise HTTPException(
            status_code=400,
            detail=f"seed out of range [{SEED_MIN}, {SEED_MAX}]; got {seed}",
        )


def _validate_scenario(scenario_id: str) -> None:
    """Validate scenario_id is recognized."""
    if scenario_id not in VALID_SCENARIOS:
        raise HTTPException(
            status_code=404,
            detail=f"unknown scenario_id={scenario_id}; valid={sorted(VALID_SCENARIOS)}",
        )


def _validate_week(week_index: int) -> None:
    """Validate week_index is in range [1, WEEK_COUNT]."""
    if not 1 <= week_index <= WEEK_COUNT:
        raise HTTPException(
            status_code=400,
            detail=f"week_index out of range [1, {WEEK_COUNT}]; got {week_index}",
        )


def _validate_shift_share(shift_share: float) -> None:
    """Validate shift_share is in [0, 1]."""
    if not SHIFT_SHARE_MIN <= shift_share <= SHIFT_SHARE_MAX:
        raise HTTPException(
            status_code=400,
            detail=f"shift_share out of range [{SHIFT_SHARE_MIN}, {SHIFT_SHARE_MAX}]; got {shift_share}",
        )


def _validate_routing_scenario(scenario: str) -> None:
    """Validate routing scenario is recognized."""
    if scenario not in VALID_ROUTING_SCENARIOS:
        raise HTTPException(
            status_code=400,
            detail=f"unknown routing scenario={scenario}; valid={sorted(VALID_ROUTING_SCENARIOS)}",
        )


def _validate_fx_series(series_id: str) -> None:
    """Validate FX series_id is recognized."""
    if series_id not in VALID_FX_SERIES:
        raise HTTPException(
            status_code=400,
            detail=f"unknown series_id={series_id}; valid={sorted(VALID_FX_SERIES)}",
        )


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
            Must be in range [0, 2^31-1].

    Returns:
        Dict with solver metadata plus ``rows`` as record dictionaries.

    Raises:
        HTTPException: 404 if scenario_id unknown; 400 if broadcast_to_direct
            or seed out of range.

    Example:
        ``GET /allocation/baseline?seed=20180422`` for a full-table replay.
    """
    _validate_scenario(scenario_id)
    _validate_seed(seed)
    if scenario_id == SCENARIO_BROADCAST_TO_DIRECT:
        raise HTTPException(
            status_code=400,
            detail="use /counterfactual/broadcast_to_direct for this scenario",
        )
    problem = build_problem(scenario_id=scenario_id, solver_seed=seed)
    result = solve(problem)
    logger.info(
        f"allocation scenario_id={scenario_id} solver_status={result.solver_status} "
        f"budget_usd={result.total_budget_usd:.2f} row_count={len(result.allocation)} "
        f"seed={seed}"
    )
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
        week_index: 1-based week index; must be in range [1, WEEK_COUNT].
        seed: Deterministic seed; must be in range [0, 2^31-1].

    Returns:
        Same shape as :func:`get_allocation`, but ``rows`` only include the
        requested ``week_index`` and ``row_count`` is updated.

    Raises:
        HTTPException: 400 if week_index or seed out of range; 404 if scenario
            unknown.

    Example:
        ``GET /allocation/baseline/week/3`` for a narrow dashboard slice.
    """
    _validate_week(week_index)
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
            Must be in range [0, 2^31-1].
        routing_scenario: Label passed to :func:`build_cost_matrix`. Must be
            one of: dry_standard, wet_election_week, chaco_stress.
        shift_share: Fraction of broadcast spend reallocated toward bilateral
            channels. Must be in range [0, 1].

    Returns:
        Dict with counterfactual rows, deltas vs. baseline, and budget totals.

    Raises:
        HTTPException: 400 if seed, routing_scenario, or shift_share invalid.

    Example:
        ``GET /counterfactual/broadcast_to_direct?shift_share=0.25`` for what-if
        budgeting.
    """
    _validate_seed(seed)
    _validate_routing_scenario(routing_scenario)
    _validate_shift_share(shift_share)
    baseline = solve(build_problem(scenario_id="baseline", solver_seed=seed))
    routing = build_cost_matrix(scenario=routing_scenario, seed=seed)
    cf = run_broadcast_to_direct(baseline, routing, shift_share=shift_share)
    budget_baseline = float(cf.baseline_allocation["budget_allocation_usd"].sum())
    budget_counterfactual = float(cf.counterfactual_allocation["budget_allocation_usd"].sum())
    logger.info(
        f"counterfactual routing_scenario={routing_scenario} "
        f"shift_share={shift_share} routing_feasible_share={cf.routing_feasible_share:.2%} "
        f"budget_delta_usd={budget_counterfactual - budget_baseline:.2f} seed={seed}"
    )
    return {
        "scenario_id": SCENARIO_BROADCAST_TO_DIRECT,
        "shift_share": shift_share,
        "routing_scenario": routing_scenario,
        "routing_feasible_share": round(cf.routing_feasible_share, 4),
        "total_budget_usd_baseline": round(budget_baseline, 2),
        "total_budget_usd_counterfactual": round(budget_counterfactual, 2),
        "row_count": int(len(cf.counterfactual_allocation)),
        "rows": _frame_to_records(cf.counterfactual_allocation),
        "deltas": _frame_to_records(cf.deltas),
    }


@app.get("/fx/{series_id}")
def get_fx(series_id: Literal["series_a_monthly", "series_b_weekly"] = "series_b_weekly") -> dict:
    """Expose the tiered FX layer used by allocation as JSON records.

    Args:
        series_id: Which calibrated FX series to materialize. Must be one of:
            series_a_monthly, series_b_weekly.

    Returns:
        Dict with ``series_id`` and ``rows`` suitable for dashboards.

    Raises:
        HTTPException: 400 if series_id unknown; OSError if backing FX
            artifacts cannot be read from disk.

    Example:
        ``GET /fx/series_b_weekly`` to inspect the default weekly path.
    """
    _validate_fx_series(series_id)
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
        scenario: Routing scenario label. Must be one of: dry_standard,
            wet_election_week, chaco_stress.
        seed: RNG seed for stochastic tie breaks inside routing heuristics.
            Must be in range [0, 2^31-1].

    Returns:
        Dict with ``scenario_id``, ``row_count``, and edge ``rows``.

    Raises:
        HTTPException: 400 if scenario or seed invalid.

    Example:
        ``GET /routing/cost_matrix?scenario=dry_standard`` when debugging tours.
    """
    _validate_routing_scenario(scenario)
    _validate_seed(seed)
    df = build_cost_matrix(scenario=scenario, seed=seed)
    return {
        "scenario_id": scenario,
        "row_count": int(len(df)),
        "rows": _frame_to_records(df),
    }
