#!/usr/bin/env python3
"""Verification script for F-048 (EDA battleground charts lack illustrative disclosure).

F-045 closed labeling in epistemic_boundaries.md and geo/heatmap.py. Static EDA
charts C3 and C8 still use full red/blue battleground framing without an
in-chart subtitle that the department mapping is synthetic/illustrative.
"""

from __future__ import annotations

import re
from pathlib import Path

from _governance_check import REPO_ROOT, gate

GENERATOR = REPO_ROOT / "reports" / "eda" / "generate_eda.py"
NOTEBOOK_BUILDER = REPO_ROOT / "reports" / "eda" / "build_notebook.py"

REQUIRED_MARKERS = ("illustrative", "synthetic mapping", "synthetic")


def _chart_block(src: str, chart_id: str) -> str:
    m = re.search(rf'@safe_chart\("{chart_id}"\).*?(?=@safe_chart|\Z)', src, re.S)
    return m.group(0) if m else ""


def _notebook_c3_c8_s4_blocks(src: str) -> list[str]:
    blocks: list[str] = []
    for cid in ("C3", "C8", "S4"):
        m = re.search(rf"# {cid} —.*?(?=# [A-Z]\d+ —|\Z)", src, re.S)
        if m:
            blocks.append(m.group(0))
    return blocks


def _has_disclosure(text: str) -> bool:
    lower = text.lower()
    return any(marker in lower for marker in REQUIRED_MARKERS)


def main() -> int:
    gaps: list[str] = []

    if not GENERATOR.is_file():
        gaps.append("missing generate_eda.py")
    else:
        gen = GENERATOR.read_text(encoding="utf-8")
        for cid in ("C3", "C8", "S4"):
            block = _chart_block(gen, cid)
            if block and not _has_disclosure(block):
                gaps.append(
                    f"generate_eda.py chart {cid} title/subtitle missing illustrative disclosure"
                )

    if NOTEBOOK_BUILDER.is_file():
        nb = NOTEBOOK_BUILDER.read_text(encoding="utf-8")
        for block in _notebook_c3_c8_s4_blocks(nb):
            if not _has_disclosure(block):
                label = block.splitlines()[0].strip("# ").split("—")[0].strip()
                gaps.append(f"build_notebook.py {label} missing illustrative disclosure")

    ok = not gaps
    detail = "; ".join(gaps) if gaps else "EDA battleground charts disclose illustrative mapping"
    return gate("F-048", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    raise SystemExit(main())
