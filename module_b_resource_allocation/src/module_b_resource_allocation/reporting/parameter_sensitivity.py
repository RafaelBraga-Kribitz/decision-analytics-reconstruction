# pyright: reportPrivateUsage=false
# This sweep deliberately reaches into the coefficient dicts that the objective
# reads (allocation._TIER_PENALTY / _SCENARIO_WEEK_WEIGHTS, diminishing_returns
# _K_SHAPE / _INFLECTION_PCT) to perturb them in place and re-solve. Those dicts
# are the module's tuning surface; perturbing them is this file's whole purpose.
"""Objective-coefficient sensitivity: re-solve under perturbed hand-set parameters.

The budget sweep (``budget_sensitivity.py``) validates LP *mechanics* — how the
objective moves with the one well-governed input, the budget envelope. It says
nothing about how sensitive the recommended allocation is to the coefficients
someone *invented*: ``_tier_penalty``, ``_scenario_week_weight`` and the
diminishing-returns shape parameters (IMP-B01 / issue #57).

This tornado-style sweep perturbs each unmeasured coefficient family and
re-solves at the same budget and seed, recording how far
``total_persuasion_adjusted_contacts`` moves. A family whose ±perturbation moves
the objective by more than ``STABILITY_BREACH_PCT`` is flagged — the run is not
blocked, but the instability is surfaced, not silent.
"""

from __future__ import annotations

import contextlib
from collections.abc import Generator
from typing import Any

from module_b_resource_allocation.constants import CAMPAIGN_BUDGET_USD
from module_b_resource_allocation.features import diminishing_returns as _dr
from module_b_resource_allocation.models import allocation as _alloc
from module_b_resource_allocation.models.allocation import build_problem, solve

# Perturbation magnitudes per family (fraction of the baseline value).
TIER_PENALTY_PCT: float = 0.20
SCENARIO_WEEK_PCT: float = 0.20
DR_K_SHAPE_PCT: float = 0.20
DR_INFLECTION_PCT: float = 0.20
COVERAGE_PCT: float = 0.10

# A single ±perturbation that moves total_persuasion_adjusted_contacts by more
# than this fraction of baseline is flagged as a stability breach.
STABILITY_BREACH_PCT: float = 0.15


@contextlib.contextmanager
def _scaled_dict(
    target: dict[str, Any], factor: float, *, keys: list[str] | None = None
) -> Generator[None, None, None]:
    """Temporarily scale numeric values of ``target`` in place, then restore."""
    keys = keys if keys is not None else list(target.keys())
    saved = {k: target[k] for k in keys}
    try:
        for k in keys:
            target[k] = float(target[k]) * factor
        yield
    finally:
        for k, v in saved.items():
            target[k] = v


@contextlib.contextmanager
def _scaled_scenario_weights(factor: float) -> Generator[None, None, None]:
    """Temporarily scale the early/late emphasis multipliers, then restore."""
    saved = {s: dict(curve) for s, curve in _alloc._SCENARIO_WEEK_WEIGHTS.items()}
    try:
        for curve in _alloc._SCENARIO_WEEK_WEIGHTS.values():
            curve["early"] = float(curve["early"]) * factor
            curve["late"] = float(curve["late"]) * factor
        yield
    finally:
        for s, curve in saved.items():
            _alloc._SCENARIO_WEEK_WEIGHTS[s] = curve


@contextlib.contextmanager
def _scaled_coverage(factor: float) -> Generator[None, None, None]:
    """Temporarily scale the module-level COVERAGE_LOWER_BOUND_PCT, then restore."""
    saved = _alloc.COVERAGE_LOWER_BOUND_PCT
    try:
        _alloc.COVERAGE_LOWER_BOUND_PCT = float(saved) * factor
        yield
    finally:
        _alloc.COVERAGE_LOWER_BOUND_PCT = saved


def _perturbation_context(family: str, factor: float):
    """Return the context manager that applies ``family``'s perturbation."""
    if family == "tier_penalty":
        return _scaled_dict(_alloc._TIER_PENALTY, factor)
    if family == "scenario_week_weight":
        return _scaled_scenario_weights(factor)
    if family == "dr_k_shape":
        return _scaled_dict(_dr._K_SHAPE, factor)
    if family == "dr_inflection_pct":
        return _scaled_dict(_dr._INFLECTION_PCT, factor)
    if family == "coverage_lower_bound_pct":
        return _scaled_coverage(factor)
    raise ValueError(f"unknown coefficient family: {family!r}")


