#!/usr/bin/env python3
"""Regenerate governance/FIGURE_MANIFEST.yaml from pipeline artifacts.

The manifest binds every committed PNG under reports/eda and reports/module_a
to the model run (data/processed/model_run_manifest.json) that produced the
data behind it. check_figure_artifact_lineage.py (F-050) verifies the binding;
this script is the only sanctioned writer — never edit the manifest by hand.

Schema (versioned read surface for external tooling, e.g. the
Chart_Audit_Framework cross-repo audit ratchet, IMP-F03):

* ``schema_version`` (int) — this script is the only writer, and the header
  comment it emits into the manifest is the bump policy of record. Additive,
  backward-compatible changes (a new optional top-level or per-figure field)
  do NOT bump ``schema_version``. It increments only for breaking changes:
  removing or renaming an existing key, changing an existing key's type or
  meaning, or removing/repointing a ``chart_id``.
* ``chart_id`` (per figure, str) — the stable external identifier for a
  chart, derived from the on-disk filename stem at the time the id was
  minted. chart_id is permanent once published: renaming what a chart shows
  means retiring its chart_id (dropping the entry) and adding a new one, never
  repointing an existing id at different content.
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

# Bumped only for breaking changes — see module docstring "Schema" section.
SCHEMA_VERSION = 1

# Prepended verbatim above the YAML body on every regeneration. This is the
# only sanctioned home for the consumer contract note; edit it here, never in
# the generated file, since the generator is the only sanctioned writer.
HEADER_COMMENT = f"""\
# governance/FIGURE_MANIFEST.yaml — GENERATED FILE. Do not hand-edit.
# Regenerate with: poetry run python scripts/generate_figure_manifest.py
# Verified by: scripts/check_figure_artifact_lineage.py (F-050)
#
# CONSUMER CONTRACT: external read-only tooling (e.g. the Chart_Audit_Framework
# cross-repo audit ratchet, spec IMP-F03) may rely on schema_version as a
# gate on parser compatibility (see the bump policy in
# scripts/generate_figure_manifest.py's module docstring), on each figure's
# chart_id as a permanent identifier that is never reused or repointed at
# different content once published (a rename retires the old chart_id and
# adds a new one), and on path, generator, and save_name as accurate as of
# the run named by run_id/git_commit; consumers must not rely on figure
# ordering or on any field not named above.
#
# schema_version bump policy: {SCHEMA_VERSION} is the current version.
# Additive, backward-compatible changes (new optional fields) do not bump
# schema_version. It increments only on breaking changes — removing or
# renaming an existing key, changing an existing key's type/meaning, or
# removing/repointing a chart_id.
"""


def _duplicate_chart_ids(figures: list[dict]) -> list[str]:
    """Return any chart_id values used by more than one figure entry."""
    chart_ids = [f["chart_id"] for f in figures]
    return sorted({cid for cid in chart_ids if chart_ids.count(cid) > 1})


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
                    "chart_id": png.stem,
                    "path": png.relative_to(REPO_ROOT).as_posix(),
                    "generator": generator,
                    "save_name": png.name,
                }
            )

    duplicates = _duplicate_chart_ids(figures)
    if duplicates:
        raise SystemExit(f"duplicate chart_id(s) — ids must be unique: {duplicates}")

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "run_id": git_commit[:12],
        "git_commit": git_commit,
        "generated_at": dt.date.today().isoformat(),
        "data_manifest": "data/processed/model_run_manifest.json",
        "canonical_sample_size": CANONICAL_SAMPLE_SIZE,
        "segmentation_label_hash": _segmentation_label_hash(),
        "figures": figures,
    }
    body = yaml.safe_dump(manifest, sort_keys=False)
    MANIFEST_PATH.write_text(HEADER_COMMENT + body, encoding="utf-8")
    print(
        f"[generate_figure_manifest] wrote {MANIFEST_PATH.relative_to(REPO_ROOT)} "
        f"(schema_version={SCHEMA_VERSION}, {len(figures)} figures, run_id={git_commit[:12]})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
