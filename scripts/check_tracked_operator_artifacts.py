#!/usr/bin/env python3
"""Verification script for F-043 (operator-only artifacts must not be public-tracked)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

# Paths that must not appear in `git ls-files` for a public-ready clone.
FORBIDDEN_TRACKED: tuple[str, ...] = (
    "ruvector.db",
    "maintainer/pre_public_cleanup_manifest.md",
    "maintainer/Project_Evaluation.md",
    "maintainer/AUDIT_2026_05_20_COMPREHENSIVE.md",
    "maintainer/AUDIT_REMEDIATION_PLAN_2026-05-26.md",
    ".project-management/audit_task_execution_plan.md",
)

# Warn-only: large operator trees (tracked count threshold).
MAINTAINER_WARN_THRESHOLD = 40


def _tracked() -> set[str]:
    out = subprocess.check_output(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        text=True,
    )
    return {line.strip() for line in out.splitlines() if line.strip()}


def main() -> int:
    tracked = _tracked()
    gaps: list[str] = []

    for path in FORBIDDEN_TRACKED:
        if path in tracked:
            gaps.append(f"tracked:{path}")

    maintainer_count = sum(1 for p in tracked if p.startswith("maintainer/"))
    if maintainer_count > MAINTAINER_WARN_THRESHOLD:
        gaps.append(f"maintainer_tracked_count={maintainer_count}>{MAINTAINER_WARN_THRESHOLD}")

    ok = not gaps
    detail = "; ".join(gaps) if gaps else "no forbidden operator artifacts tracked"
    return gate("F-043", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    sys.exit(main())