# (family, ±fraction) rows swept, in tornado order.
_SWEEP: tuple[tuple[str, float], ...] = (
    ("tier_penalty", TIER_PENALTY_PCT),
    ("scenario_week_weight", SCENARIO_WEEK_PCT),
    ("dr_k_shape", DR_K_SHAPE_PCT),
    ("dr_inflection_pct", DR_INFLECTION_PCT),
    ("coverage_lower_bound_pct", COVERAGE_PCT),
)


def _solve_contacts(
    *, scenario_id: str, fx_series_id: str, solver_seed: int, budget_usd: float
) -> tuple[float, float, str]:
    """Build + solve once; return (persuasion_adjusted_contacts, budget_usd, status)."""
    problem = build_problem(
        scenario_id=scenario_id,
        fx_series_id=fx_series_id,  # type: ignore[arg-type]  # str→build_problem→load_fx_layer(SeriesId Literal); runtime-validated
        solver_seed=int(solver_seed),
        budget_usd=budget_usd,
    )
    try:
        result = solve(problem)
    except RuntimeError:
        return (0.0, 0.0, "INFEASIBLE")
    return (
        float(result.total_persuasion_adjusted_contacts),
        float(result.total_budget_usd),
        str(result.solver_status),
    )


def compute_parameter_sensitivity(
    *,
    scenario_id: str,
    fx_series_id: str,
    solver_seed: int,
    budget_usd: float | None = None,
) -> list[dict[str, Any]]:
    """Re-solve the MILP under ±perturbation of each unmeasured coefficient family.

    Args:
        scenario_id: Scenario label forwarded to :func:`build_problem`.
        fx_series_id: FX calibration series identifier.
        solver_seed: Deterministic CBC seed reused for every solve.
        budget_usd: Spend envelope; defaults to ``CAMPAIGN_BUDGET_USD``.

    Returns:
        One row per ``(family, direction)`` plus a ``baseline`` row. Each
        perturbation row carries ``total_persuasion_adjusted_contacts``,
        ``total_budget_usd``, the ``pct_change`` versus baseline, and
        ``stability_breach`` (``abs(pct_change) > STABILITY_BREACH_PCT``).

    Raises:
        None: solver infeasibility is captured as a row, not an exception.

    Example:
        Invoked from ``pipeline/run_allocation.py`` when ``--sensitivity`` is set.
    """
    budget = float(budget_usd) if budget_usd is not None else float(CAMPAIGN_BUDGET_USD)
    base_contacts, base_budget, base_status = _solve_contacts(
        scenario_id=scenario_id,
        fx_series_id=fx_series_id,
        solver_seed=solver_seed,
        budget_usd=budget,
    )
    rows: list[dict[str, Any]] = [
        {
            "parameter_family": "baseline",
            "direction": "baseline",
            "perturbation_pct": 0.0,
            "solver_status": base_status,
            "total_persuasion_adjusted_contacts": round(base_contacts, 4),
            "total_budget_usd": round(base_budget, 2),
            "pct_change": 0.0,
            "stability_breach": False,
        }
    ]

    for family, pct in _SWEEP:
        for direction, factor in (("minus", 1.0 - pct), ("plus", 1.0 + pct)):
            with _perturbation_context(family, factor):
                contacts, total_budget, status = _solve_contacts(
                    scenario_id=scenario_id,
                    fx_series_id=fx_series_id,
                    solver_seed=solver_seed,
                    budget_usd=budget,
                )
            pct_change = (contacts - base_contacts) / base_contacts if base_contacts else 0.0
            rows.append(
                {
                    "parameter_family": family,
                    "direction": direction,
                    "perturbation_pct": round((factor - 1.0) * 100.0, 2),
                    "solver_status": status,
                    "total_persuasion_adjusted_contacts": round(contacts, 4),
                    "total_budget_usd": round(total_budget, 2),
                    "pct_change": round(pct_change, 4),
                    "stability_breach": bool(abs(pct_change) > STABILITY_BREACH_PCT),
                }
            )
    return rows
