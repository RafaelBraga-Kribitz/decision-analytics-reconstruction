#!/usr/bin/env python3
"""Verification script for F-058: C9 transparency scatter must disclose its tiny n.

ISSUE_TRIAGE_MASTER AUD-C9 (reject): chart_c9 plots house-effect magnitude vs
pollster transparency with one point per pollster (~3 pollsters in the fixture)
and the narrative read a "transparency does not predict bias" rule off it. With
n=3 no such relationship is inferable; the panel must disclose it is a
per-pollster audit, not a fitted trend.

Closure invariant (static check on reports/eda/generate_eda.py chart_c9):
  1. The pollster count is computed and surfaced (``n_pollsters``).
  2. The title frames the panel as a "per-pollster audit ... not a fitted trend".
  3. An on-chart disclosure states n is too few to infer a relationship.

Source-level invariant (no data dependency), matching F-053 / F-055.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

GENERATOR = REPO_ROOT / "reports" / "eda" / "generate_eda.py"
_C9 = re.compile(r'@safe_chart\("C9"\).*?(?=@safe_chart\("C10"\))', re.S)


def _c9_gaps(block: str) -> list[str]:
    gaps: list[str] = []
    if "n_pollsters" not in block:
        gaps.append("C9 does not compute/surface the pollster count (n_pollsters)")
    if "not a fitted trend" not in block.lower():
        gaps.append("C9 title does not disclose it is a per-pollster audit, not a fitted trend")
    if "too few" not in block.lower():
        gaps.append("C9 missing the on-chart 'too few to infer a relationship' disclosure")
    return gaps


def main() -> int:
    if not GENERATOR.is_file():
        return gate("F-058", Path(__file__).name, False, "missing reports/eda/generate_eda.py")
    match = _C9.search(GENERATOR.read_text(encoding="utf-8"))
    gaps = _c9_gaps(match.group(0)) if match else ["could not locate chart_c9 block"]
    detail = (
        "; ".join(gaps)
        if gaps
        else "C9 discloses its small pollster n and frames itself as an audit, not a trend"
    )
    return gate("F-058", Path(__file__).name, not gaps, detail)


if __name__ == "__main__":
    sys.exit(main())
