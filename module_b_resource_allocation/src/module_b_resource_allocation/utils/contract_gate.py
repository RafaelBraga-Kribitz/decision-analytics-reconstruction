"""Generic ``schema_contracts`` gate for Module B producers.

Thin wrapper over the shared :mod:`contract_core` validator so any Module B
artifact writer can enforce its declared contract with one call:

    ``validate_named_contract(reach_caps_df, "reachability_caps_dept_channel")``

The bespoke ``allocation_output`` gate lives in
:mod:`module_b_resource_allocation.utils.allocation_output_gate`; this module
covers the remaining contracted secondary artifacts (reach caps, routing cost
matrix, reallocation counterfactuals).
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import pandas as pd
from contract_core import check_frame, load_named_contract

_CONTRACTS_DIR: Final[Path] = Path(__file__).resolve().parents[4] / "schema_contracts"


def validate_named_contract(df: pd.DataFrame, schema_name: str) -> None:
    """Validate ``df`` against the named ``schema_contracts`` contract.

    Args:
        df: Frame about to be written to disk.
        schema_name: ``schema_name`` of the contract to enforce.

    Returns:
        None. The gate raises instead of returning a verdict.

    Raises:
        ValueError: If ``df`` violates any declared constraint; the message
            names the contract, column and constraint that failed.

    Example:
        ``validate_named_contract(reach_caps, "reachability_caps_dept_channel")``
        immediately before ``reach_caps.to_csv(...)``.
    """
    contract = load_named_contract(_CONTRACTS_DIR, schema_name)
    violations = check_frame(df, contract)
    if violations:
        raise ValueError(f"{schema_name} contract gate failed: " + "; ".join(violations))
