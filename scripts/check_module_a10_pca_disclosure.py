#!/usr/bin/env python3
"""Verification script for F-066: A10 PCA lattice disclosed as dept-level constant features.

ISSUE_TRIAGE_MASTER row: AUD-A10 (severity reject).
PCA input features are department-level constants. The biplot lattice reflects
department assignment, not individual-voter variance. Fix: disclose this in title
and annotation.

Closure invariant (static check on reports/eda/generate_eda.py):
  - "dept-level" or "department level" appears in A10 block
  - "department assignment" appears in A10 block
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

GENERATOR = REPO_ROOT / "reports" / "eda" / "generate_eda.py"
_A10 = re.compile(r'@safe_chart\("A10"\).*?(?=@safe_chart\("A11"\))', re.S)


def _a10_gaps(block: str) -> list[str]:
    low = block.lower()
    gaps: list[str] = []
    if "dept-level" not in low and "dept level" not in low and "department level" not in low:
        gaps.append("A10 does not disclose that features are dept-level constants")
    if "department assignment" not in low:
        gaps.append("A10 does not mention department assignment as the source of the PCA pattern")
    return gaps


def main() -> int:
    if not GENERATOR.is_file():
        return gate("F-066", Path(__file__).name, False, "missing reports/eda/generate_eda.py")
    src = GENERATOR.read_text(encoding="utf-8")
    a10 = _A10.search(src)
    gaps: list[str] = []
    gaps += _a10_gaps(a10.group(0)) if a10 else ["could not locate chart_a10 block"]
    detail = (
        "; ".join(gaps)
        if gaps
        else "A10 discloses dept-level constant features; lattice = department assignment"
    )
    return gate("F-066", Path(__file__).name, not gaps, detail)


if __name__ == "__main__":
    sys.exit(main())
