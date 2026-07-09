"""YAML contract checks for Module C DataFrames (layered on ``contract_core``).

``load_contract`` resolves a ``schema_name`` to its ``schema_contracts/*.yaml``
spec; ``validate_dataframe_contract`` delegates to the shared
:mod:`contract_core` validator so every declared constraint (nullable,
allowed_values, min/max, pattern, per-field unique, unique_key, row_count) is
enforced the same way here as in every other module gate.
"""

from __future__ import annotations

import pandas as pd
import yaml
from contract_core import ContractError, check_frame, parse_contract

from module_c_forecasting_scenarios.data.exceptions import QAGateFailure
from module_c_forecasting_scenarios.paths import schema_contracts_dir


def load_contract(schema_name: str) -> dict[str, object]:
    d = schema_contracts_dir()
    for path in d.glob("*.yaml"):
        with open(path) as f:
            spec = yaml.safe_load(f)
        if spec.get("schema_name") == schema_name:
            return spec
    raise QAGateFailure(f"Unknown schema_name={schema_name!r}")


def validate_dataframe_contract(df: pd.DataFrame, schema_name: str) -> None:
    """Enforce every declared constraint in ``schema_name`` against ``df``.

    Args:
        df: Frame to validate.
        schema_name: ``schema_name`` of a ``schema_contracts/*.yaml`` contract.

    Raises:
        QAGateFailure: If the contract declares an unknown key, or ``df``
            violates any declared constraint. The message names the contract,
            column and constraint that failed.
    """
    spec = load_contract(schema_name)
    try:
        contract = parse_contract(spec, source=schema_name)
    except ContractError as exc:
        raise QAGateFailure(str(exc)) from exc
    violations = check_frame(df, contract)
    if violations:
        raise QAGateFailure(f"{schema_name}: " + "; ".join(violations))
