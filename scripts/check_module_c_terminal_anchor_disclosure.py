#!/usr/bin/env python3
"""Verification script for F-056: C2 must disclose the terminal posterior is anchor-calibrated.

Chart-audit batch 1 (governance/ISSUE_TRIAGE_MASTER.yaml, AUD-C2, severity
critical) flagged reports/eda/generate_eda.py ``chart_c2``: the terminal latent
margin is pinned to the verified outcome anchor m★ = +3.70 pp by a soft
likelihood term (``outcome_anchor ~ Normal(mu_margin[-1], sigma=0.5)`` in
models/tracking/hierarchical.py), so the terminal posterior sits near m★ **by
construction**. The chart drew the posterior mean beside the anchor as if their
proximity were independent agreement / validation.

Closure invariant (static check on the canonical generator):
  1. The C2 anchor line is drawn from the shared ``TSJE_ANCHOR_PP`` constant
     (no bare ``axvline(3.7`` magic literal), labelled as a *calibration target*.
  2. The C2 title frames the panel as a *Calibrated* terminal posterior.
  3. chart_c2 carries an on-chart disclosure that proximity to the anchor is
     "by construction", not out-of-sample validation.

Source-level invariant (no data dependency), matching F-053 / F-055.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

GENERATOR = REPO_ROOT / "reports" / "eda" / "generate_eda.py"

_C2_BLOCK = re.compile(r'@safe_chart\("C2"\).*?(?=@safe_chart\("C3"\))', re.S)
_ANCHOR_LINE = re.compile(
    r'axvline\(\s*TSJE_ANCHOR_PP.*?label\s*=\s*f?"[^"]*[Cc]alibration target[^"]*"',
    re.S,
)
_MAGIC_ANCHOR = re.compile(r"axvline\(\s*3\.7\b")
_TITLE = re.compile(r'set_title\(\s*\n?\s*f?"([^"]*)"')


def _block_gaps(src: str) -> list[str]:
    match = _C2_BLOCK.search(src)
    if not match:
        return ["could not locate the chart_c2 block"]
    block = match.group(0)
    gaps: list[str] = []
    if _MAGIC_ANCHOR.search(block):
        gaps.append("chart_c2 still draws the anchor from a bare 3.7 literal (use TSJE_ANCHOR_PP)")
    if not _ANCHOR_LINE.search(block):
        gaps.append(
            "chart_c2 anchor line not drawn from TSJE_ANCHOR_PP / not labelled a calibration target"
        )
    title = _TITLE.search(block)
    if title is None or "Calibrated" not in title.group(1):
        gaps.append("chart_c2 title does not disclose a 'Calibrated' terminal posterior")
    if "by construction" not in block.lower():
        gaps.append("chart_c2 missing the 'by construction' anchor-pinning disclosure")
    return gaps


def main() -> int:
    if not GENERATOR.is_file():
        return gate("F-056", Path(__file__).name, False, "missing reports/eda/generate_eda.py")
    gaps = _block_gaps(GENERATOR.read_text(encoding="utf-8"))
    detail = (
        "; ".join(gaps)
        if gaps
        else "C2 discloses the terminal posterior is anchor-calibrated (pinned by construction)"
    )
    return gate("F-056", Path(__file__).name, not gaps, detail)


if __name__ == "__main__":
    sys.exit(main())
