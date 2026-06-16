"""Detect hardcoded magic values that should live in config files.

Scans Python source files for non-trivial numeric/date literals across:
  - assignments (incl. attributes, subscripts, tuple unpacking)
  - augmented assignments
  - comparisons (if x > 10000:)
  - function-call positional + keyword arguments
  - default parameter values
  - dict / list / set literal RHS

Shared AST visitor lives in scripts/_hardcoded_scan.py (reused by the
notebook scanner). See that module for the full rule set + allowlist.

Gate: F-HARDCODED-VALUES (numeric_drift category)
"""

from __future__ import annotations

import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate
from _hardcoded_scan import format_violation, scan_source

SCAN_DIRS = ["src", "app", "notebooks", "scripts"]
EXCLUDE_DIRS = {"config", "tests", "test", ".venv", "venv", "__pycache__", ".git"}

_FINDING_ID = "F-HARDCODED-VALUES"
_SCRIPT_NAME = "check_hardcoded_values.py"


def _collect_violations(path: Path) -> list[str]:
    try:
        source = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    rel = str(path.relative_to(REPO_ROOT))
    return [format_violation(rel, v) for v in scan_source(source)]


def _python_files_to_scan() -> list[Path]:
    files: list[Path] = []
    for dirname in SCAN_DIRS:
        d = REPO_ROOT / dirname
        if not d.exists():
            continue
        for f in d.rglob("*.py"):
            if any(part in EXCLUDE_DIRS for part in f.parts):
                continue
            files.append(f)
    for f in REPO_ROOT.glob("*.py"):
        files.append(f)
    return files


def _config_exists() -> bool:
    cfg = REPO_ROOT / "config"
    if not cfg.is_dir():
        return False
    return bool(list(cfg.glob("*.yaml")) + list(cfg.glob("*.yml")))


def main() -> int:
    if not _config_exists():
        return gate(
            _FINDING_ID,
            _SCRIPT_NAME,
            False,
            "config/ directory with YAML files not found — "
            "no single source of truth for parameters.",
        )

    all_violations: list[str] = []
    for f in _python_files_to_scan():
        all_violations.extend(_collect_violations(f))

    if all_violations:
        sample = all_violations[0]
        return gate(
            _FINDING_ID,
            _SCRIPT_NAME,
            False,
            f"{len(all_violations)} hardcoded value(s) detected. First: {sample}",
        )

    return gate(_FINDING_ID, _SCRIPT_NAME, True, "no hardcoded magic values found")


if __name__ == "__main__":
    sys.exit(main())
