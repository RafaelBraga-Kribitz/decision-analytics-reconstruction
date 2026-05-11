"""Contract column tests for the Module A batch export pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest
import yaml

MEDIA_REQUIRED_COLUMNS = [
    "segment_label",
    "segment_size",
    "segment_size_pct",
    "mean_participation_propensity",
    "pct_internet_access",
    "mean_tv_penetration",
    "mean_radio_penetration",
    "mean_whatsapp_penetration",
    "pct_rural",
    "pct_jopara",
    "pct_structural_dependency",
    "dominant_department",
    "primary_reach_channel",
]


@pytest.fixture(scope="module")
def export_artifacts(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    """Run the export pipeline once with a small sample and return artifact paths."""
    from population_segmentation.pipeline.export import run_export

    repo_root = Path(__file__).resolve().parents[2]
    config_path = repo_root / "module_a_population_segmentation" / "config" / "generation.yaml"
    anchors_path = (
        repo_root / "module_a_population_segmentation" / "config" / "calibration_anchors.yaml"
    )

    with open(config_path) as f:
        config: dict[str, Any] = yaml.safe_load(f)
    with open(anchors_path) as f:
        anchors: dict[str, Any] = yaml.safe_load(f)

    out_dir = tmp_path_factory.mktemp("export_out")
    # 15k rows: department calibration gates (especially Guaira with only ~167
    # entities at 3k) are only stable above ~10k rows where the rake multiplicative
    # factor does not cause systematic clipping.
    artifacts = run_export(config, anchors, out_dir, sample_size=15_000)
    return artifacts


def test_segment_labels_columns(export_artifacts: dict[str, Path]) -> None:
    df = pd.read_parquet(export_artifacts["segment_labels"])
    for col in ["entity_id", "segment_label", "segment_id", "dbscan_noise_flag"]:
        assert col in df.columns, f"segment_labels.parquet missing column: {col}"


def test_participation_propensity_columns(export_artifacts: dict[str, Path]) -> None:
    df = pd.read_parquet(export_artifacts["participation_propensity"])
    required = [
        "entity_id",
        "participation_propensity",
        "raw_logit_score",
        "department_rake_multiplier",
    ]
    for col in required:
        assert col in df.columns, f"participation_propensity.parquet missing column: {col}"


def test_media_reachability_columns(export_artifacts: dict[str, Path]) -> None:
    df = pd.read_csv(export_artifacts["media_reachability_by_segment"])
    for col in MEDIA_REQUIRED_COLUMNS:
        assert col in df.columns, f"media_reachability_by_segment.csv missing column: {col}"


def test_population_master_clean_min_columns(export_artifacts: dict[str, Path]) -> None:
    df = pd.read_parquet(export_artifacts["population_master_clean"])
    assert "entity_id" in df.columns
    assert (
        len(df.columns) >= 20
    ), f"population_master_clean.parquet has only {len(df.columns)} columns; expected >= 20"


def test_entity_id_unique_in_all_artifacts(export_artifacts: dict[str, Path]) -> None:
    """Contract: entity_id must be unique (schema_contracts/*.yaml unique: true)."""
    for artifact in ["population_master_clean", "segment_labels", "participation_propensity"]:
        path = export_artifacts[artifact]
        df = pd.read_parquet(path)
        n_dup = int(df["entity_id"].duplicated().sum())
        assert n_dup == 0, f"{artifact}: {n_dup} duplicate entity_id values found"


def test_propensity_range_contract(export_artifacts: dict[str, Path]) -> None:
    """Contract: participation_propensity must lie in [0, 1] with no nulls."""
    df = pd.read_parquet(export_artifacts["participation_propensity"])
    assert not df["participation_propensity"].isna().any(), "propensity contains NaN"
    assert (
        df["participation_propensity"].between(0.0, 1.0).all()
    ), "propensity values outside [0, 1]"


def test_department_calibration_gates(
    export_artifacts: dict[str, Path],
) -> None:
    """Contract: verified TSJE department participation rates within ±0.5 pp."""
    import yaml

    anchors_path = (
        Path(__file__).resolve().parents[2]
        / "module_a_population_segmentation"
        / "config"
        / "calibration_anchors.yaml"
    )
    with open(anchors_path) as f:
        anchors: dict = yaml.safe_load(f)

    master = pd.read_parquet(export_artifacts["population_master_clean"])
    prop = pd.read_parquet(export_artifacts["participation_propensity"])

    dept_targets = anchors["department_participation_rates"]
    for dept in ["Presidente Hayes", "Alto Parana", "Central", "Guaira"]:
        mask = master["department"] == dept
        if mask.any():
            actual = float(prop.loc[mask.values, "participation_propensity"].mean())
            target = float(dept_targets[dept])
            assert abs(actual - target) < 0.005, (
                f"Dept calibration gate failed: {dept} actual={actual:.4f} "
                f"target={target:.4f} diff={actual - target:+.4f}"
            )


def test_dbscan_noise_flag_is_bool(export_artifacts: dict[str, Path]) -> None:
    """DBSCAN noise flag must be boolean (not an integer or object dtype)."""
    df = pd.read_parquet(export_artifacts["segment_labels"])
    assert (
        df["dbscan_noise_flag"].dtype == bool
    ), f"dbscan_noise_flag dtype is {df['dbscan_noise_flag'].dtype}, expected bool"


def test_all_four_artifacts_exist(export_artifacts: dict[str, Path]) -> None:
    expected_keys = {
        "population_master_clean",
        "segment_labels",
        "participation_propensity",
        "media_reachability_by_segment",
    }
    assert expected_keys == set(export_artifacts.keys())
    for name, path in export_artifacts.items():
        assert path.exists(), f"Artifact {name} not written to {path}"


def test_segment_labels_row_count_matches_master(export_artifacts: dict[str, Path]) -> None:
    master = pd.read_parquet(export_artifacts["population_master_clean"])
    labels = pd.read_parquet(export_artifacts["segment_labels"])
    assert len(master) == len(
        labels
    ), f"Row count mismatch: master={len(master)}, labels={len(labels)}"


def test_participation_propensity_row_count_matches_master(
    export_artifacts: dict[str, Path],
) -> None:
    master = pd.read_parquet(export_artifacts["population_master_clean"])
    prop = pd.read_parquet(export_artifacts["participation_propensity"])
    assert len(master) == len(
        prop
    ), f"Row count mismatch: master={len(master)}, propensity={len(prop)}"
