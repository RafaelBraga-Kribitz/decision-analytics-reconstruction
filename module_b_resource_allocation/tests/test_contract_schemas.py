"""Round-trip Pydantic validation for handshake-shaped allocation rows."""

from __future__ import annotations

from module_b_resource_allocation.contracts.schemas import AllocationHandshakeRow
from module_b_resource_allocation.models.allocation import build_problem, solve


def test_allocation_row_validates_as_handshake() -> None:
    result = solve(build_problem(solver_seed=42))
    row = result.allocation.iloc[0].to_dict()
    model = AllocationHandshakeRow.model_validate(row)
    assert model.department
    assert model.channel
