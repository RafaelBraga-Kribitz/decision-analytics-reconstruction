"""Validate config/parameter_registry.yaml completeness and integrity.

Enforces the registry rules from PROJECT_CHARTER SSOT section:

  1. Every leaf key in config/*.yaml (excluding parameter_registry.yaml) must
     appear as a key under parameter_registry.parameter_registry.
  2. Every registry entry's source_file must reference a real config file,
     and the leaf path must exist inside that file.
  3. Every entry has non-null value, source_file under config/, non-empty
     owner (not 'TBD'/'unknown'), rationale >= 20 chars (not 'TBD'/'see code'),
     and a non-empty history list.
  4. Each history record has date / changed_by / old_value / new_value / reason
     fields, and the latest new_value matches the current value.

Gate: F-PARAMETER-REGISTRY-INCOMPLETE (registry_incomplete category)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

from _governance_check import REPO_ROOT, gate

_FINDING_ID = "F-PARAMETER-REGISTRY-INCOMPLETE"
_SCRIPT_NAME = "check_parameter_registry.py"

PLACEHOLDER_TOKENS = {"", "tbd", "unknown", "n/a", "none", "see code"}


def _flatten(prefix: str, node: Any, out: dict[str, Any]) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, dict):
                _flatten(key, v, out)
            else:
                out[key] = v
    else:
        out[prefix] = node


def _load_yaml(path: Path) -> dict:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}


def _placeholder(s: Any) -> bool:
    return isinstance(s, str) and s.strip().lower() in PLACEHOLDER_TOKENS


def _validate_entry(name: str, entry: Any) -> list[str]:
    errs: list[str] = []
    if not isinstance(entry, dict):
        return [f"{name}: entry is not a mapping"]
    if entry.get("value") is None:
        errs.append(f"{name}: missing 'value'")
    src = entry.get("source_file") or ""
    if not src or not str(src).startswith("config/"):
        errs.append(f"{name}: source_file must start with 'config/' (got {src!r})")
    owner = entry.get("owner")
    if _placeholder(owner):
        errs.append(f"{name}: owner is empty or placeholder ({owner!r})")
    rationale = entry.get("rationale") or ""
    if _placeholder(rationale) or len(str(rationale).strip()) < 20:
        errs.append(f"{name}: rationale must be >= 20 chars and non-placeholder")
    history = entry.get("history")
    if not isinstance(history, list) or not history:
        errs.append(f"{name}: history must be a non-empty list")
        return errs
    required = {"date", "changed_by", "old_value", "new_value", "reason"}
    for i, h in enumerate(history):
        if not isinstance(h, dict):
            errs.append(f"{name}: history[{i}] is not a mapping")
            continue
        missing = required - set(h.keys())
        if missing:
            errs.append(f"{name}: history[{i}] missing fields {sorted(missing)}")
    latest = history[-1]
    if isinstance(latest, dict) and latest.get("new_value") != entry.get("value"):
        errs.append(
            f"{name}: latest history.new_value ({latest.get('new_value')!r}) "
            f"does not match current value ({entry.get('value')!r})"
        )
    return errs


def _lookup(tree: dict, dotted: str) -> tuple[bool, Any]:
    cur: Any = tree
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False, None
        cur = cur[part]
    return True, cur


def main() -> int:
    cfg_dir = REPO_ROOT / "config"
    registry_path = cfg_dir / "parameter_registry.yaml"
    if not registry_path.exists():
        return gate(
            _FINDING_ID,
            _SCRIPT_NAME,
            False,
            "config/parameter_registry.yaml not found",
        )

    registry_doc = _load_yaml(registry_path)
    registry = (registry_doc.get("parameter_registry") or {})
    if not isinstance(registry, dict) or not registry:
        return gate(
            _FINDING_ID,
            _SCRIPT_NAME,
            False,
            "parameter_registry block is empty or malformed",
        )

    errors: list[str] = []

    # Rule 3 + 4: per-entry validation
    for name, entry in registry.items():
        errors.extend(_validate_entry(name, entry))

    # Load every config/*.yaml (except registry) flattened
    config_trees: dict[str, dict] = {}
    for f in sorted(cfg_dir.glob("*.yaml")):
        if f.name == "parameter_registry.yaml":
            continue
        config_trees[f.name] = _load_yaml(f)

    all_leaves: dict[str, str] = {}  # dotted_key -> source filename
    for fname, tree in config_trees.items():
        flat: dict[str, Any] = {}
        _flatten("", tree, flat)
        for k in flat:
            all_leaves[k] = fname

    # Rule 1: every config leaf has a registry entry
    for leaf, fname in all_leaves.items():
        if leaf not in registry:
            errors.append(
                f"config/{fname}: leaf '{leaf}' has no parameter_registry entry"
            )

    # Rule 2: every registry source_file exists and contains the key
    for name, entry in registry.items():
        if not isinstance(entry, dict):
            continue
        src = entry.get("source_file") or ""
        if not src.startswith("config/"):
            continue
        rel = src[len("config/"):]
        tree = config_trees.get(rel)
        if tree is None:
            errors.append(f"{name}: source_file {src} does not exist")
            continue
        ok, _ = _lookup(tree, name)
        if not ok:
            errors.append(f"{name}: not found inside {src}")

    if errors:
        return gate(
            _FINDING_ID,
            _SCRIPT_NAME,
            False,
            f"{len(errors)} registry issue(s). First: {errors[0]}",
        )
    return gate(_FINDING_ID, _SCRIPT_NAME, True, "parameter_registry is complete")


if __name__ == "__main__":
    sys.exit(main())
