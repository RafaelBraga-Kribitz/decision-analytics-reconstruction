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

import os
import sys
from pathlib import Path

import yaml


def _find_repo_root() -> Path:
    """Locate the consumer's repo root.

    Resolution order:
      1. $GOV_REPO_ROOT environment variable (explicit override).
      2. Nearest ancestor containing PROJECT_CHARTER.md or a .governance-root marker.
      3. Nearest ancestor containing .git/.
      4. parent.parent of this file (legacy default).

    This lets the kit work both at the canonical bootstrap layout (scripts/
    next to templates at the repo root) and when vendored at
    governance/_kit/scripts/ inside a consumer project.
    """
    override = os.environ.get("GOV_REPO_ROOT")
    if override:
        return Path(override).resolve()
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "PROJECT_CHARTER.md").exists() or (parent / ".governance-root").exists():
            return parent
    for parent in here.parents:
        if (parent / ".git").exists():
            return parent
    return here.parent.parent


REPO_ROOT = _find_repo_root()
FINDINGS = REPO_ROOT / "governance" / "findings"

ENFORCING = {"closed", "closed_historical"}


def _status(finding_id: str) -> str | None:
    path = FINDINGS / f"{finding_id}.yaml"
    if not path.exists():
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
