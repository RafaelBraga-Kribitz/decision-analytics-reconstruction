"""Shared declarative contract-validation core (schema_contracts/*.yaml).

One implementation of "does this DataFrame satisfy its YAML contract" used by
every module gate, so a constraint declared in a contract is enforced the same
way everywhere. See :mod:`contract_core.validator`.
"""

from __future__ import annotations

from contract_core.validator import (
    Contract,
    ContractError,
    ContractViolationError,
    build_conformance_matrix,
    check_frame,
    load_contract_files,
    load_named_contract,
    parse_contract,
    validate_frame,
)

__all__ = [
    "Contract",
    "ContractError",
    "ContractViolationError",
    "build_conformance_matrix",
    "check_frame",
    "load_contract_files",
    "load_named_contract",
    "parse_contract",
    "validate_frame",
]
