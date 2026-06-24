"""Detect code references to config keys that don't exist in any config/*.yaml.

Scans Python files under src/, app/, scripts/, notebooks/ for these patterns:

    config.<dotted>          cfg.<dotted>
    config["<key>"]           cfg["<key>"]
    config['<key>']           cfg['<key>']

For each captured key, resolves it against the merged tree of every
config/*.yaml (excluding parameter_registry.yaml). Unresolved references
indicate a typo or stale rename — silent bugs at runtime.

Gate: F-CONFIG-REFERENCE-RESOLUTION (registry_incomplete category)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

from _governance_check import REPO_ROOT, gate

_FINDING_ID = "F-CONFIG-REFERENCE-RESOLUTION"
_SCRIPT_NAME = "check_config_references.py"

SCAN_DIRS = ["src", "app", "scripts", "notebooks"]
EXCLUDE_DIRS = {".venv", "venv", "__pycache__", ".git", ".ipynb_checkpoints"}

ATTR_RE = re.compile(r"\b(?:config|cfg)\.([A-Za-z_][\w.]*)")
SUB_RE = re.compile(r"\b(?:config|cfg)\[['\"]([^'\"]+)['\"]\]")

# Identifiers commonly chained on a config object that are not config keys.
STDLIB_TAILS = {"get", "items", "keys", "values", "update", "pop", "setdefault"}


def _flatten_keys(prefix: str, node: Any, out: set[str]) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            out.add(key)
            if isinstance(v, dict):
                _flatten_keys(key, v, out)


def _load_known_keys() -> set[str]:
    cfg_dir = REPO_ROOT / "config"
    keys: set[str] = set()
    if not cfg_dir.is_dir():
        return keys
    for f in sorted(cfg_dir.glob("*.yaml")):
        if f.name == "parameter_registry.yaml":
            continue
        try:
            tree = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        _flatten_keys("", tree, keys)
    return keys


def _candidate_paths(dotted: str) -> list[str]:
    # "a.b.get" or "a.b.items" — strip trailing stdlib-ish call
    parts = dotted.split(".")
    while parts and parts[-1] in STDLIB_TAILS:
        parts.pop()
    out: list[str] = []
    while parts:
        out.append(".".join(parts))
        parts.pop()
    return out


def _resolves(dotted: str, known: set[str]) -> bool:
    for cand in _candidate_paths(dotted):
        if cand in known:
            return True
    return False


def _scan_source(text: str, rel: str, lineno_base: int, known: set[str]) -> list[str]:
    out: list[str] = []
    for lineno, line in enumerate(text.splitlines(), start=lineno_base):
        for m in ATTR_RE.finditer(line):
            ref = m.group(1)
            if not _resolves(ref, known):
                out.append(f"{rel}:{lineno}  config.{ref} — key not found in config/*.yaml")
        for m in SUB_RE.finditer(line):
            ref = m.group(1)
            if ref not in known and ref.split(".")[0] not in {k.split(".")[0] for k in known}:
                # also try as a top-level leaf name
                if not any(k == ref or k.endswith("." + ref) for k in known):
                    out.append(f"{rel}:{lineno}  config[{ref!r}] — key not found in config/*.yaml")
    return out


def _scan_python(path: Path, known: set[str]) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    rel = str(path.relative_to(REPO_ROOT))
    return _scan_source(text, rel, 1, known)


def _scan_notebook(path: Path, known: set[str]) -> list[str]:
    try:
        nb = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, json.JSONDecodeError):
        return []
    rel = str(path.relative_to(REPO_ROOT))
    out: list[str] = []
    for idx, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
        src = cell.get("source", "")
        text = "".join(src) if isinstance(src, list) else (src or "")
        for hit in _scan_source(text, f"{rel}#cell-{idx}", 1, known):
            out.append(hit)
    return out


def _files_to_scan() -> tuple[list[Path], list[Path]]:
    pys: list[Path] = []
    nbs: list[Path] = []
    for dirname in SCAN_DIRS:
        d = REPO_ROOT / dirname
        if not d.exists():
            continue
        for f in d.rglob("*.py"):
            if any(part in EXCLUDE_DIRS for part in f.parts):
                continue
            pys.append(f)
        for f in d.rglob("*.ipynb"):
            if any(part in EXCLUDE_DIRS for part in f.parts):
                continue
            nbs.append(f)
    return pys, nbs


def main() -> int:
    known = _load_known_keys()
    if not known:
        print(f"[SKIP] {_SCRIPT_NAME}: no config keys to resolve against")
        return 0

    pys, nbs = _files_to_scan()
    out: list[str] = []
    for f in pys:
        out.extend(_scan_python(f, known))
    for f in nbs:
        out.extend(_scan_notebook(f, known))

    if out:
        return gate(
            _FINDING_ID,
            _SCRIPT_NAME,
            False,
            f"{len(out)} unresolved config reference(s). First: {out[0]}",
        )
    return gate(_FINDING_ID, _SCRIPT_NAME, True, "all config references resolve")


if __name__ == "__main__":
    sys.exit(main())
