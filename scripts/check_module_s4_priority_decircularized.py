#!/usr/bin/env python3
"""Verification script for F-064: S4 priority score decircularized (budget removed).

ISSUE_TRIAGE_MASTER row: AUD-S4 (severity reject).
priority_score = win_prob × propensity × log1p(budget). Budget was itself
allocated based on priority (circular). Fix: remove budget from the score.

Closure invariant (static check on reports/eda/generate_eda.py):
  - "log1p" does NOT appear in the S4 block (budget removed)
  - "circularity" or "tautology" appears in the S4 block
  - "win_prob × propensity" appears (the new colorbar label phrasing)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

GENERATOR = REPO_ROOT / "reports" / "eda" / "generate_eda.py"
_S4 = re.compile(r'@safe_chart\("S4"\).*?(?=@safe_chart\("S5"\))', re.S)


def _s4_gaps(block: str) -> list[str]:
    low = block.lower()
    gaps: list[str] = []
    if "log1p" in block:
        gaps.append("S4 still uses log1p(budget) in priority score — circular formula not removed")
    if "circularity" not in low and "tautology" not in low:
        gaps.append("S4 annotation does not mention circularity or tautology")
    if "win_prob × propensity" not in block:
        gaps.append("S4 colorbar label does not contain 'win_prob × propensity'")
    return gaps


def main() -> int:
    if not GENERATOR.is_file():
        return gate("F-064", Path(__file__).name, False, "missing reports/eda/generate_eda.py")
    src = GENERATOR.read_text(encoding="utf-8")
    s4 = _S4.search(src)
    gaps: list[str] = []
    gaps += _s4_gaps(s4.group(0)) if s4 else ["could not locate chart_s4 block"]
    detail = (
        "; ".join(gaps)
        if gaps
        else "S4 priority score is win_prob × propensity (budget removed); circularity disclosed"
    )
    return gate("F-064", Path(__file__).name, not gaps, detail)


if __name__ == "__main__":
    sys.exit(main())
