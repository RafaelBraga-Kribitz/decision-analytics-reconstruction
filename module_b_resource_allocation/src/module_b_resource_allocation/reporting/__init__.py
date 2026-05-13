"""Reporting helpers: sensitivity curves, dual exports, benchmark tables."""

from module_b_resource_allocation.reporting.budget_sensitivity import (
    BUDGET_EXPANSION_MULTIPLIERS,
    compute_budget_expansion_curve,
)

__all__ = [
    "BUDGET_EXPANSION_MULTIPLIERS",
    "compute_budget_expansion_curve",
]
