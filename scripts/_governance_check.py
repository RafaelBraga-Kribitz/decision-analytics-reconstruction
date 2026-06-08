"""Shared ratchet helper for governance check_*.py scripts.

Mirrors the test-side ratchet (tests/governance/_ratchet.py):
  closed / closed_historical  -> [FAIL] exit 1 on regression
  open / in_progress          -> [GAP]  exit 0 (known gap)

Use from a check_*.py script as:

    from _governance_check import REPO_ROOT, gate

    def main() -> int:
        ok = ...  # whatever the invariant is
        gap = "" if ok else "describe the gap"
        return gate("F-NNN", "check_xxx.py", ok, gap)

Each check_*.py is the verification_script for exactly one finding.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
FINDINGS = REPO_ROOT / "governance" / "findings"

ENFORCING = {"closed", "closed_historical"}


def _finding_path(finding_id: str) -> Path | None:
    """Resolve a finding YAML by id (supports F-NNN-slug.yaml filenames)."""
    exact = FINDINGS / f"{finding_id}.yaml"
    if exact.is_file():
        return exact
    if not FINDINGS.is_dir():
        return None
    for path in sorted(FINDINGS.glob(f"{finding_id}*.yaml")):
        if path.name == "F-TEMPLATE.yaml":
            continue
        data = yaml.safe_load(path.read_text()) or {}
        if data.get("id") == finding_id:
            return path
    return None


def _status(finding_id: str) -> str | None:
    path = _finding_path(finding_id)
    if path is None:
        return None
    return (yaml.safe_load(path.read_text()) or {}).get("status")


def gate(finding_id: str, script_name: str, fixed: bool, gap_msg: str) -> int:
    """Print PASS/GAP/FAIL line and return an exit code.

    Use as: `return gate("F-001", "check_charter.py", ok, msg)` at the end of main().
    """
    if fixed:
        print(f"[PASS] {script_name}: {finding_id} clean")
        return 0
    if _status(finding_id) in ENFORCING:
        print(f"[FAIL] {script_name}: {finding_id} regression: {gap_msg}", file=sys.stderr)
        return 1
    print(f"[GAP]  {script_name}: {finding_id} open: {gap_msg}")
    return 0
