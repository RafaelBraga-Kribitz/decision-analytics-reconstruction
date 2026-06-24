"""Detect hardcoded magic values in Jupyter notebook code cells.

Parses every *.ipynb under notebooks/ (and the repo root), joins each code
cell's source, and runs the shared HardcodedVisitor from _hardcoded_scan.py.

Cells with mixed Jupyter magic (% / !) that fail to parse are skipped.
Cells tagged 'exploratory' or 'scratch' are also skipped.

Gate: F-NOTEBOOK-HARDCODED-VALUES (notebook_drift category)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate
from _hardcoded_scan import scan_source

SCAN_DIRS = ["notebooks", "src", "app", "scripts"]
EXCLUDE_DIRS = {".ipynb_checkpoints", ".venv", "venv", "__pycache__", ".git"}
SKIP_TAGS = {"exploratory", "scratch"}

_FINDING_ID = "F-NOTEBOOK-HARDCODED-VALUES"
_SCRIPT_NAME = "check_notebook_values.py"


def _cell_source(cell: dict) -> str:
    src = cell.get("source", "")
    if isinstance(src, list):
        return "".join(src)
    return src or ""


def _scan_notebook(path: Path) -> list[str]:
    try:
        nb = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, json.JSONDecodeError):
        return []
    rel = str(path.relative_to(REPO_ROOT))
    out: list[str] = []
    for idx, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
        tags = set((cell.get("metadata") or {}).get("tags") or [])
        if tags & SKIP_TAGS:
            continue
        source = _cell_source(cell)
        for v in scan_source(source):
            out.append(f"{rel}#cell-{idx}:{v.lineno}  [{v.kind}] {v.where} = {v.value}")
    return out


def _notebooks_to_scan() -> list[Path]:
    files: list[Path] = []
    for dirname in SCAN_DIRS:
        d = REPO_ROOT / dirname
        if not d.exists():
            continue
        for f in d.rglob("*.ipynb"):
            if any(part in EXCLUDE_DIRS for part in f.parts):
                continue
            files.append(f)
    for f in REPO_ROOT.glob("*.ipynb"):
        files.append(f)
    return files


def main() -> int:
    files = _notebooks_to_scan()
    if not files:
        print(f"[SKIP] {_SCRIPT_NAME}: no .ipynb files found")
        return 0

    all_violations: list[str] = []
    for f in files:
        all_violations.extend(_scan_notebook(f))

    if all_violations:
        return gate(
            _FINDING_ID,
            _SCRIPT_NAME,
            False,
            f"{len(all_violations)} hardcoded value(s) in notebooks. First: {all_violations[0]}",
        )
    return gate(_FINDING_ID, _SCRIPT_NAME, True, "no hardcoded values in notebooks")


if __name__ == "__main__":
    sys.exit(main())
