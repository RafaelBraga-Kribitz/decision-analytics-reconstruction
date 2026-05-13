"""Lightweight YAML contract checks for Module C DataFrames."""

from __future__ import annotations

import pandas as pd
import yaml

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
    spec = load_contract(schema_name)
    fields = spec.get("fields") or {}
    missing = [k for k in fields if k not in df.columns]
    if missing:
        raise QAGateFailure(f"{schema_name}: missing columns {missing}")
    uk = spec.get("unique_key")
    if uk:
        keys = uk if isinstance(uk, list) else [uk]
        dup = df.duplicated(keys)
        if dup.any():
            raise QAGateFailure(f"{schema_name}: duplicate keys on {keys}")
