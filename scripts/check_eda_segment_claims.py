#!/usr/bin/env python3
"""Guard EDA segment-propensity narrative against pre-F-051/F-052 fabrications.

Issues #87 (narrative contradicts published charts) and #112 (stale wave/pollster
counts). F-051 fixed the segment-label inversion and F-052 established that
participation propensity is a near-uniform participation-likelihood score
(department std ~0.003, segment std ~0.02) — NOT a segment differentiator. The
canonical A4 heatmap / A5 violins therefore show every department x segment cell
inside a narrow ~0.50-0.70 band.

This is a STATIC narrative-sync gate (same family as check_numeric_ssot.py): it
scans BOTH the EDA generators (so a regeneration cannot re-emit the fabrications)
AND the committed rendered artifacts (.md / .ipynb, so a hand-edit cannot drift
either). It fails if any of the refuted claims reappear:

  * a segment asserted to be "the highest-propensity segment" / to have the
    "highest propensity" (self-refuting once propensity is flat);
  * fabricated A4/A5 extremes the charts refute — Rural Committed ">0.80"/">0.70",
    Committed Opposition "uniformly low propensity (<0.15)" / "near 0.10" /
    "mean propensity 0.10", or an "IQR 0.65-0.80" high cluster;
  * the stale "4 poll waves" / "four polling waves" / "all four pollsters"
    counts (the fixture carries 8 tracking waves; golden n_tracking_waves=8).

Run: poetry run python scripts/check_eda_segment_claims.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EDA = REPO_ROOT / "reports" / "eda"

# The generators (source of every claim) plus the committed rendered artifacts.
SCANNED_FILES: tuple[Path, ...] = (
    EDA / "generate_eda.py",
    EDA / "build_notebook.py",
    EDA / "eda_report.md",
    EDA / "strategic_brief.md",
    EDA / "paraguay_election_eda.ipynb",
)

# Each forbidden pattern is written so it matches ONLY the refuted pre-fix claim,
# never the corrected flat-band prose (which legitimately mentions, in negated
# form, "above 0.80" and "a low cluster near 0.10").
FORBIDDEN: tuple[tuple[str, re.Pattern[str]], ...] = (
    # --- #87: self-refuting "highest propensity" attributions -----------------
    ("highest_propensity_segment", re.compile(r"highest[- ]propensity segment", re.I)),
    ("highest_propensity_values_for", re.compile(r"highest propensity values for", re.I)),
    ("highest_propensity_distributions", re.compile(r"highest propensity distributions", re.I)),
    ("having_the_highest_propensity", re.compile(r"having the highest propensity", re.I)),
    ("highest_propensity_table_cell", re.compile(r"highest propensity \(0\.\d", re.I)),
    # --- #87: fabricated A4/A5 extremes the charts refute ---------------------
    ("committed_opp_uniformly_low", re.compile(r"uniformly low propensity", re.I)),
    ("rural_committed_over_080", re.compile(r"propensity >\s*0\.80")),
    ("rural_committed_over_070", re.compile(r"Rural Committed \(>\s*0\.70\)")),
    ("iqr_065_080_cluster", re.compile(r"IQR 0\.65")),
    ("committed_opp_near_010_across", re.compile(r"near 0\.10 across")),
    ("committed_opp_010_median", re.compile(r"~0\.10 median")),
    ("committed_opp_mean_010", re.compile(r"[Mm]ean propensity 0\.10")),
    ("rural_low_035_literal", re.compile(r"Propensity 0\.35\b")),
    # --- #112: stale tracking-wave / pollster counts --------------------------
    ("stale_4_poll_waves", re.compile(r"\b4 poll waves\b")),
    ("stale_four_poll_waves", re.compile(r"four poll(?:ing)? waves", re.I)),
    ("stale_all_four_pollsters", re.compile(r"all four pollsters", re.I)),
    # --- #154: residual narrative contradictions --------------------------------
    ("stale_rake_mean_32x", re.compile(r"mean 3\.2×")),
    ("highest_volume_segment", re.compile(r"highest-volume", re.I)),
    ("yv_high_variance_propensity", re.compile(r"High variance in Youth Volatile", re.I)),
    (
        "exit_intercept_tracks_tracking_mean",
        re.compile(r"anchors the exit model near the tracking final mean", re.I),
    ),
    ("safe_yield_high_propensity", re.compile(r"safe yield.*high propensity", re.I)),
)

# Positive anchors: the corrected framing must be present so the gate also fails
# if someone deletes the honest prose instead of restoring the fabrication.
REQUIRED: tuple[tuple[str, Path, re.Pattern[str]], ...] = (
    ("gen_wave_count_data_derived", EDA / "generate_eda.py", re.compile(r"_n_tracking_waves")),
    (
        "report_near_uniform",
        EDA / "eda_report.md",
        re.compile(r"near-uniform across all six segments", re.I),
    ),
    ("report_8_waves", EDA / "eda_report.md", re.compile(r"\b8 poll waves\b")),
    ("brief_8_waves", EDA / "strategic_brief.md", re.compile(r"\b8 poll waves\b")),
    ("notebook_8_waves", EDA / "paraguay_election_eda.ipynb", re.compile(r"Only 8 poll waves")),
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def main() -> int:
    gaps: list[str] = []

    for path in SCANNED_FILES:
        if not path.is_file():
            gaps.append(f"missing scanned file {path.relative_to(REPO_ROOT)}")
            continue
        text = _read(path)
        for label, pat in FORBIDDEN:
            if pat.search(text):
                gaps.append(f"{path.relative_to(REPO_ROOT)}: forbidden EDA claim [{label}]")

    for label, path, pat in REQUIRED:
        if not path.is_file():
            gaps.append(f"missing {path.relative_to(REPO_ROOT)} for anchor {label}")
        elif not pat.search(_read(path)):
            gaps.append(f"{path.relative_to(REPO_ROOT)} missing anchor [{label}]")

    if gaps:
        print("[FAIL] check_eda_segment_claims.py: " + "; ".join(gaps), file=sys.stderr)
        return 1
    print(
        "[PASS] check_eda_segment_claims.py: EDA segment-propensity narrative "
        "matches the flat-band charts; no stale wave/pollster counts"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
