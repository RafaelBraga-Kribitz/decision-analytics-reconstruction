#!/usr/bin/env python3
"""Fail CI if banned portfolio tokens appear in public-facing markdown."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("election_date_token", re.compile(r"\belection_date\b", re.I)),
    ("voter_token", re.compile(r"\bvoters?\b", re.I)),
)

SCAN_DIRS = [
    ROOT / "README.md",
    ROOT / "ARCHITECTURE.md",
    ROOT / "reports",
    ROOT / "module_a_population_segmentation" / "reports",
    ROOT / "module_b_resource_allocation" / "reports",
]


def _iter_files() -> list[Path]:
    out: list[Path] = []
    for p in SCAN_DIRS:
        if p.is_file():
            out.append(p)
        elif p.is_dir():
            out.extend(sorted(p.rglob("*.md")))
    return out


def main() -> int:
    bad: list[str] = []
    for path in _iter_files():
        if "pre_public_cleanup" in str(path) or "ai_harness" in str(path):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for label, pat in PATTERNS:
            if pat.search(text):
                bad.append(f"{path.relative_to(ROOT)}: matched {label}")
    if bad:
        print("Terminology check FAILED:\n" + "\n".join(bad))
        return 1
    print("Terminology check OK (sample patterns).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
