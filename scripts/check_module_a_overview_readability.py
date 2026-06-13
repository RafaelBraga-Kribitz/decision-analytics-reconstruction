#!/usr/bin/env python3
"""Verification script for F-061: A12 legibility + eda_overview scope honesty.

ISSUE_TRIAGE_MASTER rows (severity reject):
  AUD-A12 — chart_a12 overlaid six translucent filled histograms on one axis,
            an unreadable overplot.
  AUD-PUB-004 — the eda_overview composite was titled "EMPIRICAL DATA OVERVIEW /
            pipeline inputs only" while panel 3 plots participation_propensity (a
            Module A *model output*, not an empirical input), and panel 4 cut
            segment names to 8 characters (truncated bar labels).

Closure invariant (static check on reports/eda/generate_eda.py):
  A12 — uses step-outline histograms (histtype="step"), not filled overplots.
  eda_overview — no ``s[:8]`` truncated labels; no "inputs only" scope claim; and
  the footnote acknowledges the Module A participation-propensity output.

Source-level invariant (no data dependency), matching F-053 / F-055.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

GENERATOR = REPO_ROOT / "reports" / "eda" / "generate_eda.py"
_A12 = re.compile(r'@safe_chart\("A12"\).*?(?=@safe_chart\("A13"\))', re.S)
_OVERVIEW = re.compile(r'@safe_chart\("OVERVIEW"\).*?eda_overview\.png', re.S)


def _a12_gaps(block: str) -> list[str]:
    if 'histtype="step"' not in block:
        return ["A12 still overlays filled histograms instead of legible step outlines"]
    return []


def _overview_gaps(block: str) -> list[str]:
    low = block.lower()
    gaps: list[str] = []
    if "s[:8]" in block:
        gaps.append("eda_overview still truncates segment bar labels to 8 chars")
    if "inputs only" in low:
        gaps.append("eda_overview still claims 'inputs only' while plotting a model output")
    if "module a participation-propensity" not in low:
        gaps.append("eda_overview footnote does not acknowledge the Module A propensity output")
    return gaps


def main() -> int:
    if not GENERATOR.is_file():
        return gate("F-061", Path(__file__).name, False, "missing reports/eda/generate_eda.py")
    src = GENERATOR.read_text(encoding="utf-8")
    a12, ov = _A12.search(src), _OVERVIEW.search(src)
    gaps: list[str] = []
    gaps += _a12_gaps(a12.group(0)) if a12 else ["could not locate chart_a12 block"]
    gaps += _overview_gaps(ov.group(0)) if ov else ["could not locate eda_overview block"]
    detail = (
        "; ".join(gaps)
        if gaps
        else "A12 uses legible step outlines; eda_overview labels its scope and segments honestly"
    )
    return gate("F-061", Path(__file__).name, not gaps, detail)


if __name__ == "__main__":
    sys.exit(main())
