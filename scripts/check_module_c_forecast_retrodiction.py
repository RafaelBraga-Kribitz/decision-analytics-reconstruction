#!/usr/bin/env python3
"""Verification script for F-055: Module C C1 must read as a retrodiction, not a forecast.

Chart-audit batch 1 (governance/ISSUE_TRIAGE_MASTER.yaml, AUD-C1, severity
critical, blocks AUD-C2) flagged reports/eda/generate_eda.py ``chart_c1`` for
two defects:

  1. It titled an in-sample Bayesian *tracking retrodiction* of the past 2018
     Series A election a "Forecast Timeline" — overstating predictive power for
     an election whose outcome is already known and used as the anchor.
  2. It drew the terminal posterior mean as an unlabelled line and never plotted
     the verified TSJE outcome anchor (+3.70 pp) the retrodiction is read
     against — hiding the retrodiction-vs-truth relationship.

Closure invariant (static check on the canonical generator):
  1. A module-level ``TSJE_ANCHOR_PP = 3.70`` constant exists.
  2. The misleading phrase "Forecast Timeline" appears nowhere in the file
     (chart title and narrative heading both de-mislabelled).
  3. ``chart_c1`` draws the anchor from ``TSJE_ANCHOR_PP`` as a labelled
     "Verified ... anchor" reference line.
  4. ``chart_c1``'s title frames the panel as a "Retrodiction".
  5. ``chart_c1`` carries an on-chart disclosure that it is not a forward
     forecast.

This is a source-level invariant (no data dependency), matching F-053. The
canonical PNG is rebuilt from the fixed generator by ``make pipeline-full`` and
bound by F-050 lineage.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

GENERATOR = REPO_ROOT / "reports" / "eda" / "generate_eda.py"
MISLABEL = "Forecast Timeline"

_C1_BLOCK = re.compile(r'@safe_chart\("C1"\).*?(?=@safe_chart\("C2"\))', re.S)
_ANCHOR_CONST = re.compile(r"^TSJE_ANCHOR_PP\s*=\s*3\.70?\b", re.M)
_ANCHOR_LINE = re.compile(
    r'axhline\(\s*TSJE_ANCHOR_PP.*?label\s*=\s*f?"[^"]*[Vv]erified[^"]*anchor[^"]*"',
    re.S,
)
_TITLE = re.compile(r'set_title\(\s*"([^"]*)"')


def _source_gaps(src: str) -> list[str]:
    """File-level invariants: anchor constant present, mislabel absent."""
    gaps: list[str] = []
    if not _ANCHOR_CONST.search(src):
        gaps.append("no module-level 'TSJE_ANCHOR_PP = 3.70' constant")
    if MISLABEL in src:
        line = src.count("\n", 0, src.index(MISLABEL)) + 1
        gaps.append(f'misleading "{MISLABEL}" framing still present at line {line}')
    return gaps


def _block_gaps(src: str) -> list[str]:
    """chart_c1 invariants: anchor drawn + labelled, honest title, disclosure."""
    match = _C1_BLOCK.search(src)
    if not match:
        return ["could not locate the chart_c1 block"]
    block = match.group(0)
    gaps: list[str] = []
    if not _ANCHOR_LINE.search(block):
        gaps.append(
            "chart_c1 does not draw a labelled 'Verified ... anchor' line from TSJE_ANCHOR_PP"
        )
    title = _TITLE.search(block)
    if title is None or "Retrodiction" not in title.group(1):
        gaps.append("chart_c1 title does not frame the panel as a 'Retrodiction'")
    if "not a forward forecast" not in block.lower():
        gaps.append("chart_c1 missing the on-chart 'not a forward forecast' disclosure")
    return gaps


def main() -> int:
    if not GENERATOR.is_file():
        return gate("F-055", Path(__file__).name, False, "missing reports/eda/generate_eda.py")

    src = GENERATOR.read_text(encoding="utf-8")
    gaps = _source_gaps(src) + _block_gaps(src)
    detail = (
        "; ".join(gaps)
        if gaps
        else "C1 reads as a retrodiction with the verified outcome anchor drawn and labelled"
    )
    return gate("F-055", Path(__file__).name, not gaps, detail)


if __name__ == "__main__":
    sys.exit(main())
