#!/usr/bin/env python3
"""Verification script for F-041 (terminology compliance in public markdown)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

# Scope master §12 — sample high-signal banned tokens in public prose.
PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("election_date_token", re.compile(r"\belection_date\b", re.I)),
    ("voter_token", re.compile(r"\bvoters?\b", re.I)),
    ("turnout_token", re.compile(r"\bturnout\b", re.I)),
    ("poll_token", re.compile(r"\bpolls?\b", re.I)),
    ("campaign_token", re.compile(r"\bcampaign\b", re.I)),
)

SCAN_PATHS: tuple[Path, ...] = (
    REPO_ROOT / "README.md",
    REPO_ROOT / "ARCHITECTURE.md",
    REPO_ROOT / "PROJECT_CHARTER.md",
    REPO_ROOT / "CONTRIBUTING.md",
    REPO_ROOT / "reports" / "CASE_STUDY.md",
    REPO_ROOT / "reports" / "NUMERIC_SSOT.md",
    REPO_ROOT / "reports" / "epistemic_boundaries.md",
    REPO_ROOT / "reports" / "VALIDATION.md",
    REPO_ROOT / "module_a_population_segmentation" / "README.md",
    REPO_ROOT / "module_b_resource_allocation" / "README.md",
    REPO_ROOT / "module_c_forecasting_scenarios" / "README.md",
)

SKIP_SUBSTRINGS = ("maintainer/", "pre_public_cleanup", "ai_harness", "archive/")


def _iter_files() -> list[Path]:
    out: list[Path] = []
    for p in SCAN_PATHS:
        if p.is_file():
            out.append(p)
        elif p.is_dir():
            out.extend(sorted(p.rglob("*.md")))
    return out


def main() -> int:
    bad: list[str] = []
    for path in _iter_files():
        rel = path.relative_to(REPO_ROOT).as_posix()
        if any(s in rel for s in SKIP_SUBSTRINGS):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(text.splitlines(), start=1):
            for name, pattern in PATTERNS:
                if pattern.search(line):
                    bad.append(f"{rel}:{line_no} [{name}] {line.strip()[:120]}")
    ok = not bad
    detail = "; ".join(bad[:8]) if bad else "no banned tokens in scoped public docs"
    if bad and len(bad) > 8:
        detail += f" (+{len(bad) - 8} more)"
    return gate("F-041", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    sys.exit(main())
