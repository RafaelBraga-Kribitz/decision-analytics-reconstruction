"""Reproducibility manifest written beside Module A export artifacts."""

from __future__ import annotations

import json
import logging
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_MODEL_TYPE = "module_a_export_bundle"


def get_distribution_version() -> str:
    try:
        from importlib.metadata import version

        return str(version("decision-analytics-reconstruction"))
    except Exception:
        return "0.0.0-dev"


def get_git_commit(*, cwd: Path | None = None) -> str:
    try:
        root = cwd if cwd is not None else Path.cwd()
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if r.returncode == 0 and r.stdout:
            return r.stdout.strip()[:40]
    except (OSError, subprocess.TimeoutExpired):
        pass
    return "unknown"


def build_model_run_manifest(
    artifacts: dict[str, Path],
    *,
    random_seeds: dict[str, int],
    model_type: str = DEFAULT_MODEL_TYPE,
    package_version: str | None = None,
    git_commit: str | None = None,
    train_date_utc_iso: str | None = None,
) -> dict[str, Any]:
    """JSON-serializable manifest for CFO / ML engineer provenance."""
    ver = package_version if package_version is not None else get_distribution_version()
    commit = git_commit if git_commit is not None else get_git_commit()
    when = train_date_utc_iso
    if when is None:
        when = datetime.now(UTC).replace(microsecond=0).isoformat()

    artifact_entries = {k: str(Path(v).resolve()) for k, v in sorted(artifacts.items())}

    return {
        "model_type": model_type,
        "version": ver,
        "train_date": when,
        "git_commit": commit,
        "random_seeds": dict(random_seeds),
        "artifacts": artifact_entries,
    }


def write_model_run_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def maybe_log_mlflow_export(manifest: dict[str, Any]) -> None:
    """Optional tracking when MLFLOW_TRACKING_URI is set (same opt-in pattern as Module C)."""
    uri = os.environ.get("MLFLOW_TRACKING_URI")
    if not uri:
        return
    try:
        import mlflow

        mlflow.set_tracking_uri(uri)
        exp = os.environ.get("MLFLOW_EXPERIMENT_NAME", "module_a_export")
        mlflow.set_experiment(exp)
        with mlflow.start_run(run_name="population_segmentation_export"):
            mlflow.log_param("model_type", manifest.get("model_type", ""))
            mlflow.log_param("package_version", manifest.get("version", ""))
            mlflow.log_param("git_commit", manifest.get("git_commit", ""))
            mlflow.log_param("train_date", manifest.get("train_date", ""))
            seeds = manifest.get("random_seeds") or {}
            for k, v in seeds.items():
                mlflow.log_param(f"seed_{k}", v)
            arts = manifest.get("artifacts") or {}
            for name, pth in arts.items():
                mlflow.log_param(f"artifact_{name}", str(pth))
    except Exception as exc:  # pragma: no cover - optional path
        logger.warning("MLflow logging skipped: %s", exc)
