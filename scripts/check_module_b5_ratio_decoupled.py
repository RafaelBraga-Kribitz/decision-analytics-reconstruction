#!/usr/bin/env python3
"""Verification script for F-062: B5 x-axis decoupled from ratio denominator.

ISSUE_TRIAGE_MASTER row: AUD-B5 (severity reject).
chart_b5 plotted total_budget on the x-axis while y-axis was
cpp = total_budget / total_persuasion — budget in both axes = tautological correlation.

Closure invariant (static check on reports/eda/generate_eda.py):
  - x-axis label is "Total Persuasion-Adjusted Contacts"
  - annotation contains "ratio denominator"
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

GENERATOR = REPO_ROOT / "reports" / "eda" / "generate_eda.py"
_B5 = re.compile(r'@safe_chart\("B5"\).*?(?=@safe_chart\("B6"\))', re.S)


def _b5_gaps(block: str) -> list[str]:
    gaps: list[str] = []
    if "Total Persuasion-Adjusted Contacts" not in block:
        gaps.append("B5 x-axis label does not say 'Total Persuasion-Adjusted Contacts'")
    if "ratio denominator" not in block.lower():
        gaps.append("B5 annotation does not mention 'ratio denominator'")
    return gaps


def main() -> int:
    if not GENERATOR.is_file():
        return gate("F-062", Path(__file__).name, False, "missing reports/eda/generate_eda.py")
    src = GENERATOR.read_text(encoding="utf-8")
    b5 = _B5.search(src)
    gaps: list[str] = []
    gaps += _b5_gaps(b5.group(0)) if b5 else ["could not locate chart_b5 block"]
    detail = (
        "; ".join(gaps)
        if gaps
        else "B5 x-axis is total persuasion contacts; ratio denominator annotation present"
    )
    return gate("F-062", Path(__file__).name, not gaps, detail)


if __name__ == "__main__":
    sys.exit(main())
