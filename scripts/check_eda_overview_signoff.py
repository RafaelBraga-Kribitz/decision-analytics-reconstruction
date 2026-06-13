#!/usr/bin/env python3
"""Verification script for F-073: eda_overview layout sign-off after pipeline fixes."""

from __future__ import annotations

from pathlib import Path

from _governance_check import REPO_ROOT, gate

OVERVIEW = REPO_ROOT / "reports" / "eda" / "eda_overview.png"
GEN = REPO_ROOT / "reports" / "eda" / "generate_eda.py"


def main() -> int:
    gaps: list[str] = []
    if not OVERVIEW.is_file():
        gaps.append("missing reports/eda/eda_overview.png — regenerate generate_eda.py")
    if "forecast_filtered" not in GEN.read_text(encoding="utf-8"):
        gaps.append("generate_eda missing filtered forecast load for C1")

    ok = not gaps
    detail = (
        "; ".join(gaps) if gaps else "eda_overview present; C1 uses filtered track when available"
    )
    return gate("F-073", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    raise SystemExit(main())
