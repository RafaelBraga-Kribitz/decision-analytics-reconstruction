#!/usr/bin/env python3
"""Verification script for F-041 (terminology compliance in public markdown)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

# Issue #99 — the owner-binding decision: name the domain (Paraguay 2018
# presidential election) plainly and DROP the euphemism layer. The reader-facing
# vocabulary is now plain (voter / turnout / poll / campaign / vote-preference /
# the 2018 election); the synthetic-microdata disclosures are unchanged. This gate
# keeps one consistent, enforced vocabulary — it now forbids REINTRODUCING the
# euphemisms (never the plain words) in the flagship public docs, and it requires
# the domain to be named plainly (positive anchor below).
#
# NOTE: only reader-facing PROSE is scanned (markdown). Stable code identifiers are
# untouched by design — `entity_id`, `participation_propensity.parquet`,
# `preference_proxy_*`, etc. remain, so the ban patterns below match the euphemism
# *phrases* in prose, not the identifier tokens (e.g. `preference proxy` the phrase,
# not the `preference_proxy` column, and the bare form is allowed inside the plain
# `vote-preference proxy`).
PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("euphemism_outcome_event", re.compile(r"outcome event", re.I)),
    ("euphemism_survey_measurement", re.compile(r"survey measurement", re.I)),
    ("euphemism_tracking_measurement", re.compile(r"tracking measurement", re.I)),
    ("euphemism_participation_rate", re.compile(r"participation rate", re.I)),
    ("euphemism_preference_proxy", re.compile(r"(?<!vote-)preference proxy", re.I)),
    ("euphemism_program_collocation", re.compile(r"program (?:window|phase|days?|scope)", re.I)),
)

# Positive anchor: the domain must be named plainly in the terminology-defining
# doc, so dropping the euphemism layer can never regress into an unnamed domain.
DOMAIN_ANCHOR: tuple[Path, re.Pattern[str]] = (
    REPO_ROOT / "reports" / "epistemic_boundaries.md",
    re.compile(r"Paraguay 2018 presidential election", re.I),
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

    anchor_path, anchor_pat = DOMAIN_ANCHOR
    anchor_rel = anchor_path.relative_to(REPO_ROOT).as_posix()
    if not anchor_path.is_file():
        bad.append(f"{anchor_rel} [domain_anchor_missing_file]")
    elif not anchor_pat.search(anchor_path.read_text(encoding="utf-8", errors="replace")):
        bad.append(
            f"{anchor_rel} [domain_not_named_plainly] "
            "expected 'Paraguay 2018 presidential election'"
        )

    ok = not bad
    detail = (
        "; ".join(bad[:8]) if bad else "plain vocabulary enforced; euphemisms absent; domain named"
    )
    if bad and len(bad) > 8:
        detail += f" (+{len(bad) - 8} more)"
    return gate("F-041", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    sys.exit(main())
