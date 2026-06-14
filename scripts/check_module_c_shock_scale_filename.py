#!/usr/bin/env python3
"""Verification script for F-059: C10 content must match its win-probability filename.

ISSUE_TRIAGE_MASTER AUD-C10 (reject): chart_c10 saves to
``C10_mc_win_probability_histogram.png`` and its docstring claimed a "Monte
Carlo win-probability histogram", but the panel histograms shock_scale per
scenario and never derives P(win). The filename is kept (a rename would orphan
the committed PNG under F-050), so the chart must instead state plainly that it
is a shock-scale distribution and point P(win) to C3 / C8.

Closure invariant (static check on reports/eda/generate_eda.py chart_c10):
  1. The title frames the panel as a "Shock-Scale Distribution".
  2. It explicitly disclaims "not win probability".
  3. An on-chart disclosure flags the legacy filename and points to C3 / C8.

Source-level invariant (no data dependency), matching F-053 / F-055.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

GENERATOR = REPO_ROOT / "reports" / "eda" / "generate_eda.py"
_C10 = re.compile(r'@safe_chart\("C10"\).*?(?=@safe_chart\("S1"\))', re.S)


def _c10_gaps(block: str) -> list[str]:
    low = block.lower()
    gaps: list[str] = []
    if "shock-scale distribution" not in low:
        gaps.append("C10 title does not frame the panel as a 'Shock-Scale Distribution'")
    if "not win probability" not in low:
        gaps.append("C10 does not disclaim 'not win probability'")
    if "legacy filename" not in low:
        gaps.append("C10 missing the on-chart legacy-filename disclosure pointing P(win) to C3/C8")
    return gaps


def main() -> int:
    if not GENERATOR.is_file():
        return gate("F-059", Path(__file__).name, False, "missing reports/eda/generate_eda.py")
    match = _C10.search(GENERATOR.read_text(encoding="utf-8"))
    gaps = _c10_gaps(match.group(0)) if match else ["could not locate chart_c10 block"]
    detail = (
        "; ".join(gaps)
        if gaps
        else "C10 states it is a shock-scale distribution and points win probability to C3/C8"
    )
    return gate("F-059", Path(__file__).name, not gaps, detail)


if __name__ == "__main__":
    sys.exit(main())
