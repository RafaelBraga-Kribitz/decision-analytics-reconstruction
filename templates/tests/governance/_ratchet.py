"""Shared ratchet helper for finding verification tests.

Each tests/governance/test_fNNN_*.py is the `verification_script` for finding
F-NNN. It asserts the *fixed* (post-remediation) state, but follows the same
ratchet as the check_*.py scripts:

  finding closed / closed_historical  -> a still-broken condition FAILS (regression)
  finding open / in_progress          -> a still-broken condition xfails (known gap)

This keeps the suite green while findings are open, yet the moment a finding
is marked closed its test starts guarding against regression. The Adversary
(scripts/check_closed_findings.py) runs these via pytest on every PR.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FINDINGS = REPO_ROOT / "governance" / "findings"

ENFORCING = {"closed", "closed_historical"}


def finding_status(finding_id: str) -> str | None:
    path = FINDINGS / f"{finding_id}.yaml"
    if not path.exists():
        return None
    return (yaml.safe_load(path.read_text()) or {}).get("status")


def ratchet(finding_id: str, fixed: bool, gap_msg: str) -> None:
    """Pass if fixed; else fail when the finding is closed, xfail when still open."""
    if fixed:
        return
    if finding_status(finding_id) in ENFORCING:
        pytest.fail(f"{finding_id} regression: {gap_msg}")
    pytest.xfail(f"{finding_id} open: {gap_msg}")
