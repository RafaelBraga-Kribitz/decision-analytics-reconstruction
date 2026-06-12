#!/usr/bin/env python3
"""Verification script for F-049 (EDA notebook vs canonical chart parity + E-10 drift).

ISSUE_TRIAGE_MASTER E-10: worst EDA plots not portfolio-grade. This script
gates structural drift between the canonical PNG generator and the notebook
builder (same Johnny Decimal IDs must describe the same estimand).

Known defect: build_notebook.py C2 plots MC shock_scale histogram while
generate_eda.py C2 plots final-day posterior margin + HDI.
"""

from __future__ import annotations

import re
from pathlib import Path

from _governance_check import REPO_ROOT, gate

GENERATOR = REPO_ROOT / "reports" / "eda" / "generate_eda.py"
NOTEBOOK_BUILDER = REPO_ROOT / "reports" / "eda" / "build_notebook.py"


def _extract_c2_notebook_block(src: str) -> str:
    m = re.search(r"# C2 —.*?(?=# C3 —|\Z)", src, re.S)
    return m.group(0) if m else ""


def _extract_c2_generator_block(src: str) -> str:
    m = re.search(r'@safe_chart\("C2"\).*?(?=@safe_chart\("C3"\)|\Z)', src, re.S)
    return m.group(0) if m else ""


def _check_c2_parity(gen_c2: str, nb_c2: str) -> list[str]:
    gaps: list[str] = []
    if "posterior_mean_preference_margin_pp" not in gen_c2:
        gaps.append("generate_eda C2 no longer plots posterior margin HDI")
    if "shock_scale" in nb_c2 and "posterior_mean_preference_margin_pp" not in nb_c2:
        gaps.append("build_notebook C2 still uses MC shock_scale instead of posterior margin")
    if "Histogram" in nb_c2 and "Final-Day Posterior Margin" in gen_c2:
        gaps.append("C2 chart type mismatch between notebook builder and PNG generator")
    return gaps


def _check_c8_layout(gen_full: str) -> list[str]:
    c8_block = re.search(r'@safe_chart\("C8"\).*?(?=@safe_chart\("C9"\)|\Z)', gen_full, re.S)
    if not c8_block:
        return []
    block = c8_block.group(0)
    if "_stagger_annotate" not in block:
        return ["generate_eda C8 missing staggered label placement"]
    return []


def main() -> int:
    if not GENERATOR.is_file() or not NOTEBOOK_BUILDER.is_file():
        return gate(
            "F-049",
            Path(__file__).name,
            False,
            "missing generate_eda.py or build_notebook.py",
        )

    gen_full = GENERATOR.read_text(encoding="utf-8")
    gen_c2 = _extract_c2_generator_block(gen_full)
    nb_c2 = _extract_c2_notebook_block(NOTEBOOK_BUILDER.read_text(encoding="utf-8"))
    gaps = _check_c2_parity(gen_c2, nb_c2) + _check_c8_layout(gen_full)

    ok = not gaps
    detail = (
        "; ".join(gaps) if gaps else "EDA notebook builder aligned with canonical chart definitions"
    )
    return gate("F-049", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    raise SystemExit(main())
