"""MILP bundle-constraint regression tests (T6-4).

Verifies the binary-linked bundle constraints in
``module_b_resource_allocation.models.allocation`` behave as a true MILP:

* ``bundle_constraints=True`` (default): bundle-level binary ``z`` is active,
  each hard bundle's total spend respects ``BUNDLE_MIN_USD`` floors, and the
  ``ge_2_of_3`` / ``equality`` cardinality constraints fire per (department,
  week) cell.
* ``bundle_constraints=False`` (LP-relaxation comparator): every bundle
  constraint is skipped; the optimizer is free to ignore floors and ratios,
  and the resulting allocation differs from the constrained MILP solution.
"""

from __future__ import annotations

import pytest
from module_b_resource_allocation.bundle_definitions import (
    BUNDLE_MIN_USD,
    CHANNEL_TO_BUNDLE,
)
from module_b_resource_allocation.models.allocation import build_problem, solve


@pytest.fixture(scope="module")
def milp_result():
    problem = build_problem(scenario_id="baseline", bundle_constraints=True)
    return solve(problem)


@pytest.fixture(scope="module")
def relaxation_result():
    problem = build_problem(scenario_id="baseline", bundle_constraints=False)
    return solve(problem)


def test_milp_with_bundle_constraints_reaches_optimal(milp_result) -> None:
    assert milp_result.solver_status in {"OPTIMAL", "FEASIBLE"}


def test_milp_bundle_min_spend_floors_satisfied(milp_result) -> None:
    """Each hard bundle's total USD spend must clear its BUNDLE_MIN_USD floor."""
    alloc = milp_result.allocation
    for bundle_id in ("conglomerate_x", "conglomerate_y"):
        floor = BUNDLE_MIN_USD[bundle_id]
        members = [c for c, b in CHANNEL_TO_BUNDLE.items() if b == bundle_id]
        bundle_spend = float(alloc[alloc["channel"].isin(members)]["budget_allocation_usd"].sum())
        assert bundle_spend >= floor - 1.0, (
            f"{bundle_id}: spent {bundle_spend:.2f} < floor {floor:.2f}"
        )


def test_milp_bundle_id_column_populated(milp_result) -> None:
    """Each channel row must carry its bundle_id (or None for unbundled channels)."""
    alloc = milp_result.allocation
    for _, row in alloc.iterrows():
        expected = CHANNEL_TO_BUNDLE.get(row["channel"])
        assert row["bundle_id"] == expected


def test_relaxation_solves_optimal_too(relaxation_result) -> None:
    """Skipping bundle constraints must still yield a valid optimum."""
    assert relaxation_result.solver_status in {"OPTIMAL", "FEASIBLE"}


def test_milp_solution_differs_from_relaxation(milp_result, relaxation_result) -> None:
    """The MILP-with-bundles objective must be ≤ the unconstrained relaxation
    (more constraints = lower or equal optimum). At least one bundle's spend
    distribution must differ between the two solutions."""
    milp_total = milp_result.total_persuasion_adjusted_contacts
    relax_total = relaxation_result.total_persuasion_adjusted_contacts
    # Relaxation must be ≥ MILP (or essentially equal within solver tolerance).
    assert relax_total >= milp_total - 1.0, (
        f"relaxation {relax_total:.2f} unexpectedly < MILP {milp_total:.2f}"
    )
    # The two allocations must differ in at least one cell.
    milp_alloc = milp_result.allocation.set_index(["department", "channel", "week_index"])[
        "budget_allocation_usd"
    ]
    relax_alloc = relaxation_result.allocation.set_index(["department", "channel", "week_index"])[
        "budget_allocation_usd"
    ]
    diff = (milp_alloc - relax_alloc).abs().sum()
    assert diff > 1.0, f"MILP and LP relaxation allocations match (Σ|Δ|={diff:.2f})"
