"""IMP-B01 / issue #57: objective-coefficient sensitivity sweep.

Verifies the tornado sweep re-solves under each unmeasured coefficient family's
±perturbation and computes the stability-breach flag against the 15% threshold.
The full sweep re-solves the MILP ~11 times; the perturbation-plumbing unit
tests below need no solve and run fast.
"""

from __future__ import annotations

import pytest
from module_b_resource_allocation.features import diminishing_returns as _dr
from module_b_resource_allocation.models import allocation as _alloc
from module_b_resource_allocation.reporting.parameter_sensitivity import (
    STABILITY_BREACH_PCT,
    _perturbation_context,
    _scaled_coverage,
    _scaled_dict,
    compute_parameter_sensitivity,
)

_FAMILIES = (
    "tier_penalty",
    "scenario_week_weight",
    "dr_k_shape",
    "dr_inflection_pct",
    "coverage_lower_bound_pct",
)


def test_scaled_dict_scales_and_restores() -> None:
    d = {"a": 1.0, "b": 2.0}
    with _scaled_dict(d, 1.2):
        assert d["a"] == pytest.approx(1.2)
        assert d["b"] == pytest.approx(2.4)
    assert d == {"a": 1.0, "b": 2.0}


def test_scaled_coverage_restores_module_constant() -> None:
    before = _alloc.COVERAGE_LOWER_BOUND_PCT
    with _scaled_coverage(0.9):
        assert pytest.approx(before * 0.9) == _alloc.COVERAGE_LOWER_BOUND_PCT
    assert before == _alloc.COVERAGE_LOWER_BOUND_PCT


def test_perturbation_context_restores_every_family() -> None:
    snapshots = {
        "tier_penalty": dict(_alloc._TIER_PENALTY),
        "scenario_week_weight": {s: dict(c) for s, c in _alloc._SCENARIO_WEEK_WEIGHTS.items()},
        "dr_k_shape": dict(_dr._K_SHAPE),
        "dr_inflection_pct": dict(_dr._INFLECTION_PCT),
        "coverage_lower_bound_pct": _alloc.COVERAGE_LOWER_BOUND_PCT,
    }
    for family in _FAMILIES:
        with _perturbation_context(family, 1.2):
            pass
    assert dict(_alloc._TIER_PENALTY) == snapshots["tier_penalty"]
    assert {s: dict(c) for s, c in _alloc._SCENARIO_WEEK_WEIGHTS.items()} == snapshots[
        "scenario_week_weight"
    ]
    assert dict(_dr._K_SHAPE) == snapshots["dr_k_shape"]
    assert dict(_dr._INFLECTION_PCT) == snapshots["dr_inflection_pct"]
    assert snapshots["coverage_lower_bound_pct"] == _alloc.COVERAGE_LOWER_BOUND_PCT


def test_perturbation_context_rejects_unknown_family() -> None:
    with pytest.raises(ValueError):
        _perturbation_context("not_a_family", 1.1)


def test_sensitivity_sweep_shape_and_breach_flag() -> None:
    rows = compute_parameter_sensitivity(
        scenario_id="baseline",
        fx_series_id="series_b_weekly",
        solver_seed=20180422,
    )
    # baseline row + two (minus/plus) rows per swept family
    assert rows[0]["parameter_family"] == "baseline"
    assert rows[0]["pct_change"] == 0.0
    perturbed = rows[1:]
    assert len(perturbed) == 2 * len(_FAMILIES)
    assert {r["parameter_family"] for r in perturbed} == set(_FAMILIES)

    for r in perturbed:
        assert r["direction"] in ("minus", "plus")
        assert set(r) >= {
            "parameter_family",
            "direction",
            "perturbation_pct",
            "total_persuasion_adjusted_contacts",
            "total_budget_usd",
            "pct_change",
            "stability_breach",
        }
        # the breach flag is exactly the >15% rule
        assert r["stability_breach"] == (abs(r["pct_change"]) > STABILITY_BREACH_PCT)
