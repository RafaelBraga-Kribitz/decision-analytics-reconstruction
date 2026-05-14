"""Tests for export run manifest (versioning / reproducibility metadata)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

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


def test_maybe_log_mlflow_local_store_logs_metrics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """maybe_log_mlflow_export writes run with metrics to local mlruns/ store."""
    # Unset any leaked env var so local_tracking_root fallback is exercised
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
    from population_segmentation.pipeline.model_run_manifest import maybe_log_mlflow_export

    manifest: dict[str, object] = {
        "model_type": "module_a_export_bundle",
        "version": "0.1.0",
        "git_commit": "abc123",
        "train_date": "2026-05-13T10:00:00+00:00",
        "random_seeds": {"segmentation": 42},
        "artifacts": {},
    }
    metrics = {
        "segmentation_silhouette": 0.52,
        "propensity_auc_roc": 0.81,
        "propensity_brier_score": 0.12,
    }

    local_root = tmp_path / "run_out"
    local_root.mkdir()
    maybe_log_mlflow_export(manifest, metrics=metrics, local_tracking_root=local_root)

    db_path = local_root / "mlruns.db"
    assert db_path.exists(), "mlruns.db not created — maybe_log_mlflow_export must write local store"

    import mlflow

    client = mlflow.MlflowClient(tracking_uri=f"sqlite:///{db_path}")
    experiments = client.search_experiments()
    assert len(experiments) >= 1, "at least one MLflow experiment expected"
    runs = client.search_runs([e.experiment_id for e in experiments])
    assert len(runs) >= 1, "at least one MLflow run expected"
    logged_keys = {m.key for r in runs for m in client.get_metric_history(r.info.run_id, "segmentation_silhouette")}
    assert "segmentation_silhouette" in logged_keys or any(
        r.data.metrics.get("segmentation_silhouette") for r in runs
    ), "segmentation_silhouette metric not logged"
