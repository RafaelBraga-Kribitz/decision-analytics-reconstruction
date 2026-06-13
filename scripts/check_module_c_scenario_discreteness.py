#!/usr/bin/env python3
"""Verification script for F-057: C5/C6 must respect discrete, exchangeable MC draws.

ISSUE_TRIAGE_MASTER AUD-C5 (reject): chart_c5 drew a percentile "fan" over a
draw-chunk index — a meaningless x-axis, since Monte-Carlo draws are
exchangeable (no ordering). AUD-C6 (reject): chart_c6 fit a Gaussian KDE over
shock_scale, which clusters at discrete point masses, fabricating continuous
density that is not in the data.

Closure invariant (static check on reports/eda/generate_eda.py):
  C5 — no "Draw Chunk" fan x-axis; discloses the draws are exchangeable.
  C6 — no gaussian_kde over shock_scale; discloses the discrete point masses.

Source-level invariant (no data dependency), matching F-053 / F-055.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

GENERATOR = REPO_ROOT / "reports" / "eda" / "generate_eda.py"
_C5 = re.compile(r'@safe_chart\("C5"\).*?(?=@safe_chart\("C6"\))', re.S)
_C6 = re.compile(r'@safe_chart\("C6"\).*?(?=@safe_chart\("C7"\))', re.S)


def _c5_gaps(block: str) -> list[str]:
    gaps: list[str] = []
    if "Draw Chunk" in block:
        gaps.append("C5 still plots a percentile fan over a meaningless draw-chunk index")
    if "exchangeable" not in block.lower():
        gaps.append("C5 missing the 'draws are exchangeable / no temporal order' disclosure")
    return gaps


def _c6_gaps(block: str) -> list[str]:
    gaps: list[str] = []
    if "gaussian_kde" in block:
        gaps.append("C6 still applies a Gaussian KDE to discrete shock-scale point masses")
    if "point mass" not in block.lower():
        gaps.append("C6 missing the discrete 'point mass' disclosure")
    return gaps


def main() -> int:
    if not GENERATOR.is_file():
        return gate("F-057", Path(__file__).name, False, "missing reports/eda/generate_eda.py")
    src = GENERATOR.read_text(encoding="utf-8")
    c5, c6 = _C5.search(src), _C6.search(src)
    gaps: list[str] = []
    gaps += _c5_gaps(c5.group(0)) if c5 else ["could not locate chart_c5 block"]
    gaps += _c6_gaps(c6.group(0)) if c6 else ["could not locate chart_c6 block"]
    detail = (
        "; ".join(gaps)
        if gaps
        else "C5 shows an exchangeable-draw distribution; C6 marks discrete point masses, no KDE"
    )
    return gate("F-057", Path(__file__).name, not gaps, detail)


if __name__ == "__main__":
    sys.exit(main())
