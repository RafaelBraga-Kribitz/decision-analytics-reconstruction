#!/usr/bin/env python3
"""Verification script for F-050: canonical figure + data artifact lineage.

Ensures committed chart PNGs are registered in governance/FIGURE_MANIFEST.yaml,
bound to data/processed/model_run_manifest.json, and that public-facing Module A
surfaces consume the same canonical parquet bundle (not live rebuilds at
arbitrary sample sizes).
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml
from _governance_check import REPO_ROOT, gate

MANIFEST_PATH = REPO_ROOT / "governance" / "FIGURE_MANIFEST.yaml"
MODEL_MANIFEST = REPO_ROOT / "data" / "processed" / "model_run_manifest.json"
EDA_GENERATOR = REPO_ROOT / "reports" / "eda" / "generate_eda.py"
STREAMLIT_APP = REPO_ROOT / "module_a_population_segmentation" / "app" / "streamlit_dashboard.py"
SEGMENT_LABELS = REPO_ROOT / "data" / "processed" / "segment_labels.parquet"
REPORT_DIRS = (
    REPO_ROOT / "reports" / "eda",
    REPO_ROOT / "reports" / "module_a",
)


def _segmentation_label_hash() -> str | None:
    if not SEGMENT_LABELS.is_file():
        return None
    import pandas as pd

    sl = pd.read_parquet(SEGMENT_LABELS)
    pairs = sl.drop_duplicates("segment_id")[["segment_id", "segment_label"]].sort_values(
        "segment_id"
    )
    payload = "|".join(f"{int(r.segment_id)}:{r.segment_label}" for r in pairs.itertuples())
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _canonical_save_fig_names() -> set[str]:
    if not EDA_GENERATOR.is_file():
        return set()
    src = EDA_GENERATOR.read_text(encoding="utf-8")
    return set(re.findall(r'save_fig\(fig,\s*"([^"]+\.png)"\)', src))


def _collect_committed_pngs() -> list[Path]:
    on_disk: list[Path] = []
    for report_dir in REPORT_DIRS:
        if report_dir.is_dir():
            on_disk.extend(sorted(report_dir.glob("*.png")))
    return on_disk


def _manifest_header_gaps(manifest: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    for key in ("run_id", "git_commit", "data_manifest", "segmentation_label_hash", "figures"):
        if key not in manifest:
            gaps.append(f"FIGURE_MANIFEST.yaml missing required key: {key}")
    return gaps


def _model_manifest_gaps(manifest: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    if not MODEL_MANIFEST.is_file():
        gaps.append("missing data/processed/model_run_manifest.json")
        return gaps
    model_doc = json.loads(MODEL_MANIFEST.read_text(encoding="utf-8"))
    model_commit = model_doc.get("git_commit")
    if manifest.get("git_commit") != model_commit:
        gaps.append("FIGURE_MANIFEST git_commit does not match model_run_manifest.json")
    if manifest.get("run_id") != str(model_commit or "")[:12]:
        gaps.append("FIGURE_MANIFEST run_id must equal first 12 chars of git_commit")
    return gaps


def _segmentation_hash_gaps(manifest: dict[str, Any]) -> list[str]:
    expected_hash = _segmentation_label_hash()
    if expected_hash is None:
        return ["missing data/processed/segment_labels.parquet for hash check"]
    if manifest.get("segmentation_label_hash") != expected_hash:
        return [
            f"segmentation_label_hash drift (manifest vs parquet): "
            f"{manifest.get('segmentation_label_hash')} != {expected_hash}"
        ]
    return []


def _png_registration_gaps(manifest: dict[str, Any], on_disk: list[Path]) -> list[str]:
    gaps: list[str] = []
    listed_paths = {
        str((REPO_ROOT / entry["path"]).resolve())
        for entry in manifest.get("figures", [])
        if isinstance(entry, dict) and entry.get("path")
    }
    canonical = _canonical_save_fig_names()
    for png in on_disk:
        if str(png.resolve()) not in listed_paths:
            gaps.append(f"unregistered committed PNG: {png.relative_to(REPO_ROOT)}")
        if png.parent.name == "eda" and png.name not in canonical:
            gaps.append(f"orphan EDA PNG not emitted by generate_eda.py: {png.name}")
    return gaps


def _surface_binding_gaps() -> list[str]:
    gaps: list[str] = []
    if EDA_GENERATOR.is_file():
        src = EDA_GENERATOR.read_text(encoding="utf-8")
        has_parquet = (
            'population_master_clean.parquet"' in src or "population_master_clean.parquet" in src
        )
        if not has_parquet:
            gaps.append("generate_eda.py must read data/processed/population_master_clean.parquet")
    else:
        gaps.append("missing reports/eda/generate_eda.py")

    if STREAMLIT_APP.is_file():
        dash = STREAMLIT_APP.read_text(encoding="utf-8")
        if "population_master_clean.parquet" not in dash:
            gaps.append(
                "streamlit_dashboard.py must load canonical data/processed/"
                "population_master_clean.parquet (not live-only rebuilds)"
            )
    else:
        gaps.append("missing module_a_population_segmentation/app/streamlit_dashboard.py")
    return gaps


def main() -> int:
    if not MANIFEST_PATH.is_file():
        return gate("F-050", Path(__file__).name, False, "missing governance/FIGURE_MANIFEST.yaml")

    manifest = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8")) or {}
    on_disk = _collect_committed_pngs()
    gaps = [
        *_manifest_header_gaps(manifest),
        *_model_manifest_gaps(manifest),
        *_segmentation_hash_gaps(manifest),
        *_png_registration_gaps(manifest, on_disk),
        *_surface_binding_gaps(),
    ]

    ok = not gaps
    detail = (
        "; ".join(gaps)
        if gaps
        else (f"FIGURE_MANIFEST binds {len(on_disk)} PNGs to run_id={manifest.get('run_id')}")
    )
    return gate("F-050", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    raise SystemExit(main())
