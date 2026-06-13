#!/usr/bin/env python3
"""Verification script for F-063: B8 multi-channel contacts vs unique-voter cap disclosed.

ISSUE_TRIAGE_MASTER row: AUD-B8 (severity reject).
expected_contacts exceeded reach_cap by ~5×; without disclosure it looks like
a constraint violation. Fix: disclose that contacts are cumulative multi-channel
exposures while the cap is a unique-voter ceiling.

Closure invariant (static check on reports/eda/generate_eda.py):
  - "cumulative" appears in the B8 block
  - "unique" appears in the B8 block
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

GENERATOR = REPO_ROOT / "reports" / "eda" / "generate_eda.py"
_B8 = re.compile(r'@safe_chart\("B8"\).*?(?=# ════.*MODULE C)', re.S)


def _b8_gaps(block: str) -> list[str]:
    low = block.lower()
    gaps: list[str] = []
    if "cumulative" not in low:
        gaps.append("B8 does not disclose that contacts are cumulative multi-channel exposures")
    if "unique" not in low:
        gaps.append("B8 does not mention unique voter ceiling")
    return gaps


def main() -> int:
    if not GENERATOR.is_file():
        return gate("F-063", Path(__file__).name, False, "missing reports/eda/generate_eda.py")
    src = GENERATOR.read_text(encoding="utf-8")
    b8 = _B8.search(src)
    gaps: list[str] = []
    gaps += _b8_gaps(b8.group(0)) if b8 else ["could not locate chart_b8 block"]
    detail = (
        "; ".join(gaps)
        if gaps
        else "B8 discloses cumulative multi-channel contacts vs unique voter ceiling"
    )
    return gate("F-063", Path(__file__).name, not gaps, detail)


if __name__ == "__main__":
    sys.exit(main())
