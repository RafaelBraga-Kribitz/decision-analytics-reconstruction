"""Detect config keys that are declared but never referenced in code.

For each leaf key in config/*.yaml (excluding parameter_registry.yaml),
grep across src/, app/, scripts/, notebooks/, sql/, queries/, models/ for
any of these access patterns:

    config.<leaf>          cfg.<leaf>
    config["<leaf>"]       cfg["<leaf>"]
    config['<leaf>']       cfg['<leaf>']
    "<leaf>"               (last-resort literal string match, for dynamic lookups)

A leaf with zero references is reported as an orphan.

Gate: F-CONFIG-ORPHANS (registry_incomplete category)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml

from _governance_check import REPO_ROOT, gate

_FINDING_ID = "F-CONFIG-ORPHANS"
_SCRIPT_NAME = "check_config_orphans.py"

SCAN_DIRS = ["src", "app", "scripts", "notebooks", "sql", "queries", "models"]
EXCLUDE_DIRS = {".venv", "venv", "__pycache__", ".git", ".ipynb_checkpoints"}
EXTS = {".py", ".ipynb", ".sql", ".sql.j2", ".yaml", ".yml", ".j2"}


def _flatten(prefix: str, node: Any, out: dict[str, Any]) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, dict):
                _flatten(key, v, out)
            else:
                out[key] = v


def _gather_corpus() -> str:
    parts: list[str] = []
    for dirname in SCAN_DIRS:
        d = REPO_ROOT / dirname
        if not d.exists():
            continue
        for f in d.rglob("*"):
            if not f.is_file():
                continue
            if any(part in EXCLUDE_DIRS for part in f.parts):
                continue
            if f.suffix not in EXTS and not f.name.endswith(".sql.j2"):
                continue
            try:
                parts.append(f.read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                continue
    return "\n".join(parts)


def _is_referenced(leaf: str, corpus: str) -> bool:
    # leaf is dotted, e.g. "quality_gates.coverage.min_lines"; the final
    # segment is the most actionable for grep, the full path for safety.
    final = leaf.split(".")[-1]
    patterns = [
        rf"\bconfig\.{re.escape(leaf)}\b",
        rf"\bcfg\.{re.escape(leaf)}\b",
        rf"\bconfig\[['\"]{re.escape(leaf)}['\"]\]",
        rf"\bcfg\[['\"]{re.escape(leaf)}['\"]\]",
        rf"\bconfig\[['\"]{re.escape(final)}['\"]\]",
        rf"\bcfg\[['\"]{re.escape(final)}['\"]\]",
        rf"\bconfig\.{re.escape(final)}\b",
        rf"\bcfg\.{re.escape(final)}\b",
        rf"['\"]{re.escape(leaf)}['\"]",
    ]
    for p in patterns:
        if re.search(p, corpus):
            return True
    return False


def main() -> int:
    cfg_dir = REPO_ROOT / "config"
    if not cfg_dir.is_dir():
        print(f"[SKIP] {_SCRIPT_NAME}: no config/ directory")
        return 0

    leaves: dict[str, str] = {}
    for f in sorted(cfg_dir.glob("*.yaml")):
        if f.name == "parameter_registry.yaml":
            continue
        try:
            tree = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        flat: dict[str, Any] = {}
        _flatten("", tree, flat)
        for k in flat:
            leaves[k] = f.name

    if not leaves:
        print(f"[SKIP] {_SCRIPT_NAME}: no config leaf keys to check")
        return 0

    corpus = _gather_corpus()
    if not corpus:
        print(f"[SKIP] {_SCRIPT_NAME}: no source files to scan against")
        return 0

    orphans = [
        f"config/{fname}: '{leaf}' never referenced in code"
        for leaf, fname in leaves.items()
        if not _is_referenced(leaf, corpus)
    ]

    if orphans:
        return gate(
            _FINDING_ID,
            _SCRIPT_NAME,
            False,
            f"{len(orphans)} orphan config key(s). First: {orphans[0]}",
        )
    return gate(_FINDING_ID, _SCRIPT_NAME, True, "no orphan config keys")


if __name__ == "__main__":
    sys.exit(main())
