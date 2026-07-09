"""Mutation-fixture tests for the shared contract-validation core (IMP-C07).

Every declared constraint key must be *provably* enforceable: for each key we
build one otherwise-clean frame that violates only that key and assert the
validator aborts with a message naming the contract, the column and the
constraint. Unknown constraint keys must abort at parse time.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import pytest
from contract_core import (
    ContractError,
    ContractViolationError,
    check_frame,
    parse_contract,
    validate_frame,
)

# A synthetic contract exercising every enforced constraint key in one place.
_SPEC: dict[str, Any] = {
    "schema_name": "synthetic_all_constraints",
    "schema_version": "1.0.0",
    "unique_key": ["id"],
    "row_count": {"exact": 3},
    "fields": {
        "id": {"type": "int64", "nullable": False, "unique": True},
        "category": {"type": "string", "nullable": False, "allowed_values": ["A", "B"]},
        "score": {"type": "float64", "nullable": False, "min": 0.0, "max": 1.0},
        "code": {"type": "string", "nullable": False, "pattern": r"^X-\d{3}$"},
        "note": {"type": "string", "nullable": True},
    },
}


def _clean_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": [1, 2, 3],
            "category": ["A", "B", "A"],
            "score": [0.1, 0.5, 0.9],
            "code": ["X-001", "X-002", "X-003"],
            "note": ["ok", None, "ok"],
        }
    )


def _contract():
    return parse_contract(_SPEC, source="synthetic_all_constraints")


def test_clean_frame_passes() -> None:
    assert check_frame(_clean_frame(), _contract()) == []
    validate_frame(_clean_frame(), _contract())  # must not raise


def test_nullable_violation_aborts() -> None:
    df = _clean_frame()
    df.loc[0, "category"] = None
    with pytest.raises(
        ContractViolationError, match=r"synthetic_all_constraints\.category: nullable"
    ):
        validate_frame(df, _contract())


def test_allowed_values_violation_aborts() -> None:
    df = _clean_frame()
    df.loc[0, "category"] = "C"
    with pytest.raises(
        ContractViolationError, match=r"category: allowed_values violated by \['C'\]"
    ):
        validate_frame(df, _contract())


def test_min_violation_aborts() -> None:
    df = _clean_frame()
    df.loc[0, "score"] = -0.5
    with pytest.raises(ContractViolationError, match=r"score: min=0.0 violated"):
        validate_frame(df, _contract())


def test_max_violation_aborts() -> None:
    df = _clean_frame()
    df.loc[0, "score"] = 1.5
    with pytest.raises(ContractViolationError, match=r"score: max=1.0 violated"):
        validate_frame(df, _contract())


def test_pattern_violation_aborts() -> None:
    df = _clean_frame()
    df.loc[0, "code"] = "Y-001"
    with pytest.raises(ContractViolationError, match=r"code: pattern .* violated"):
        validate_frame(df, _contract())


def test_unique_field_violation_aborts() -> None:
    df = _clean_frame()
    df.loc[2, "id"] = 1
    with pytest.raises(ContractViolationError, match=r"\.id: unique violated"):
        validate_frame(df, _contract())


def test_unique_key_violation_aborts() -> None:
    # Duplicate the key tuple without tripping the per-field `unique` on id.
    spec = {k: v for k, v in _SPEC.items()}
    spec["fields"] = {k: dict(v) for k, v in _SPEC["fields"].items()}
    spec["fields"]["id"].pop("unique")
    df = _clean_frame()
    df.loc[2, "id"] = 1
    with pytest.raises(ContractViolationError, match=r"duplicate keys on \['id'\]"):
        validate_frame(df, parse_contract(spec, source="synthetic_all_constraints"))


def test_row_count_violation_aborts() -> None:
    df = _clean_frame().head(2)
    with pytest.raises(ContractViolationError, match=r"row_count exact=3, got 2"):
        validate_frame(df, _contract())


def test_missing_column_violation_aborts() -> None:
    df = _clean_frame().drop(columns=["score"])
    with pytest.raises(ContractViolationError, match=r"missing columns \['score'\]"):
        validate_frame(df, _contract())


def test_unknown_top_level_key_aborts_at_parse() -> None:
    spec = dict(_SPEC, bogus_top_key=1)
    with pytest.raises(ContractError, match=r"unknown top-level contract keys \['bogus_top_key'\]"):
        parse_contract(spec, source="synthetic_all_constraints")


def test_unknown_field_key_aborts_at_parse() -> None:
    spec = dict(_SPEC)
    spec["fields"] = {k: dict(v) for k, v in _SPEC["fields"].items()}
    spec["fields"]["score"]["maks"] = 1.0  # typo of `max`
    with pytest.raises(ContractError, match=r"field 'score' declares unknown keys \['maks'\]"):
        parse_contract(spec, source="synthetic_all_constraints")


def test_unknown_row_count_key_aborts_at_parse() -> None:
    spec = dict(_SPEC, row_count={"exact": 3, "approx": 2})
    with pytest.raises(ContractError, match=r"unknown row_count keys \['approx'\]"):
        parse_contract(spec, source="synthetic_all_constraints")


def test_committed_contracts_all_parse() -> None:
    """Every committed contract must parse (i.e. declare only known keys)."""
    from pathlib import Path

    from contract_core import load_contract_files

    root = Path(__file__).resolve().parents[1] / "schema_contracts"
    contracts = load_contract_files(root)
    assert len(contracts) >= 15
