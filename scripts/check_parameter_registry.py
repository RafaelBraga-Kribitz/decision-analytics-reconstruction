#!/usr/bin/env python3
"""Verify docs/parameter_registry.yaml is in sync with source config files.

For each registered parameter the script:
  1. Loads the referenced source_file.
  2. Searches for the registered ``value`` via key-name lookup (recursive) first,
     then by plain value scan as a fallback (covers aliases like
     ``tsje_participation_rate`` → ``national.participation_rate``).
  3. Fails if a registered value is not found in its declared source_file at all,
     or if a key-matched value has drifted from the registry.

Exit codes: 0 = PASS / GAP (open finding), 1 = FAIL (regression on closed finding).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml
from _governance_check import REPO_ROOT, gate

_REGISTRY = REPO_ROOT / "docs" / "parameter_registry.yaml"

# Top-level registry sections that hold parameter entries.
# Each section maps parameter_name -> {value, source_file, ...}.
_PARAM_SECTIONS = {
    "module_c_pymc_sampler",
    "module_b_budget",
    "module_a_pca",
    "module_a_kmeans",
    "verified_outcome_anchors",
}


def _load_yaml(path: Path) -> dict[str, Any]:
    with open(path) as f:
        raw = yaml.safe_load(f)
    return raw if isinstance(raw, dict) else {}


def _find_by_key(data: Any, key: str) -> list[Any]:
    """Recursively collect all values in ``data`` where the mapping key equals ``key``."""
    found: list[Any] = []
    if isinstance(data, dict):
        for k, v in data.items():
            if k == key:
                found.append(v)
            found.extend(_find_by_key(v, key))
    elif isinstance(data, list):
        for item in data:
            found.extend(_find_by_key(item, key))
    return found


def _value_exists_anywhere(data: Any, target: Any) -> bool:
    """Return True if ``target`` appears as a leaf value anywhere in ``data``."""
    if isinstance(data, dict):
        for v in data.values():
            if _value_exists_anywhere(v, target):
                return True
    elif isinstance(data, list):
        for item in data:
            if _value_exists_anywhere(item, target):
                return True
    else:
        # Numeric tolerance: compare as floats when both are numeric.
        try:
            if float(data) == float(target):  # type: ignore[arg-type]
                return True
        except (TypeError, ValueError):
            pass
        return data == target
    return False


def _numeric_eq(a: Any, b: Any) -> bool:
    try:
        return abs(float(a) - float(b)) < 1e-9
    except (TypeError, ValueError):
        return a == b


def _check_param(
    section_name: str,
    param_name: str,
    meta: dict[str, Any],
) -> str | None:
    """Validate one registry parameter against its source config. Returns error or None."""
    registered_value = meta.get("value")
    source_file_rel = meta.get("source_file")
    if registered_value is None or source_file_rel is None:
        return None

    source_path = REPO_ROOT / source_file_rel
    if not source_path.exists():
        return f"{section_name}.{param_name}: source_file not found: {source_file_rel}"

    config_data = _load_yaml(source_path)
    matches = _find_by_key(config_data, param_name)
    if matches:
        if not any(_numeric_eq(m, registered_value) for m in matches):
            return (
                f"{section_name}.{param_name}: registry={registered_value!r} "
                f"but config has {matches!r} — drift detected in {source_file_rel}"
            )
        return None  # key found with matching value

    # Fallback: value scan for aliased keys (e.g. tsje_participation_rate).
    if not _value_exists_anywhere(config_data, registered_value):
        return (
            f"{section_name}.{param_name}: value {registered_value!r} not found "
            f"in {source_file_rel} — either key renamed or value drifted"
        )
    return None


def check_registry() -> tuple[bool, list[str]]:
    """Return (all_ok, list_of_failure_messages)."""
    if not _REGISTRY.exists():
        return False, [f"registry missing: {_REGISTRY}"]

    registry = _load_yaml(_REGISTRY)
    failures: list[str] = []
    for section_name in _PARAM_SECTIONS:
        section = registry.get(section_name)
        if not isinstance(section, dict):
            continue
        for param_name, meta in section.items():
            if not isinstance(meta, dict):
                continue
            err = _check_param(section_name, param_name, meta)
            if err:
                failures.append(err)
    return len(failures) == 0, failures


def main() -> int:
    ok, failures = check_registry()
    for msg in failures:
        print(f"  MISMATCH: {msg}", file=sys.stderr)
    gap_msg = f"{len(failures)} registry mismatches" if failures else ""
    return gate("F-075", Path(__file__).name, ok, gap_msg)


if __name__ == "__main__":
    sys.exit(main())
