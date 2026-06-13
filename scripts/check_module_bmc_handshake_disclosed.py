#!/usr/bin/env python3
"""Verification script for F-065: B→C contact handshake scenario-invariance disclosed.

ISSUE_TRIAGE_MASTER row: AUD-BMC (severity reject).
alloc_mean_contacts is a single scalar passed identically to all MC draws,
so contacts are scenario-invariant. Without disclosure, readers assume
contact volume differs per scenario.

Closure invariant (static check on reports/eda/generate_eda.py):
  - "alloc_mean_persuasion_contacts" appears in C5 block
  - "scenario-invariant" appears in C5 block
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

GENERATOR = REPO_ROOT / "reports" / "eda" / "generate_eda.py"
_C5 = re.compile(r'@safe_chart\("C5"\).*?(?=@safe_chart\("C6"\))', re.S)


def _bmc_gaps(block: str) -> list[str]:
    gaps: list[str] = []
    if "alloc_mean_persuasion_contacts" not in block:
        gaps.append("C5 does not reference alloc_mean_persuasion_contacts")
    if "scenario-invariant" not in block:
        gaps.append("C5 does not disclose scenario-invariant contact volume")
    return gaps


def main() -> int:
    if not GENERATOR.is_file():
        return gate("F-065", Path(__file__).name, False, "missing reports/eda/generate_eda.py")
    src = GENERATOR.read_text(encoding="utf-8")
    c5 = _C5.search(src)
    gaps: list[str] = []
    gaps += _bmc_gaps(c5.group(0)) if c5 else ["could not locate chart_c5 block"]
    detail = (
        "; ".join(gaps)
        if gaps
        else "C5 discloses B→C handshake: alloc_mean_persuasion_contacts is scenario-invariant"
    )
    return gate("F-065", Path(__file__).name, not gaps, detail)


if __name__ == "__main__":
    sys.exit(main())
