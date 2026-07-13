#!/usr/bin/env python3
"""Verification script for F-023 (numeric SSOT enforcement in public docs)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

SSOT = REPO_ROOT / "reports" / "NUMERIC_SSOT.md"
CASE_STUDY = REPO_ROOT / "reports" / "CASE_STUDY.md"
VALIDATION = REPO_ROOT / "reports" / "VALIDATION.md"
MODEL_CARD_PROPENSITY = (
    REPO_ROOT / "module_a_population_segmentation" / "reports" / "model_card_propensity.md"
)
MODEL_CARD_SEGMENTATION = (
    REPO_ROOT / "module_a_population_segmentation" / "reports" / "model_card_segmentation.md"
)
MODULE_A_README = REPO_ROOT / "module_a_population_segmentation" / "README.md"
MODULE_B_README = REPO_ROOT / "module_b_resource_allocation" / "README.md"
MODULE_C_README = REPO_ROOT / "module_c_forecasting_scenarios" / "README.md"

# Files that must exist and cite canonical numbers (grep anchors).
ANCHOR_FILES: tuple[Path, ...] = (
    REPO_ROOT / "reports" / "NUMERIC_SSOT.md",
    CASE_STUDY,
    REPO_ROOT / "README.md",
    # Model cards + module READMEs added for issue #91: they carry Module A/C
    # headline metrics and must not drift away from the SSOT table.
    MODEL_CARD_PROPENSITY,
    MODEL_CARD_SEGMENTATION,
    MODULE_A_README,
    MODULE_B_README,
    MODULE_C_README,
)

# Canonical metric anchors that MUST be present in a specific file. This is the
# positive half of the drift guard (issue #91): the model cards and the SSOT must
# keep citing the artifact-backed Module A/C figures with their run config, so a
# silent value change fails CI. Values are corroborated by the model cards,
# `config/model_params.yaml`, `reports/module_a/k_sweep_2026-07-09.md`, and a
# seed-42 50k pipeline run (`data/processed/model_run_manifest.json`).
REQUIRED_IN_FILE: tuple[tuple[str, Path, re.Pattern[str]], ...] = (
    # Propensity model card: Brier + circular AUC at the 15k holdout run.
    ("card_brier_15k", MODEL_CARD_PROPENSITY, re.compile(r"0\.1185")),
    ("card_auc_circular", MODEL_CARD_PROPENSITY, re.compile(r"0\.89")),
    ("card_run_config_15k", MODEL_CARD_PROPENSITY, re.compile(r"n=15k", re.I)),
    # Segmentation model card: silhouette + canonical bootstrap ARI at the 50k run.
    ("card_silhouette_50k", MODEL_CARD_SEGMENTATION, re.compile(r"0\.2562")),
    ("card_ari_50k", MODEL_CARD_SEGMENTATION, re.compile(r"0\.4304")),
    # SSOT must carry the same canonical Module A figures + tracking-wave count.
    ("ssot_brier_canonical", SSOT, re.compile(r"0\.1185")),
    ("ssot_ari_gate", SSOT, re.compile(r"0\.40")),
    ("ssot_tracking_waves", SSOT, re.compile(r"n_tracking_waves=8")),
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
        (REPO_ROOT / "reports" / "CASE_STUDY.md",),
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
    # --- issue #98: forbidden confidence register in the EDA brief -------------
    # The outputs are ILLUSTRATIVE (see epistemic_boundaries.md); certainty
    # language ("with high confidence", "under virtually all scenarios") over an
    # illustrative fixture posterior is exactly the register violation #98 fixed.
    # Scan both the committed brief/report AND the generator that emits them, so a
    # regeneration cannot re-introduce the phrasing.
    (
        "brief_high_confidence",
        re.compile(r"with high confidence", re.I),
        (
            REPO_ROOT / "reports" / "eda" / "strategic_brief.md",
            REPO_ROOT / "reports" / "eda" / "eda_report.md",
            REPO_ROOT / "reports" / "eda" / "generate_eda.py",
        ),
    ),
    (
        "brief_virtually_all_scenarios",
        re.compile(r"under virtually all scenarios", re.I),
        (
            REPO_ROOT / "reports" / "eda" / "strategic_brief.md",
            REPO_ROOT / "reports" / "eda" / "eda_report.md",
            REPO_ROOT / "reports" / "eda" / "generate_eda.py",
        ),
    ),
    # --- issue #91: stale Module A / Module C metric values ---------------------
    # These figures were superseded by the model cards + a seed-42 pipeline run.
    # Reappearance in any SSOT-family doc, model card, or module README signals the
    # exact drift class #91 fixed (SSOT contradicting the model card).
    (
        "stale_brier_071",
        re.compile(r"\b0\.071(?!\d)"),
        (SSOT, VALIDATION, CASE_STUDY, MODEL_CARD_PROPENSITY, MODULE_A_README),
    ),
    (
        "stale_auc_9679",
        re.compile(r"0\.9679"),
        (SSOT, VALIDATION, CASE_STUDY, MODEL_CARD_PROPENSITY, MODULE_A_README),
    ),
    (
        "stale_bootstrap_ari_7615",
        re.compile(r"0\.7615"),
        (SSOT, VALIDATION, CASE_STUDY, MODEL_CARD_SEGMENTATION, MODULE_A_README),
    ),
    (
        "stale_ari_gate_over_070",
        re.compile(r"ARI\s*[>≥]\s*0\.7[0-9]"),
        (SSOT, VALIDATION, CASE_STUDY, MODEL_CARD_SEGMENTATION, MODULE_A_README),
    ),
    (
        "stale_divergences_14",
        re.compile(r"14\s+(?:measured\b|divergenc)", re.I),
        (SSOT, VALIDATION, CASE_STUDY, MODULE_C_README),
    ),
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _ssot_anchor_gaps(ssot_text: str) -> list[str]:
    gaps: list[str] = []
    for label, pat in REQUIRED_PATTERNS:
        if not pat.search(ssot_text):
            gaps.append(f"NUMERIC_SSOT.md missing anchor {label}")
    return gaps


def _missing_anchor_files() -> list[str]:
    return [
        f"missing anchor file {path.relative_to(REPO_ROOT)}"
        for path in ANCHOR_FILES
        if not path.is_file()
    ]


def _forbidden_claim_gaps() -> list[str]:
    gaps: list[str] = []
    for label, pat, paths in FORBIDDEN_IN_PUBLIC:
        for path in paths:
            if path.is_file() and pat.search(_read(path)):
                gaps.append(f"{path.relative_to(REPO_ROOT)}: forbidden {label}")
    return gaps


def _required_in_file_gaps() -> list[str]:
    gaps: list[str] = []
    for label, path, pat in REQUIRED_IN_FILE:
        if not path.is_file():
            gaps.append(f"missing {path.relative_to(REPO_ROOT)} for anchor {label}")
        elif not pat.search(_read(path)):
            gaps.append(f"{path.relative_to(REPO_ROOT)} missing anchor {label}")
    return gaps


def _ssot_disclaimer_gaps(ssot_text: str) -> list[str]:
    gaps: list[str] = []
    if "Circular" not in ssot_text and "circular" not in ssot_text:
        gaps.append("NUMERIC_SSOT.md missing AUC circularity disclaimer")
    if not re.search(r"18[- ]week.*14", ssot_text, re.I | re.S):
        gaps.append("NUMERIC_SSOT.md missing 18-week scope vs 14-week pipeline framing")
    return gaps


def main() -> int:
    gaps: list[str] = []

    if not SSOT.is_file():
        gaps.append("missing reports/NUMERIC_SSOT.md")
    else:
        ssot_text = _read(SSOT)
        gaps.extend(_ssot_anchor_gaps(ssot_text))
        gaps.extend(_ssot_disclaimer_gaps(ssot_text))

    gaps.extend(_missing_anchor_files())
    gaps.extend(_forbidden_claim_gaps())
    gaps.extend(_required_in_file_gaps())

    ok = not gaps
    return gate(
        "F-023",
        Path(__file__).name,
        ok,
        "; ".join(gaps) if gaps else "numeric SSOT anchors present, forbidden claims absent",
    )


if __name__ == "__main__":
    sys.exit(main())
