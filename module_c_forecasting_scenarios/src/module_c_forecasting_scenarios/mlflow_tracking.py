"""Optional MLflow lineage (stub — enable when MLFLOW_TRACKING_URI is set)."""

from __future__ import annotations

import os
from typing import Any


def log_run_params(params: dict[str, Any]) -> None:
    uri = os.environ.get("MLFLOW_TRACKING_URI")
    if not uri:
        return
    try:
        import mlflow
    except ImportError:
        return
    mlflow.set_tracking_uri(uri)
    mlflow.set_experiment(os.environ.get("MLFLOW_EXPERIMENT_NAME", "module_c_forecasting"))
    mlflow.log_params({k: str(v) for k, v in params.items()})
