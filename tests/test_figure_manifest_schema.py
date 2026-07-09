"""Schema-version contract for governance/FIGURE_MANIFEST.yaml (issue #71 /
IMP-F03 companion).

The manifest is a versioned read surface for external, read-only tooling
(the Chart_Audit_Framework cross-repo audit ratchet). This test regenerates
the manifest with its sanctioned writer (scripts/generate_figure_manifest.py)
and parses the result back, asserting:

* ``schema_version`` is present and matches the generator's own constant.
* every figure entry carries a stable, unique ``chart_id``.
* the generated header still carries the consumer-contract paragraph and
  the bump policy, since those are hand-authored strings duplicated nowhere
  else — a future edit could silently drop them.

scripts/check_figure_artifact_lineage.py (F-050) already re-verifies the
manifest's lineage-and-registration invariants on every PR; this test only
covers the schema-version surface added for issue #71 and does not
duplicate F-050's checks.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts import generate_figure_manifest as gen

ROOT = Path(__file__).resolve().parents[1]
MODEL_MANIFEST = ROOT / "data" / "processed" / "model_run_manifest.json"
SEGMENT_LABELS = ROOT / "data" / "processed" / "segment_labels.parquet"


def _require_pipeline_artifacts() -> None:
    if not MODEL_MANIFEST.exists() or not SEGMENT_LABELS.exists():
        pytest.skip(
            "pipeline artifacts not present (run `make pipeline-full`) — "
            "generate_figure_manifest.py needs data/processed/model_run_manifest.json "
            "and data/processed/segment_labels.parquet"
        )


@pytest.fixture(scope="module")
def regenerated_manifest() -> dict:
    """Regenerate governance/FIGURE_MANIFEST.yaml and parse it back."""
    _require_pipeline_artifacts()
    assert gen.main() == 0
    return yaml.safe_load(gen.MANIFEST_PATH.read_text(encoding="utf-8"))


def test_schema_version_matches_generator_constant(regenerated_manifest: dict) -> None:
    assert regenerated_manifest["schema_version"] == gen.SCHEMA_VERSION
    assert isinstance(regenerated_manifest["schema_version"], int)


def test_every_figure_has_a_unique_chart_id(regenerated_manifest: dict) -> None:
    figures = regenerated_manifest["figures"]
    assert figures, "expected at least one figure entry"
    chart_ids = [entry["chart_id"] for entry in figures]
    assert all(chart_ids), "every figure entry must carry a non-empty chart_id"
    assert len(chart_ids) == len(set(chart_ids)), "chart_id values must be unique"


def test_manifest_header_carries_the_consumer_contract() -> None:
    _require_pipeline_artifacts()
    raw = gen.MANIFEST_PATH.read_text(encoding="utf-8")
    assert raw.startswith("# governance/FIGURE_MANIFEST.yaml — GENERATED FILE")
    assert "CONSUMER CONTRACT" in raw
    assert "chart_id" in raw
    assert "schema_version bump policy" in raw
    # Header (YAML comments) must precede a still-parseable machine body.
    parsed = yaml.safe_load(raw)
    assert parsed["schema_version"] == gen.SCHEMA_VERSION


def test_generator_flags_duplicate_chart_ids() -> None:
    """Unit test for the generator's own duplicate-id guard (belt-and-
    suspenders with the manifest-side uniqueness assertion above)."""
    figures = [
        {"chart_id": "dup", "path": "a.png", "generator": "g", "save_name": "a.png"},
        {"chart_id": "dup", "path": "b.png", "generator": "g", "save_name": "b.png"},
        {"chart_id": "unique", "path": "c.png", "generator": "g", "save_name": "c.png"},
    ]
    assert gen._duplicate_chart_ids(figures) == ["dup"]
