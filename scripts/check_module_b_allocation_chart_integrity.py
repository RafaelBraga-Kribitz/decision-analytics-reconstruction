#!/usr/bin/env python3
"""Verification script for F-060: Module B allocation charts B3/B7/S5 integrity.

ISSUE_TRIAGE_MASTER rows (severity reject), shared theme = Module B chart
presentation that misstates the data:
  AUD-B3 — B3a stacked two *mutually exclusive* budget scenarios (Baseline vs
           Broadcast→Direct), summing alternatives into a meaningless total.
  AUD-B7 — the routing cost matrix labelled only every ~9th department (sparse
           ``// 9`` tick step), leaving the heatmap half-labelled.
  AUD-S5 — a linear OLS fit was titled a "Campaign Efficiency Frontier", which
           is a Pareto (non-dominated) envelope, not a regression line.

Closure invariant (static check on reports/eda/generate_eda.py):
  B3 — stacks exactly the within-budget channel split (one stackplot), and
       discloses the scenarios are mutually exclusive (compared, not summed).
  B7 — labels every origin/destination (full-range ticks, no ``// 9`` step).
  S5 — no longer titles the panel an efficiency frontier; labels the line an OLS
       trend and discloses it is not a Pareto frontier.

Source-level invariant (no data dependency), matching F-053 / F-055.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

GENERATOR = REPO_ROOT / "reports" / "eda" / "generate_eda.py"
_B3 = re.compile(r'@safe_chart\("B3"\).*?(?=@safe_chart\("B4"\))', re.S)
_B7 = re.compile(r'@safe_chart\("B7"\).*?(?=@safe_chart\("B8"\))', re.S)
_S5 = re.compile(r'@safe_chart\("S5"\).*?(?=\nchart_s5\(\))', re.S)


def _b3_gaps(block: str) -> list[str]:
    gaps: list[str] = []
    if block.count("stackplot(") != 1:
        gaps.append("B3 must stack only the within-budget channel split, not the two scenarios")
    if "mutually exclusive" not in block.lower():
        gaps.append("B3 missing the 'mutually exclusive — compared, not summed' disclosure")
    return gaps


def _b7_gaps(block: str) -> list[str]:
    gaps: list[str] = []
    if "// 9" in block:
        gaps.append("B7 still uses a sparse every-9th-department tick step")
    if "set_xticks(range(len(piv.columns)))" not in block:
        gaps.append("B7 does not label every destination department")
    if "set_yticks(range(len(piv.index)))" not in block:
        gaps.append("B7 does not label every origin department")
    return gaps


def _s5_gaps(block: str) -> list[str]:
    low = block.lower()
    gaps: list[str] = []
    if "campaign efficiency frontier by department" in low:
        gaps.append("S5 title still calls a regression line an 'efficiency frontier'")
    if "not a pareto efficiency frontier" not in low:
        gaps.append("S5 missing the 'not a Pareto efficiency frontier' disclosure")
    if "ols" not in low:
        gaps.append("S5 trend line not labelled as a descriptive OLS trend")
    return gaps


def main() -> int:
    if not GENERATOR.is_file():
        return gate("F-060", Path(__file__).name, False, "missing reports/eda/generate_eda.py")
    src = GENERATOR.read_text(encoding="utf-8")
    pairs = [("B3", _B3, _b3_gaps), ("B7", _B7, _b7_gaps), ("S5", _S5, _s5_gaps)]
    gaps: list[str] = []
    for label, pattern, fn in pairs:
        match = pattern.search(src)
        gaps += fn(match.group(0)) if match else [f"could not locate chart_{label.lower()} block"]
    detail = (
        "; ".join(gaps)
        if gaps
        else "B3/B7/S5 present data honestly (no stacked scenarios, full labels, no false frontier)"
    )
    return gate("F-060", Path(__file__).name, not gaps, detail)


if __name__ == "__main__":
    sys.exit(main())
