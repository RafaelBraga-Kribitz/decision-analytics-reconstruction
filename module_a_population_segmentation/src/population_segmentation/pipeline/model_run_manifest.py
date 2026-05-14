"""Reproducibility manifest written beside Module A export artifacts."""

from __future__ import annotations

import json
import logging
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_MODEL_TYPE = "module_a_export_bundle"


def get_distribution_version() -> str:
    """Return the installed ``decision-analytics-reconstruction`` package version string.

    Args:
        None

    Returns:
        PEP 440 version from importlib metadata, or ``\"0.0.0-dev\"`` if unavailable.

    Raises:
        None: Exceptions from metadata lookup are swallowed and mapped to the dev sentinel.

    Example:
        Written into ``model_run_manifest.json`` for reproducibility alongside git SHA.
    """
    try:
        from importlib.metadata import version

        return str(version("decision-analytics-reconstruction"))
    except Exception:
        return "0.0.0-dev"


def get_git_commit(*, cwd: Path | None = None) -> str:
    """Return the current ``git rev-parse HEAD`` truncated to 40 characters.

    Args:
        cwd: Repository root for the git subprocess; defaults to :func:`Path.cwd`.

    Returns:
        Short commit hash or ``\"unknown\"`` if git is unavailable or not a repo.

    Raises:
        None: Git failures are mapped to ``\"unknown\"``.

    Example:
        Bundled into export manifests next to package version and random seeds.
    """
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
) -> dict[str, object]:
    """Build a JSON-serializable manifest for CFO / ML engineer provenance.

    Args:
        artifacts: Map of logical artifact names to on-disk paths (resolved to
            absolute strings in the output).
        random_seeds: Named integer seeds used during the run (for example
            ``numpy``, ``sklearn``, stdlib ``random``).
        model_type: High-level model or pipeline label stored in the manifest.
        package_version: Override for package version; when ``None``, uses
            :func:`get_distribution_version`.
        git_commit: Override for git SHA; when ``None``, uses :func:`get_git_commit`.
        train_date_utc_iso: ISO8601 UTC timestamp string; when ``None``, uses
            the current time (microseconds stripped).

    Returns:
        Dict suitable for :func:`write_model_run_manifest`, including
        ``model_type``, ``version``, ``train_date``, ``git_commit``,
        ``random_seeds``, and ``artifacts``.

    Raises:
        None: This function does not raise for typical inputs.

    Example:
        Used by the export pipeline to bundle reproducibility metadata next to
        parquet and CSV outputs.
    """
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


def write_model_run_manifest(path: Path, manifest: dict[str, object]) -> None:
    """Persist ``manifest`` as UTF-8 JSON with stable key ordering.

    Args:
        path: Destination file (parent directories are created as needed).
        manifest: Serializable dict from :func:`build_model_run_manifest`.

    Returns:
        None

    Raises:
        OSError: If the path cannot be written.

    Example:
        Called at the end of ``run_export`` beside parquet and CSV artifacts.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def maybe_log_mlflow_export(
    manifest: dict[str, object],
    *,
    metrics: dict[str, float] | None = None,
    local_tracking_root: Path | None = None,
) -> None:
    """Log export metadata and ML metrics to MLflow local file store.

    Defaults to a local ``mlruns/`` store beside ``local_tracking_root`` when
    ``MLFLOW_TRACKING_URI`` is not set. Swallows all MLflow failures at warning level.

    Args:
        manifest: Dict from :func:`build_model_run_manifest`.
        metrics: Optional scalar metrics to log (e.g. silhouette, auc_roc, brier_score).
        local_tracking_root: Directory under which ``mlruns/`` is created when no
            ``MLFLOW_TRACKING_URI`` env var is present. When ``None`` and no env var
            is set, MLflow defaults to ``mlruns/`` in the current working directory.

    Returns:
        ``None``

    Raises:
        None: MLflow failures are caught and logged at warning level.

    Example:
        Called at the end of ``run_export`` to persist a reproducible run record.
    """
    # Env var always wins; local_tracking_root only used as fallback default
    env_uri = os.environ.get("MLFLOW_TRACKING_URI")
    if env_uri:
        uri = env_uri
    elif local_tracking_root is not None:
        uri = f"sqlite:///{local_tracking_root.resolve() / 'mlruns.db'}"
    else:
        uri = "sqlite:///mlruns.db"
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
            raw_seeds = manifest.get("random_seeds")
            if isinstance(raw_seeds, dict):
                for k, v in raw_seeds.items():
                    mlflow.log_param(f"seed_{k}", v)
            raw_arts = manifest.get("artifacts")
            if isinstance(raw_arts, dict):
                for name, pth in raw_arts.items():
                    mlflow.log_param(f"artifact_{name}", str(pth))
            if metrics:
                mlflow.log_metrics(metrics)
    except Exception as exc:  # pragma: no cover - optional path
        logger.warning("MLflow logging skipped: %s", exc)
