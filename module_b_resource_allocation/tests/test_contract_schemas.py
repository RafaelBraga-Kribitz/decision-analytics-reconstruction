"""Round-trip Pydantic validation for handshake-shaped allocation rows."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from module_b_resource_allocation.constants import WEEK_COUNT
from module_b_resource_allocation.contracts.schemas import AllocationHandshakeRow
from module_b_resource_allocation.models.allocation import build_problem, solve
from pydantic import ValidationError

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ALLOCATION_OUTPUT_CONTRACT = _REPO_ROOT / "schema_contracts" / "allocation_output.yaml"


def test_allocation_row_validates_as_handshake() -> None:
    result = solve(build_problem(solver_seed=42))
    row = result.allocation.iloc[0].to_dict()
    model = AllocationHandshakeRow.model_validate(row)
    assert model.department
    assert model.channel


def test_week_index_upper_bound_matches_week_count_ssot() -> None:
    """Regression guard for IMP-B03: the handshake bound must track WEEK_COUNT.

    Before this fix, ``week_index`` was bounded ``le=60`` — a stale value
    that silently accepted an impossible ``week_index=40`` even though the
    SSOT campaign window is 14 weeks. This test fails if ``le=60`` (or any
    value other than ``WEEK_COUNT``) is reintroduced.
    """
    field_info = AllocationHandshakeRow.model_fields["week_index"]
    upper_bounds = [
        meta.le for meta in field_info.metadata if getattr(meta, "le", None) is not None
    ]
    assert upper_bounds, "week_index field must declare an le= upper bound"
    assert upper_bounds[0] == WEEK_COUNT

    with open(_ALLOCATION_OUTPUT_CONTRACT) as f:
        contract = yaml.safe_load(f)
    csv_contract_max = contract["fields"]["week_index"]["max"]
    assert csv_contract_max == WEEK_COUNT
    assert upper_bounds[0] == csv_contract_max


def test_week_index_rejects_out_of_ssot_range_value() -> None:
    """week_index=40 (valid under the old le=60 bound) must now be rejected."""
    base_row = {
        "department": "Asuncion",
        "channel": "whatsapp_chatbot",
        "iso_week": "2018-W40",
        "budget_allocation_usd": 100.0,
        "expected_contacts": 10.0,
        "persuasion_adjusted_contacts": 10.0,
        "scenario_id": "baseline",
        "reach_cap_population_proxy": 1000.0,
    }
    with pytest.raises(ValidationError):
        AllocationHandshakeRow.model_validate({**base_row, "week_index": 40})
