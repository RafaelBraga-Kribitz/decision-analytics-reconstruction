"""Contract presence checks for Module C inputs (scaffold)."""

from __future__ import annotations

from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA = _REPO_ROOT / "schema_contracts/allocation_output.yaml"


def test_allocation_output_contract_loads() -> None:
    with open(_SCHEMA) as f:
        spec = yaml.safe_load(f)
    assert spec.get("schema_name") == "allocation_output"
    fields = spec.get("fields", {})
    for key in (
        "department",
        "channel",
        "week_index",
        "expected_contacts",
        "persuasion_adjusted_contacts",
        "scenario_id",
    ):
        assert key in fields, f"missing contract field: {key}"


def test_pymc_importable() -> None:
    import arviz as az  # noqa: F401
    import pymc as pm  # noqa: F401

    assert pm.__name__ == "pymc"
    assert az.__name__ == "arviz"


def _load_schema(name: str) -> dict:
    root = Path(__file__).resolve().parents[2]
    for path in (root / "schema_contracts").glob("*.yaml"):
        with open(path) as f:
            spec = yaml.safe_load(f)
        if spec.get("schema_name") == name:
            return spec
    raise AssertionError(name)


def test_module_c_output_contracts_exist() -> None:
    for name in (
        "daily_posterior_forecast",
        "posterior_house_effects",
        "battleground_department_probability",
        "polls_clean_exit_wave",
    ):
        spec = _load_schema(name)
        assert spec.get("schema_version"), name
        assert spec.get("fields")
