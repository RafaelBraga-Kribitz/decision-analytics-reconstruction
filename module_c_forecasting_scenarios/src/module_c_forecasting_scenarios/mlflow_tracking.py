"""Optional MLflow lineage (stub — enable when MLFLOW_TRACKING_URI is set)."""

from __future__ import annotations

import os


def log_run_params(params: dict[str, object]) -> None:
    """Log one parameter set as its own MLflow run (no-op without a tracking URI).

    Args:
        params: Parameter mapping; values are stringified.

    Returns:
        None.

    Raises:
        None: MLflow absence or an unset URI silently no-ops.

    Example:
        ``log_run_params({"calibration_series": "A"})``.
    """
    uri = os.environ.get("MLFLOW_TRACKING_URI")
    if not uri:
        return
    try:
        import mlflow
    except ImportError:
        return
    mlflow.set_tracking_uri(uri)
    mlflow.set_experiment(os.environ.get("MLFLOW_EXPERIMENT_NAME", "module_c_forecasting"))
    # Each call is its own run: a pipeline invoking multiple fits (e.g. the
    # anchored run plus the IMP-C05 unanchored companion) must not collide on
    # immutable param keys within one ambient run.
    if mlflow.active_run() is not None:
        mlflow.end_run()
    with mlflow.start_run():
        mlflow.log_params({k: str(v) for k, v in params.items()})
