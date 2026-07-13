#!/usr/bin/env python3
"""Fail CI if the dropped euphemism layer reappears in public-facing markdown.

Issue #99 (owner-binding): the domain is named plainly — "Paraguay 2018
presidential election" — and the euphemism layer (entity / participation rate /
preference proxy / outcome event / survey measurement / program-as-campaign) is
dropped everywhere reader-facing. This gate enforces one consistent vocabulary by
banning REINTRODUCTION of those euphemism phrases in public prose (the plain
words voter / turnout / poll / campaign are now the required vocabulary, never
banned). Stable code identifiers (`entity_id`, `preference_proxy_*`,
`participation_propensity.parquet`, ...) are untouched — the patterns match the
euphemism *phrases* in prose, not identifier tokens.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("euphemism_outcome_event", re.compile(r"outcome event", re.I)),
    ("euphemism_survey_measurement", re.compile(r"survey measurement", re.I)),
    ("euphemism_tracking_measurement", re.compile(r"tracking measurement", re.I)),
    ("euphemism_participation_rate", re.compile(r"participation rate", re.I)),
    ("euphemism_preference_proxy", re.compile(r"(?<!vote-)preference proxy", re.I)),
    ("euphemism_program_collocation", re.compile(r"program (?:window|phase|days?|scope)", re.I)),
)

# Positive anchor: the domain must stay named plainly in the terminology-defining doc.
DOMAIN_ANCHOR_FILE = ROOT / "reports" / "epistemic_boundaries.md"
DOMAIN_ANCHOR_PATTERN = re.compile(r"Paraguay 2018 presidential election", re.I)

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

    if not DOMAIN_ANCHOR_FILE.is_file():
        bad.append(f"{DOMAIN_ANCHOR_FILE.relative_to(ROOT)}: domain_anchor_missing_file")
    elif not DOMAIN_ANCHOR_PATTERN.search(
        DOMAIN_ANCHOR_FILE.read_text(encoding="utf-8", errors="replace")
    ):
        bad.append(
            f"{DOMAIN_ANCHOR_FILE.relative_to(ROOT)}: domain_not_named_plainly "
            "(expected 'Paraguay 2018 presidential election')"
        )

    if bad:
        print("Terminology check FAILED:\n" + "\n".join(bad))
        return 1
    print("Terminology check OK (plain vocabulary enforced; domain named).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
