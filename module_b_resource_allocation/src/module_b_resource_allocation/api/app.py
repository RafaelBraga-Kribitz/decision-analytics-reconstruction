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
    return {"status": "ok", "module": "module_b_resource_allocation", "version": "0.1.0"}


@app.get("/allocation/{scenario_id}")
def get_allocation(scenario_id: str, seed: int = 20180422) -> dict:
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
    layer = load_fx_layer(series_id)
    return {
        "series_id": series_id,
        "rows": _frame_to_records(fx_layer_to_frame(layer)),
    }


@app.get("/reach_caps")
def get_reach_caps() -> dict:
    df = build_allocation_features()
    return {"row_count": int(len(df)), "rows": _frame_to_records(df)}


@app.get("/routing/cost_matrix")
def get_routing_cost(scenario: str = "dry_standard", seed: int = 42) -> dict:
    df = build_cost_matrix(scenario=scenario, seed=seed)
    return {
        "scenario_id": scenario,
        "row_count": int(len(df)),
        "rows": _frame_to_records(df),
    }
