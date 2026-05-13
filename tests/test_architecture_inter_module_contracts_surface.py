"""Regression: inter-module contract layers (YAML + Pydantic handshake + dataclass gates)."""

from __future__ import annotations

import dataclasses
from pathlib import Path

from module_b_resource_allocation.contracts.schemas import AllocationHandshakeRow
from population_segmentation.data.validator import AnchorCheck
from pydantic import BaseModel

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCHEMA_CONTRACTS = _REPO_ROOT / "schema_contracts"


def test_schema_contracts_yaml_collection_non_empty() -> None:
    yamls = sorted(_SCHEMA_CONTRACTS.glob("*.yaml"))
    assert len(yamls) >= 10, f"Expected at least 10 schema_contracts YAML files, got {len(yamls)}"


def test_allocation_handshake_is_pydantic_model() -> None:
    assert issubclass(AllocationHandshakeRow, BaseModel)


def test_module_a_anchor_check_is_frozen_dataclass() -> None:
    assert dataclasses.is_dataclass(AnchorCheck)
    assert AnchorCheck.__dataclass_params__.frozen is True
