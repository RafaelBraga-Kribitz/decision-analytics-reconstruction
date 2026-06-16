"""Verify every finding YAML names a verification_script that exists on disk.

A finding without a script is unverifiable. This script gates that drift.

Exception: closed_historical findings may carry a null script — they document
one-time changes (e.g., a deletion) with no recurrence surface.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

from _governance_check import REPO_ROOT, gate

FINDINGS = REPO_ROOT / "governance" / "findings"


def main() -> int:
    if not FINDINGS.exists():
        return gate(
            "F-COVERAGE", "check_finding_coverage.py", True,
            "no findings directory yet",
        )

    missing: list[str] = []
    count = 0
    for path in sorted(FINDINGS.glob("F-*.yaml")):
        if path.name == "F-TEMPLATE.yaml":
            continue
        count += 1
        data = yaml.safe_load(path.read_text()) or {}
        status = data.get("status")
        script = data.get("verification_script")
        if status == "closed_historical":
            continue
        if not script:
            missing.append(f"{path.name}: status={status} has no verification_script")
            continue
        if not (REPO_ROOT / script).exists():
            missing.append(f"{path.name}: verification_script '{script}' not found on disk")

    if missing:
        return gate(
            "F-COVERAGE", "check_finding_coverage.py", False,
            f"{len(missing)} finding(s) without a usable script: {missing[0]}",
        )
    return gate(
        "F-COVERAGE", "check_finding_coverage.py", True,
        f"{count} finding(s), each with an existing verification_script",
    )


if __name__ == "__main__":
    sys.exit(main())
