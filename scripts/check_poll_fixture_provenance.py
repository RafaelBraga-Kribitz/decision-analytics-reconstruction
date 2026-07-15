#!/usr/bin/env python3
"""Guard Module C poll-fixture provenance register (issue #92).

The epistemic register must not claim pollster names are verbatim when several
fixture labels are pseudonymized. Figures, dates, and outlet/carrier fields are
the externally checkable elements; pollster names are house-effect identifiers.

Run: poetry run python scripts/check_poll_fixture_provenance.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EPISTEMIC = REPO_ROOT / "reports" / "epistemic_boundaries.md"

# Positive anchors that must stay in the register.
REQUIRED_IN_EPISTEMIC: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "pollster_not_uniformly_verbatim",
        re.compile(r"Pollster names are.{0,24}uniformly verbatim", re.I | re.S),
    ),
    ("pseudonymized_disclaimer", re.compile(r"pseudonymized", re.I)),
    (
        "externally_checkable_carveout",
        re.compile(
            r"externally checkable elements.*outlet/carrier.*publication date.*published figures",
            re.I | re.S,
        ),
    ),
    ("mapping_table_anchor", re.compile(r"Fixture pollster label", re.I)),
    ("ati_snead_mapping", re.compile(r"Ati Snead.*ATI / Snead", re.I | re.S)),
)

# Blanket overclaims that imply every column — including pollster — is verbatim.
FORBIDDEN: tuple[tuple[str, re.Pattern[str], tuple[Path, ...]], ...] = (
    (
        "blanket_fixture_verbatim",
        re.compile(r"each fixture row.*verbatim", re.I | re.S),
        (EPISTEMIC, REPO_ROOT / "README.md", REPO_ROOT / "reports" / "VALIDATION.md"),
    ),
    (
        "tracking_measurement_sources_heading",
        re.compile(r"Tracking Measurement Sources", re.I),
        (EPISTEMIC,),
    ),
    (
        "survey_measurement_verbatim",
        re.compile(r"survey measurement.*verbatim", re.I | re.S),
        (EPISTEMIC, REPO_ROOT / "README.md", REPO_ROOT / "reports" / "VALIDATION.md"),
    ),
    (
        "pollster_names_verbatim",
        re.compile(r"pollster names are verbatim", re.I),
        (EPISTEMIC, REPO_ROOT / "README.md", REPO_ROOT / "reports" / "VALIDATION.md"),
    ),
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def main() -> int:
    gaps: list[str] = []

    if not EPISTEMIC.is_file():
        gaps.append(f"missing {EPISTEMIC.relative_to(REPO_ROOT)}")
    else:
        text = _read(EPISTEMIC)
        for label, pat in REQUIRED_IN_EPISTEMIC:
            if not pat.search(text):
                gaps.append(
                    f"{EPISTEMIC.relative_to(REPO_ROOT)}: missing anchor {label}"
                )

    for label, pat, paths in FORBIDDEN:
        for path in paths:
            if path.is_file() and pat.search(_read(path)):
                gaps.append(f"{path.relative_to(REPO_ROOT)}: forbidden {label}")

    if gaps:
        print("[FAIL] check_poll_fixture_provenance.py:\n" + "\n".join(gaps))
        return 1

    print("[PASS] check_poll_fixture_provenance.py: poll fixture provenance register OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
