#!/usr/bin/env python3
"""Verification script for F-023 (numeric SSOT enforcement in public docs)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

SSOT = REPO_ROOT / "reports" / "NUMERIC_SSOT.md"

# Files that must exist and cite canonical numbers (grep anchors).
ANCHOR_FILES: tuple[Path, ...] = (
    REPO_ROOT / "reports" / "NUMERIC_SSOT.md",
    REPO_ROOT / "reports" / "CASE_STUDY.md",
    REPO_ROOT / "README.md",
)

REQUIRED_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("ssot_50k", re.compile(r"50[,\s]?000")),
    ("ssot_14_weeks", re.compile(r"14\s+ISO\s+weeks|14-week|14 weeks", re.I)),
    ("ssot_18_week_scope", re.compile(r"18[- ]week", re.I)),
    ("ssot_margin", re.compile(r"\+3\.70\s*pp")),
    ("ssot_participation", re.compile(r"61\.25\s*%")),
    ("ssot_silhouette_gate", re.compile(r"0\.22")),
    ("ssot_brier_gate", re.compile(r"0\.237")),
    ("ssot_milp_lift", re.compile(r"54\.8|54\.77")),
)

FORBIDDEN_IN_PUBLIC: tuple[tuple[str, re.Pattern[str], tuple[Path, ...]], ...] = (
    (
        "wrong_18_week_only",
        re.compile(r"18-week execution|over 18 weeks|11 channel types over 18 weeks", re.I),
        (
            REPO_ROOT / "reports" / "CASE_STUDY.md",
            REPO_ROOT / "README.md",
        ),
    ),
    (
        "wrong_participation_636",
        re.compile(r"63\.6\s*%"),
        (
            REPO_ROOT / "reports" / "epistemic_boundaries.md",
            REPO_ROOT / "reports" / "CASE_STUDY.md",
        ),
    ),
    (
        "confidential_fiction",
        re.compile(
            r"CONFIDENTIAL\s*\|\s*For Campaign Director|Campaign Director Eyes Only",
            re.I,
        ),
        (
            REPO_ROOT / "reports" / "eda" / "strategic_brief.md",
            REPO_ROOT / "reports" / "eda" / "eda_report.md",
        ),
    ),
    (
        "causal_counterfactual",
        re.compile(r"underperformed the verified outcome by 2[–-]4", re.I),
        (
            REPO_ROOT / "reports" / "CASE_STUDY.md",
        ),
    ),
    (
        "forbidden_44m_budget",
        re.compile(r"\b44\s*(?:\.\d+)?\s*[mM]\b|\$?\s*44[,\s]?000[,\s]?000\b"),
        (
            REPO_ROOT / "reports" / "NUMERIC_SSOT.md",
            REPO_ROOT / "reports" / "CASE_STUDY.md",
            REPO_ROOT / "reports" / "epistemic_boundaries.md",
            REPO_ROOT / "module_b_resource_allocation" / "README.md",
            REPO_ROOT / "module_b_resource_allocation" / "config" / "budget_envelope.yaml",
        ),
    ),
    (
        "fiction_win_prob_79",
        re.compile(r">\s*79\s*%|exceeds\s+79\s*%|above\s+79\s*%", re.I),
        (
            REPO_ROOT / "reports" / "eda" / "strategic_brief.md",
            REPO_ROOT / "reports" / "eda" / "eda_report.md",
        ),
    ),
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def main() -> int:
    gaps: list[str] = []

    if not SSOT.is_file():
        gaps.append("missing reports/NUMERIC_SSOT.md")
    else:
        ssot_text = _read(SSOT)
        for label, pat in REQUIRED_PATTERNS:
            if not pat.search(ssot_text):
                gaps.append(f"NUMERIC_SSOT.md missing anchor {label}")

    for path in ANCHOR_FILES:
        if not path.is_file():
            gaps.append(f"missing anchor file {path.relative_to(REPO_ROOT)}")

    for label, pat, paths in FORBIDDEN_IN_PUBLIC:
        for path in paths:
            if path.is_file() and pat.search(_read(path)):
                gaps.append(f"{path.relative_to(REPO_ROOT)}: forbidden {label}")

    # SSOT doc must disclaim AUC circularity and 18-week program vs 14-week pipeline.
    if SSOT.is_file():
        ssot = _read(SSOT)
        if "Circular" not in ssot and "circular" not in ssot:
            gaps.append("NUMERIC_SSOT.md missing AUC circularity disclaimer")
        if not re.search(r"18[- ]week.*14", ssot, re.I | re.S):
            gaps.append("NUMERIC_SSOT.md missing 18-week scope vs 14-week pipeline framing")

    ok = not gaps
    return gate(
        "F-023",
        Path(__file__).name,
        ok,
        "; ".join(gaps) if gaps else "numeric SSOT anchors present, forbidden claims absent",
    )


if __name__ == "__main__":
    sys.exit(main())
