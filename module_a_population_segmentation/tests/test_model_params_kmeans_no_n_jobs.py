"""Regression: KMeans must not declare n_jobs in model_params.yaml (sklearn >= 1.4)."""

from __future__ import annotations

from pathlib import Path

import yaml

_MODULE_ROOT = Path(__file__).resolve().parents[1]
_MODEL_PARAMS = _MODULE_ROOT / "config" / "model_params.yaml"


def test_kmeans_section_has_no_n_jobs_key() -> None:
    """KMeans dropped ``n_jobs``; stale YAML breaks any future loader using **kwargs."""
    text = _MODEL_PARAMS.read_text(encoding="utf-8")
    assert "OMP_NUM_THREADS" in text or "OPENBLAS_NUM_THREADS" in text or "MKL_NUM_THREADS" in text
    data = yaml.safe_load(text)
    assert isinstance(data, dict)
    kmeans = data.get("kmeans")
    assert isinstance(kmeans, dict)
    assert "n_jobs" not in kmeans
