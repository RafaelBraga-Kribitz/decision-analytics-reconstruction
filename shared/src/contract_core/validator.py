"""Declarative contract validation shared by every module gate.

A ``schema_contracts/*.yaml`` may declare these constraint keys; this module is
the single place each one is enforced:

* top level: ``unique_key`` (no duplicate key tuples), ``row_count.exact``
* per field: presence, ``nullable``, ``allowed_values``, ``min``, ``max``,
  ``pattern``, ``unique``

Any key the contract author writes that this module does not recognize aborts
at parse time (:class:`ContractError`) — a silently-ignored typo can never
weaken a gate. Recognized-but-declarative keys (``type``, ``description`` and
the domain soft-gate keys such as ``max_rate``) are accepted but left to the
owning module gate; :data:`METADATA_FIELD_KEYS` enumerates them.

All checks are vectorized pandas; there are no per-row Python loops, so the
largest contracted artifact validates in well under a second.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

# Field-level keys the core actively enforces against the data.
ENFORCED_FIELD_KEYS: frozenset[str] = frozenset(
    {"nullable", "allowed_values", "min", "max", "pattern", "unique"}
)

# Field-level keys recognized as declarative metadata or domain soft-gates: the
# core accepts them (so they do not abort load) but the owning module gate, not
# this core, is responsible for any runtime semantics.
METADATA_FIELD_KEYS: frozenset[str] = frozenset(
    {
        "type",
        "description",
        "validation",
        "max_rate",
        "max_null_rate",
        "unknown_max_rate",
        "expected_true_rate",
        "expected_rate",
        "null_rate_expected",
        "national_mean_target",
        "national_mean_tolerance_pp",
        "tolerance_pp",
        "status",
        "flaw_types",
    }
)

KNOWN_FIELD_KEYS: frozenset[str] = ENFORCED_FIELD_KEYS | METADATA_FIELD_KEYS

KNOWN_TOP_LEVEL_KEYS: frozenset[str] = frozenset(
    {
        "schema_name",
        "schema_version",
        "description",
        "unique_key",
        "row_count",
        "fields",
        "quality_gates",
        "provenance",
        "calibration_gates",
        "calibration_anchors",
        "flaw_types",
    }
)

KNOWN_ROW_COUNT_KEYS: frozenset[str] = frozenset({"exact"})

# Columns of the conformance matrix, in report order.
MATRIX_CONSTRAINTS: tuple[str, ...] = (
    "columns",
    "nullable",
    "allowed_values",
    "min",
    "max",
    "pattern",
    "unique",
    "unique_key",
    "row_count",
)


class ContractError(Exception):
    """Raised when a contract YAML is malformed or declares an unknown key."""


class ContractViolationError(Exception):
    """Raised when a DataFrame fails one or more declared contract constraints."""


@dataclass(frozen=True)
class Contract:
    """Parsed, validated contract ready to check frames against."""

    name: str
    fields: dict[str, dict[str, Any]]
    unique_key: list[str]
    row_count_exact: int | None

    def declared_constraints(self) -> set[str]:
        """Return the matrix-constraint names this contract actually declares."""
        declared: set[str] = set()
        if self.fields:
            declared.add("columns")
        if self.unique_key:
            declared.add("unique_key")
        if self.row_count_exact is not None:
            declared.add("row_count")
        for spec in self.fields.values():
            declared.update(k for k in spec if k in ENFORCED_FIELD_KEYS)
        return declared


def _require_known_keys(spec: dict[str, Any], source: str) -> None:
    unknown = sorted(set(spec) - KNOWN_TOP_LEVEL_KEYS)
    if unknown:
        raise ContractError(f"{source}: unknown top-level contract keys {unknown}")
    row_count = spec.get("row_count")
    if isinstance(row_count, dict):
        bad = sorted(set(row_count) - KNOWN_ROW_COUNT_KEYS)
        if bad:
            raise ContractError(f"{source}: unknown row_count keys {bad}")
    fields = spec.get("fields") or {}
    for fname, fspec in fields.items():
        if not isinstance(fspec, dict):
            continue
        bad_field = sorted(set(fspec) - KNOWN_FIELD_KEYS)
        if bad_field:
            raise ContractError(f"{source}: field {fname!r} declares unknown keys {bad_field}")


def parse_contract(spec: dict[str, Any], *, source: str) -> Contract:
    """Validate ``spec``'s keys and build a :class:`Contract`.

    Args:
        spec: Raw contract mapping loaded from a ``schema_contracts/*.yaml``.
        source: Human-readable origin (schema name or path) for error messages.

    Returns:
        A frozen :class:`Contract`.

    Raises:
        ContractError: If any top-level, ``row_count`` or field key is unknown.
    """
    _require_known_keys(spec, source)
    fields_raw = spec.get("fields")
    fields: dict[str, dict[str, Any]] = {
        k: v for k, v in (fields_raw or {}).items() if isinstance(v, dict)
    }
    uk_raw = spec.get("unique_key")
    if uk_raw is None:
        unique_key: list[str] = []
    elif isinstance(uk_raw, list):
        unique_key = [str(k) for k in uk_raw]
    else:
        unique_key = [str(uk_raw)]
    row_count = spec.get("row_count")
    exact = row_count.get("exact") if isinstance(row_count, dict) else None
    name = str(spec.get("schema_name", source))
    return Contract(name=name, fields=fields, unique_key=unique_key, row_count_exact=exact)


def _check_nullable(name: str, col: str, series: pd.Series, spec: dict[str, Any]) -> list[str]:
    if spec.get("nullable", True):
        return []
    n = int(series.isna().sum())
    if n:
        return [f"{name}.{col}: nullable=false violated ({n} null rows)"]
    return []


def _check_allowed_values(
    name: str, col: str, series: pd.Series, spec: dict[str, Any]
) -> list[str]:
    allowed = spec.get("allowed_values")
    if not allowed:
        return []
    extra = set(series.dropna().unique()) - set(allowed)
    if extra:
        return [f"{name}.{col}: allowed_values violated by {sorted(map(str, extra))}"]
    return []


def _check_bounds(name: str, col: str, series: pd.Series, spec: dict[str, Any]) -> list[str]:
    out: list[str] = []
    lo = spec.get("min")
    hi = spec.get("max")
    if lo is None and hi is None:
        return out
    numeric = pd.to_numeric(series, errors="coerce")
    if lo is not None:
        below = int((numeric < float(lo)).sum())
        if below:
            out.append(f"{name}.{col}: min={lo} violated by {below} rows")
    if hi is not None:
        above = int((numeric > float(hi)).sum())
        if above:
            out.append(f"{name}.{col}: max={hi} violated by {above} rows")
    return out


def _check_pattern(name: str, col: str, series: pd.Series, spec: dict[str, Any]) -> list[str]:
    pattern = spec.get("pattern")
    if not pattern:
        return []
    values = series.dropna().astype(str)
    bad = int((~values.str.match(str(pattern))).sum())
    if bad:
        return [f"{name}.{col}: pattern {pattern!r} violated by {bad} rows"]
    return []


def _check_unique(name: str, col: str, series: pd.Series, spec: dict[str, Any]) -> list[str]:
    if not spec.get("unique"):
        return []
    n = int(series.dropna().duplicated().sum())
    if n:
        return [f"{name}.{col}: unique violated ({n} duplicate rows)"]
    return []


_FIELD_CHECKS = (
    _check_nullable,
    _check_allowed_values,
    _check_bounds,
    _check_pattern,
    _check_unique,
)


def _check_field(name: str, col: str, series: pd.Series, spec: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for check in _FIELD_CHECKS:
        out.extend(check(name, col, series, spec))
    return out


def _check_row_count(df: pd.DataFrame, contract: Contract) -> list[str]:
    exact = contract.row_count_exact
    if exact is not None and len(df) != exact:
        return [f"{contract.name}: row_count exact={exact}, got {len(df)}"]
    return []


def _check_columns(df: pd.DataFrame, contract: Contract) -> list[str]:
    missing = [c for c in contract.fields if c not in df.columns]
    if missing:
        return [f"{contract.name}: missing columns {missing}"]
    return []


def _check_fields(df: pd.DataFrame, contract: Contract) -> list[str]:
    out: list[str] = []
    for col, spec in contract.fields.items():
        if col in df.columns:
            out.extend(_check_field(contract.name, col, df[col], spec))
    return out


def _check_unique_key(df: pd.DataFrame, contract: Contract) -> list[str]:
    key = [k for k in contract.unique_key if k in df.columns]
    if len(key) == len(contract.unique_key) and key and df.duplicated(key).any():
        return [f"{contract.name}: duplicate keys on {contract.unique_key}"]
    return []


_FRAME_CHECKS = (_check_row_count, _check_columns, _check_fields, _check_unique_key)


def check_frame(df: pd.DataFrame, contract: Contract) -> list[str]:
    """Return a list of human-readable violation strings (empty when clean).

    Every string names the contract, the column (when applicable) and the
    constraint, so a caller can surface exactly what failed.
    """
    violations: list[str] = []
    for check in _FRAME_CHECKS:
        violations.extend(check(df, contract))
    return violations


def validate_frame(df: pd.DataFrame, contract: Contract) -> None:
    """Raise :class:`ContractViolationError` if ``df`` breaks any declared constraint."""
    violations = check_frame(df, contract)
    if violations:
        raise ContractViolationError(f"{contract.name}: " + "; ".join(violations))


def build_conformance_matrix(contracts: list[Contract]) -> str:
    """Render a Markdown constraint x contract matrix (declared+enforced cells).

    A ``✓`` means the contract declares that constraint and this core enforces
    it; ``·`` means the contract does not declare it. Every ``✓`` is therefore a
    live runtime gate, not a documentation aspiration.
    """
    header = "| contract | " + " | ".join(MATRIX_CONSTRAINTS) + " |"
    sep = "|" + "---|" * (len(MATRIX_CONSTRAINTS) + 1)
    lines = [
        "# Contract conformance matrix",
        "",
        "Generated by `scripts/generate_conformance_matrix.py` from "
        "`contract_core`. Do not edit by hand; run the script to regenerate.",
        "",
        "`✓` = declared by the contract and enforced by the shared core; " "`·` = not declared.",
        "",
        header,
        sep,
    ]
    for contract in sorted(contracts, key=lambda c: c.name):
        declared = contract.declared_constraints()
        cells = ["✓" if c in declared else "·" for c in MATRIX_CONSTRAINTS]
        lines.append(f"| {contract.name} | " + " | ".join(cells) + " |")
    lines.append("")
    return "\n".join(lines)


def load_named_contract(contracts_dir: Path, schema_name: str) -> Contract:
    """Resolve ``schema_name`` to a parsed :class:`Contract` from ``contracts_dir``.

    Raises:
        ContractError: If no contract in the directory declares that name.
    """
    for path in sorted(contracts_dir.glob("*.yaml")):
        with open(path) as handle:
            spec = yaml.safe_load(handle)
        if isinstance(spec, dict) and spec.get("schema_name") == schema_name:
            return parse_contract(spec, source=schema_name)
    raise ContractError(f"unknown schema_name={schema_name!r} in {contracts_dir}")


def load_contract_files(contracts_dir: Path) -> list[Contract]:
    """Parse every ``*.yaml`` in ``contracts_dir`` into a :class:`Contract`."""
    parsed: list[Contract] = []
    for path in sorted(contracts_dir.glob("*.yaml")):
        with open(path) as handle:
            spec = yaml.safe_load(handle)
        if isinstance(spec, dict) and "fields" in spec:
            parsed.append(parse_contract(spec, source=path.name))
    return parsed
