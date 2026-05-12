"""Regression: `make pipeline-dev` runs full Module A export into data/processed/."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_MAKEFILE = _REPO / "Makefile"
_PROCESSED = _REPO / "data" / "processed"
_DEFAULT_SAMPLE = "10000"

_EXPORT_ARTIFACTS = (
    "population_master_clean.parquet",
    "segment_labels.parquet",
    "participation_propensity.parquet",
    "media_reachability_by_segment.csv",
    "media_reachability_by_segment_department.csv",
    "model_run_manifest.json",
)


def _makefile_text() -> str:
    return _MAKEFILE.read_text(encoding="utf-8")


def _pipeline_dev_body(text: str) -> str:
    match = re.search(r"^pipeline-dev:\n((?:\t[^\n]*\n)+)", text, re.MULTILINE)
    assert match is not None, "Makefile target pipeline-dev: not found"
    return match.group(1)


def test_pipeline_dev_invokes_full_module_a_pipeline() -> None:
    body = _pipeline_dev_body(_makefile_text())
    flat = body.replace("\n", " ").replace("\t", " ")
    assert "poetry run python -m population_segmentation.pipeline" in flat
    assert "--out-dir data/processed" in flat
    assert "--sample-size $(or $(SAMPLE)," + _DEFAULT_SAMPLE + ")" in flat


def test_schema_contracts_cover_pipeline_dev_tabular_outputs() -> None:
    """Export writes stems documented under schema_contracts/."""
    root = _REPO / "schema_contracts"
    for filename in (
        "population_master_clean.yaml",
        "segment_labels.yaml",
        "participation_propensity.yaml",
        "media_reachability_by_segment.yaml",
        "media_reachability_by_segment_department.yaml",
    ):
        assert (root / filename).is_file(), f"Missing contract {filename}"


@pytest.mark.slow
def test_make_pipeline_dev_writes_contract_artifacts() -> None:
    """Runs ``make pipeline-dev`` with SAMPLE=10000 (matches default and ``test_eda``)."""
    proc = subprocess.run(
        ["make", "pipeline-dev", "SAMPLE=10000"],
        cwd=_REPO,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout or "")
        sys.stderr.write(proc.stderr or "")
    assert proc.returncode == 0, f"make pipeline-dev failed: {proc.stderr!r}"
    for name in _EXPORT_ARTIFACTS:
        path = _PROCESSED / name
        assert path.is_file(), f"expected artifact missing after pipeline-dev: {path}"
