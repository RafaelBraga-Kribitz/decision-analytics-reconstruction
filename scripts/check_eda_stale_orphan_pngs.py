#!/usr/bin/env python3
"""Verification script for F-046 (stale/orphan EDA PNGs).

Every PNG under reports/eda/ must be emitted by reports/eda/generate_eda.py
via save_fig(...) so committed charts cannot drift from pipeline outputs.
"""

from __future__ import annotations

import re
from pathlib import Path

from _governance_check import REPO_ROOT, gate

EDA_DIR = REPO_ROOT / "reports" / "eda"
GENERATOR = EDA_DIR / "generate_eda.py"


def _canonical_png_names(generator_src: str) -> set[str]:
    return set(re.findall(r'save_fig\(fig,\s*"([^"]+\.png)"\)', generator_src))


_OVERVIEW_CHART_RE = re.compile(
    r'@safe_chart\("OVERVIEW"\)\s*\n'
    r"def chart_eda_overview\(\):.*?save_fig\(fig, \"eda_overview.png\"\)",
    re.S,
)


def _overview_block(generator_src: str) -> str:
    m = _OVERVIEW_CHART_RE.search(generator_src)
    return m.group(0) if m else ""


def _overview_quality_gaps(block: str) -> list[str]:
    gaps: list[str] = []
    if not block:
        gaps.append("generate_eda.py missing chart_eda_overview")
        return gaps
    if "EMPIRICAL DATA OVERVIEW" not in block:
        gaps.append("eda_overview title must read EMPIRICAL DATA OVERVIEW")
    if "Model outputs: C1" not in block and "Model outputs: C1–C10" not in block:
        gaps.append("eda_overview must direct readers to C1–C10 for model outputs")
    banned = (
        "posterior_mean_preference_margin_pp",
        "win_probability_a",
        "shock_scale",
        "set_xlim(0.48, 0.52)",
        ".pie(",
    )
    for token in banned:
        if token in block:
            gaps.append(f"eda_overview must not include {token!r} (model/misleading panel)")
    return gaps


def main() -> int:
    gaps: list[str] = []

    if not GENERATOR.is_file():
        gaps.append("missing reports/eda/generate_eda.py")
        return gate("F-046", Path(__file__).name, False, "; ".join(gaps))

    gen_src = GENERATOR.read_text(encoding="utf-8")
    canonical = _canonical_png_names(gen_src)
    if not canonical:
        gaps.append("generate_eda.py declares no save_fig PNG outputs")

    gaps.extend(_overview_quality_gaps(_overview_block(gen_src)))

    for png in sorted(EDA_DIR.glob("*.png")):
        if png.name not in canonical:
            gaps.append(f"orphan PNG not emitted by generate_eda.py: {png.name}")

    for required in ("eda_overview.png", "C8_v2.png"):
        if required not in canonical:
            gaps.append(f"generate_eda.py must save_fig {required}")

    ok = not gaps
    detail = "; ".join(gaps) if gaps else "reports/eda PNGs match generate_eda.py manifest"
    return gate("F-046", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    raise SystemExit(main())
