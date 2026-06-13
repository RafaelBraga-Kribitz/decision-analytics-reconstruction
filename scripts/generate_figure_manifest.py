#!/usr/bin/env python3
"""Regenerate governance/FIGURE_MANIFEST.yaml from pipeline artifacts.

The manifest binds every committed PNG under reports/eda and reports/module_a
to the model run (data/processed/model_run_manifest.json) that produced the
data behind it. check_figure_artifact_lineage.py (F-050) verifies the binding;
this script is the only sanctioned writer — never edit the manifest by hand.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "governance" / "FIGURE_MANIFEST.yaml"
MODEL_MANIFEST = REPO_ROOT / "data" / "processed" / "model_run_manifest.json"
SEGMENT_LABELS = REPO_ROOT / "data" / "processed" / "segment_labels.parquet"
GENERATORS = {
    "eda": "reports/eda/generate_eda.py",
    "module_a": "module_a_population_segmentation/pipeline/export.py",
}
REPORT_DIRS = (
    REPO_ROOT / "reports" / "eda",
    REPO_ROOT / "reports" / "module_a",
)
CANONICAL_SAMPLE_SIZE = 50_000


def _segmentation_label_hash() -> str:
    import pandas as pd

    sl = pd.read_parquet(SEGMENT_LABELS)
    pairs = sl.drop_duplicates("segment_id")[["segment_id", "segment_label"]].sort_values(
        "segment_id"
    )
    payload = "|".join(f"{int(r.segment_id)}:{r.segment_label}" for r in pairs.itertuples())
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def main() -> int:
    model_doc = json.loads(MODEL_MANIFEST.read_text(encoding="utf-8"))
    git_commit = str(model_doc["git_commit"])

    figures = []
    for report_dir in REPORT_DIRS:
        generator = GENERATORS[report_dir.name]
        for png in sorted(report_dir.glob("*.png")):
            figures.append(
                {
                    "path": str(png.relative_to(REPO_ROOT)),
                    "generator": generator,
                    "save_name": png.name,
                }
            )

    manifest = {
        "run_id": git_commit[:12],
        "git_commit": git_commit,
        "generated_at": dt.date.today().isoformat(),
        "data_manifest": "data/processed/model_run_manifest.json",
        "canonical_sample_size": CANONICAL_SAMPLE_SIZE,
        "segmentation_label_hash": _segmentation_label_hash(),
        "figures": figures,
    }
    MANIFEST_PATH.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    print(
        f"[generate_figure_manifest] wrote {MANIFEST_PATH.relative_to(REPO_ROOT)} "
        f"({len(figures)} figures, run_id={git_commit[:12]})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
