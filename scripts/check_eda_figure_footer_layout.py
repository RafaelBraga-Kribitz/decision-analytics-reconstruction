#!/usr/bin/env python3
"""Verification script for F-057: shared finalize_figure helper in EDA generator."""

from __future__ import annotations

from pathlib import Path

from _governance_check import REPO_ROOT, gate

GEN = REPO_ROOT / "reports" / "eda" / "generate_eda.py"


def main() -> int:
    gaps: list[str] = []
    src = GEN.read_text(encoding="utf-8")
    if "def finalize_figure" not in src:
        gaps.append("generate_eda.py missing finalize_figure helper")
    if "annotate_source(ax, *, y:" not in src and "footer_y" not in src:
        gaps.append("annotate_source missing configurable footer offset")
    if "finalize_figure(" not in src:
        gaps.append("no chart calls finalize_figure yet")

    ok = not gaps
    detail = "; ".join(gaps) if gaps else "finalize_figure helper present and used"
    return gate("F-057", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    raise SystemExit(main())
