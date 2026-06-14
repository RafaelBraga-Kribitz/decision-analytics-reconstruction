#!/usr/bin/env python3
"""Verification script for F-067: Dashboard QA tab resolves the latest report.

ISSUE_TRIAGE_MASTER row: AUD-PUB-001 (severity reject).
The Streamlit QA tab hard-coded ``qa_report_20260507.md``. The cleaning pipeline
(cleaner.py:_write_qa_report) emits ``qa_report_<YYYYMMDD>.md`` with a *fresh*
date every run, and the file is a gitignored generated artefact — so the
hard-coded date never matched a freshly-generated report and the tab was always
empty.

Closure invariant (static check on streamlit_dashboard.py):
  - no hard-coded ``qa_report_20260507.md`` literal remains
  - the QA tab globs ``qa_report_*.md`` and selects the latest

Source-level invariant (no data dependency), matching F-053 / F-055. Note we do
NOT assert the report file exists on disk: it is gitignored and only present
after the cleaning pipeline runs, so the honest fix is the glob, not a committed
artefact.
"""

from __future__ import annotations

import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

DASHBOARD = REPO_ROOT / "module_a_population_segmentation" / "app" / "streamlit_dashboard.py"


def _dashboard_gaps(src: str) -> list[str]:
    gaps: list[str] = []
    if "qa_report_20260507.md" in src:
        gaps.append("QA tab still hard-codes the stale qa_report_20260507.md date")
    if 'glob("qa_report_*.md")' not in src:
        gaps.append("QA tab does not glob qa_report_*.md for the latest report")
    return gaps


def main() -> int:
    if not DASHBOARD.is_file():
        return gate("F-067", Path(__file__).name, False, "missing streamlit_dashboard.py")
    src = DASHBOARD.read_text(encoding="utf-8")
    gaps = _dashboard_gaps(src)
    detail = (
        "; ".join(gaps)
        if gaps
        else "QA tab globs qa_report_*.md for the latest report; no stale hard-coded date"
    )
    return gate("F-067", Path(__file__).name, not gaps, detail)


if __name__ == "__main__":
    sys.exit(main())
