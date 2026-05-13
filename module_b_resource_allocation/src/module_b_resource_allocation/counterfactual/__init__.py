"""Broadcast-to-direct counterfactual (canonical implementation in ``models``)."""

from module_b_resource_allocation.models.counterfactual import (
    CounterfactualResult,
    build_reallocation_counterfactuals_table,
    run_broadcast_to_direct,
)

__all__ = [
    "CounterfactualResult",
    "build_reallocation_counterfactuals_table",
    "run_broadcast_to_direct",
]
