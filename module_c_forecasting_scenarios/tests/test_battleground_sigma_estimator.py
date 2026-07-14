"""Tests for battleground sigma_idio estimator (v0.5 reference data)."""

from __future__ import annotations

from pathlib import Path

import pytest

from module_c_forecasting_scenarios.geo.sigma_estimator import (
    ESTIMATOR_VERSION,
    PROVENANCE_ESTIMATED,
    PROVENANCE_FALLBACK,
    estimate_sigma_idio,
    run_sigma_estimation_and_write,
    validate_tsje_2013,
)
from module_c_forecasting_scenarios.paths import repo_root


@pytest.fixture()
def reference_dir() -> Path:
    ref = repo_root() / "data" / "reference" / "battleground"
    if not (ref / "dept_poll_margins.csv").is_file():
        pytest.skip("reference battleground data not committed")
    return ref


def test_tsje_2013_national_reconciliation(reference_dir: Path) -> None:
    import pandas as pd

    df = pd.read_csv(reference_dir / "tsje_2013_department_results.csv")
    validate_tsje_2013(df)


def test_sigma_estimator_deterministic(reference_dir: Path) -> None:
    a = estimate_sigma_idio(reference_dir)
    b = estimate_sigma_idio(reference_dir)
    assert a.reference_data_sha256 == b.reference_data_sha256
    assert a.sigma_by_department == b.sigma_by_department


def test_sigma_estimator_covers_all_departments(reference_dir: Path) -> None:
    from module_b_resource_allocation.constants import DEPARTMENTS

    result = estimate_sigma_idio(reference_dir)
    assert set(result.sigma_by_department) == set(DEPARTMENTS)
    assert all(v > 0 for v in result.sigma_by_department.values())


def test_polled_departments_have_estimated_provenance(reference_dir: Path) -> None:
    result = estimate_sigma_idio(reference_dir)
    assert result.provenance_by_department["Asuncion"] == PROVENANCE_ESTIMATED
    assert result.n_obs_by_department["Asuncion"] >= 4


def test_missing_poll_departments_use_fallback(reference_dir: Path) -> None:
    result = estimate_sigma_idio(reference_dir)
    assert result.provenance_by_department["Caaguazu"] == PROVENANCE_FALLBACK
    assert result.n_obs_by_department["Caaguazu"] == 0


def test_write_sigma_yaml_roundtrip(reference_dir: Path, tmp_path: Path) -> None:
    import yaml

    out = tmp_path / "battleground_sigma_idio.yaml"
    run_sigma_estimation_and_write(reference_dir=reference_dir, out_yaml=out)
    data = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert data["estimator_version"] == ESTIMATOR_VERSION
    assert "Asuncion" in data["departments"]
