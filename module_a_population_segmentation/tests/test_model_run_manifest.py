"""Tests for export run manifest (versioning / reproducibility metadata)."""

from __future__ import annotations

import json
from pathlib import Path

from population_segmentation.pipeline.model_run_manifest import (
    build_model_run_manifest,
    get_distribution_version,
    write_model_run_manifest,
)


def test_build_model_run_manifest_required_keys(tmp_path: Path) -> None:
    artifacts = {
        "population_master_clean": tmp_path / "population_master_clean.parquet",
        "segment_labels": tmp_path / "segment_labels.parquet",
    }
    for p in artifacts.values():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x")

    m = build_model_run_manifest(
        artifacts,
        random_seeds={"export_pipeline": 42},
        git_commit="abc123def",
        train_date_utc_iso="2026-05-12T12:00:00+00:00",
        package_version="0.1.0",
    )
    assert m["model_type"] == "module_a_export_bundle"
    assert m["version"] == "0.1.0"
    assert m["train_date"] == "2026-05-12T12:00:00+00:00"
    assert m["git_commit"] == "abc123def"
    assert m["random_seeds"] == {"export_pipeline": 42}
    assert "artifacts" in m
    assert set(m["artifacts"].keys()) == {"population_master_clean", "segment_labels"}


def test_manifest_json_roundtrip(tmp_path: Path) -> None:
    out = tmp_path / "model_run_manifest.json"
    artifacts = {"a": tmp_path / "a.parquet"}
    artifacts["a"].write_bytes(b"x")
    m = build_model_run_manifest(artifacts, random_seeds={"export_pipeline": 42})
    write_model_run_manifest(out, m)
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["model_type"] == m["model_type"]
    assert loaded["git_commit"] == m["git_commit"]


def test_get_distribution_version_returns_string() -> None:
    v = get_distribution_version()
    assert isinstance(v, str)
    assert len(v) > 0
