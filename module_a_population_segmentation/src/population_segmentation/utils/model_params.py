"""Single loader for ``config/model_params.yaml`` (F-088 / IMP-A06).

Every hyperparameter key in that file is read through this module by the code
path it describes; :func:`effective_hyperparameters` reports the values a run
actually used so the export manifest can record them.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path
from typing import Any

import yaml

MODEL_PARAMS_PATH = Path(__file__).resolve().parents[3] / "config" / "model_params.yaml"


@cache
def load_model_params() -> dict[str, Any]:  # Any: heterogeneous YAML document values
    """Return the parsed ``model_params.yaml`` (cached for the process).

    Args:
        None.

    Returns:
        The YAML document as a dict.

    Raises:
        OSError: If the config file cannot be read.

    Example:
        ``load_model_params()["kmeans"]["default_k"]``.
    """
    with open(MODEL_PARAMS_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def section(name: str) -> dict[str, Any]:  # Any: YAML scalars, lists and nested maps
    """Return one top-level section of ``model_params.yaml`` (empty if absent).

    Args:
        name: Section key, for example ``"kmeans"``.

    Returns:
        The section dict.

    Raises:
        OSError: If the config file cannot be read.

    Example:
        ``section("dbscan").get("eps", 1.0)``.
    """
    return dict(load_model_params().get(name) or {})


def effective_hyperparameters() -> dict[str, dict[str, Any]]:  # Any: YAML scalar values
    """Hyperparameters the Module A models run with, as loaded from config.

    Args:
        None.

    Returns:
        ``{"pca": {...}, "dbscan": {...}, "kmeans": {...}, "propensity": {...}}``
        restricted to the fit-time keys each model consumes.

    Raises:
        OSError: If the config file cannot be read.

    Example:
        ``manifest["effective_hyperparameters"] = effective_hyperparameters()``.
    """
    keys = {
        "pca": ("n_components", "random_state"),
        "dbscan": ("eps", "min_samples", "metric", "n_jobs"),
        "kmeans": (
            "default_k",
            "n_init",
            "init",
            "max_iter",
            "random_state",
            "bootstrap_n_samples",
            "bootstrap_subsample_frac",
        ),
        "propensity": (
            "penalty",
            "solver",
            "random_state",
            "max_iter",
            "train_frac",
            "calibration_frac",
            "test_frac",
            "stratify_by",
            "individual_spread_std",
        ),
    }
    return {name: {k: section(name).get(k) for k in ks} for name, ks in keys.items()}
