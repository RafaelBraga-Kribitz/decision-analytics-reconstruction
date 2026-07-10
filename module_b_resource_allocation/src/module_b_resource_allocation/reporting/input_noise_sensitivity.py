"""Allocation stability under Module A input noise (IMP-B02 / issue #58).

The MILP consumes ``dept_mean_propensity`` from Module A. This diagnostic
answers "how much does Module A's own uncertainty move the recommendation":
for every department whose feature rows carry a non-degenerate propagated
propensity interval (``dept_propensity_ci_low``/``_high``), the MILP is
re-solved twice with that department's propensity pinned to each interval
bound — the interval-bounds approach the IMP-B02 spec names as the bounded-
runtime fallback to a full scenario ensemble.

Each row of the artifact records the department, its region (so any
systematic Chaco-vs-Oriental interval-width asymmetry is visible — the
IMP-B02 fairness NFR), the interval width, the objective total at the bound,
its percentage change versus baseline, and the perturbed department's own
allocated budget delta. Deterministic: the same features and
``solver_seed`` reproduce the table byte-identically.
"""

from __future__ import annotations

from typing import cast

import pandas as pd

from module_b_resource_allocation.constants import CAMPAIGN_BUDGET_USD, CHACO_DEPARTMENTS
from module_b_resource_allocation.models.allocation import build_problem, solve
from module_b_resource_allocation.models.feature_join import build_allocation_features

#: One artifact row per (department with a non-degenerate interval, bound).
InputNoiseRow = dict[str, str | float | bool]

#: Intervals narrower than this are treated as degenerate (no re-solve).
MIN_INTERVAL_WIDTH: float = 1e-9


def _solve_total(
    features: pd.DataFrame,
    *,
    scenario_id: str,
    fx_series_id: str,
    solver_seed: int,
    budget_usd: float,
) -> tuple[float, pd.DataFrame | None, str]:
    """Solve once on a prepared feature frame; return objective, allocation, status."""
    problem = build_problem(
        scenario_id=scenario_id,
        fx_series_id=fx_series_id,  # type: ignore[arg-type]  # str→load_fx_layer(SeriesId Literal); runtime-validated
        solver_seed=int(solver_seed),
        budget_usd=budget_usd,
        reach_caps=features,
    )
    try:
        result = solve(problem)
    except RuntimeError:
        return (0.0, None, "INFEASIBLE")
    return (
        float(result.total_persuasion_adjusted_contacts),
        result.allocation,
        str(result.solver_status),
    )


def _dept_budget(allocation: pd.DataFrame | None, department: str) -> float:
    if allocation is None:
        return 0.0
    mask = allocation["department"] == department
    return float(allocation.loc[mask, "budget_allocation_usd"].sum())


def compute_input_noise_sensitivity(
    *,
    scenario_id: str,
    fx_series_id: str,
    solver_seed: int,
    budget_usd: float | None = None,
    features: pd.DataFrame | None = None,
) -> list[InputNoiseRow]:
    """Re-solve the MILP at each department's propensity interval bounds.

    Args:
        scenario_id: Scenario label forwarded to :func:`build_problem`.
        fx_series_id: FX calibration series identifier.
        solver_seed: Deterministic CBC seed reused for every solve.
        budget_usd: Spend envelope; defaults to ``CAMPAIGN_BUDGET_USD``.
        features: Optional pre-built allocation feature frame (tests pass a
            fixture); defaults to :func:`build_allocation_features`.

    Returns:
        One ``baseline`` row plus one row per (department with a
        non-degenerate propagated interval, bound in {low, high}) carrying
        ``interval_width``, ``region``, ``total_persuasion_adjusted_contacts``,
        ``pct_change`` vs baseline, and ``dept_budget_delta_usd`` (the
        perturbed department's own allocated budget shift). Departments with
        no interval (NEUTRAL_FALLBACK or a pre-uncertainty artifact) are
        skipped — missing uncertainty is never treated as zero uncertainty.

    Raises:
        KeyError: If ``features`` lacks the interval columns entirely
            (frame predates IMP-B02).

    Example:
        Invoked from ``pipeline/run_allocation.py`` when ``--sensitivity``
        is set; artifact written to
        ``reports/module_b/input_noise_sensitivity.csv``.
    """
    budget = float(budget_usd) if budget_usd is not None else float(CAMPAIGN_BUDGET_USD)
    feats = features if features is not None else build_allocation_features()
    for col in ("dept_propensity_ci_low", "dept_propensity_ci_high", "dept_mean_propensity"):
        if col not in feats.columns:
            raise KeyError(
                f"feature frame lacks {col} — regenerate features with the "
                "IMP-B02 uncertainty-aware ingestion before running this diagnostic"
            )

    base_total, base_alloc, base_status = _solve_total(
        feats,
        scenario_id=scenario_id,
        fx_series_id=fx_series_id,
        solver_seed=solver_seed,
        budget_usd=budget,
    )
    rows: list[InputNoiseRow] = [
        {
            "department": "baseline",
            "region": "ALL",
            "bound": "baseline",
            "propensity_value": float("nan"),
            "interval_width": 0.0,
            "solver_status": base_status,
            "total_persuasion_adjusted_contacts": round(base_total, 4),
            "pct_change": 0.0,
            "dept_budget_delta_usd": 0.0,
        }
    ]

    per_dept_all = cast(
        pd.DataFrame,
        feats.groupby("department")[
            ["dept_mean_propensity", "dept_propensity_ci_low", "dept_propensity_ci_high"]
        ].first(),
    )
    per_dept = cast(
        pd.DataFrame,
        per_dept_all[
            per_dept_all["dept_propensity_ci_low"].notna()
            & per_dept_all["dept_propensity_ci_high"].notna()
        ],
    )
    for dept, dept_row in per_dept.sort_index().iterrows():
        lo = float(dept_row["dept_propensity_ci_low"])
        hi = float(dept_row["dept_propensity_ci_high"])
        width = hi - lo
        if width <= MIN_INTERVAL_WIDTH:
            continue
        for bound, value in (("low", lo), ("high", hi)):
            perturbed = feats.copy()
            perturbed.loc[perturbed["department"] == dept, "dept_mean_propensity"] = value
            total, alloc, status = _solve_total(
                perturbed,
                scenario_id=scenario_id,
                fx_series_id=fx_series_id,
                solver_seed=solver_seed,
                budget_usd=budget,
            )
            pct = (total - base_total) / base_total if base_total else 0.0
            rows.append(
                {
                    "department": str(dept),
                    "region": "CHACO" if str(dept) in CHACO_DEPARTMENTS else "ORIENTAL",
                    "bound": bound,
                    "propensity_value": round(value, 6),
                    "interval_width": round(width, 6),
                    "solver_status": status,
                    "total_persuasion_adjusted_contacts": round(total, 4),
                    "pct_change": round(pct, 6),
                    "dept_budget_delta_usd": round(
                        _dept_budget(alloc, str(dept)) - _dept_budget(base_alloc, str(dept)), 2
                    ),
                }
            )
    return rows
