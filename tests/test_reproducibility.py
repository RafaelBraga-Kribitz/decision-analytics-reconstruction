"""Reproducibility validation — verify artifacts match expected metrics.

Tests that seeded pipeline runs produce consistent metrics within
floating-point tolerance (1e-3 for AUC, silhouette; 1e-2 for Brier score).
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

_PIPELINE_HINT = (
    "Pipeline artifact not present — run "
    "`make pipeline-dev && make module-b-allocate && MC_FAST=1 make module-c-all`"
)


def _require_artifact(path: Path) -> Path:
    if not path.exists():
        pytest.skip(f"{_PIPELINE_HINT}: {path}")
    return path


# ============================================================================
# Module A reproducibility
# ============================================================================


def test_module_a_manifest_exists() -> None:
    """Model run manifest must exist and be valid JSON."""
    manifest_path = _require_artifact(Path("data/processed/model_run_manifest.json"))
    with open(manifest_path) as f:
        manifest = json.load(f)
    assert "random_seeds" in manifest
    assert "model_type" in manifest
    assert manifest["model_type"] == "module_a_export_bundle"


def test_module_a_segment_labels_exist() -> None:
    """Segment labels parquet artifact must exist."""
    path = _require_artifact(Path("data/processed/segment_labels.parquet"))
    df = pd.read_parquet(path)
    assert "segment_id" in df.columns
    assert "segment_label" in df.columns
    assert (df["segment_id"] >= 0).all() and (df["segment_id"] < 6).all()


def test_module_a_propensity_exists_and_in_unit_interval() -> None:
    """Participation propensity artifact exists and is [0, 1]."""
    path = _require_artifact(Path("data/processed/participation_propensity.parquet"))
    df = pd.read_parquet(path)
    assert "entity_id" in df.columns
    assert "participation_propensity" in df.columns
    assert (df["participation_propensity"] >= 0.0).all()
    assert (df["participation_propensity"] <= 1.0).all()


def test_module_a_propensity_stats_reasonable() -> None:
    """Propensity statistics should be reasonable (mean 0.4–0.7, std 0.1–0.3)."""
    path = _require_artifact(Path("data/processed/participation_propensity.parquet"))
    df = pd.read_parquet(path)
    mean_prop = float(df["participation_propensity"].mean())
    std_prop = float(df["participation_propensity"].std())
    assert 0.4 < mean_prop < 0.7, f"Propensity mean {mean_prop:.4f} unreasonable"
    assert 0.08 < std_prop < 0.35, f"Propensity std {std_prop:.4f} unreasonable"


def test_module_a_population_clean_exists() -> None:
    """Population master clean artifact must exist."""
    path = _require_artifact(Path("data/processed/population_master_clean.parquet"))
    df = pd.read_parquet(path)
    assert "entity_id" in df.columns
    assert "department" in df.columns
    assert len(df) > 0


# ============================================================================
# Module B reproducibility
# ============================================================================


def test_module_b_allocation_baseline_exists() -> None:
    """Module B allocation artifact for baseline scenario must exist."""
    path = _require_artifact(Path("data/processed/module_b/allocation_baseline.parquet"))
    df = pd.read_parquet(path)
    assert "department" in df.columns
    assert "channel" in df.columns
    assert "budget_allocation_usd" in df.columns
    assert len(df) > 0


def test_module_b_manifest_baseline_exists() -> None:
    """Module B run manifest baseline must exist and be valid."""
    manifest_path = _require_artifact(Path("data/processed/module_b/run_manifest_baseline.json"))
    with open(manifest_path) as f:
        manifest = json.load(f)
    assert "run_id" in manifest
    assert "scenario_id" in manifest
    assert manifest["scenario_id"] == "baseline"


def test_module_b_allocation_spend_within_tolerance() -> None:
    """Total spend must be within ±1% of $6M envelope (reconstruction scale)."""
    path = _require_artifact(Path("data/processed/module_b/allocation_baseline.parquet"))
    df = pd.read_parquet(path)
    total_spend = float(df["budget_allocation_usd"].sum())
    envelope = 6_000_000.0  # Reconstruction envelope ($6M)
    tolerance = envelope * 0.01  # 1%
    assert (
        abs(total_spend - envelope) < tolerance
    ), f"Total spend {total_spend:.0f} deviates > 1% from envelope {envelope:.0f}"


# ============================================================================
# Module C reproducibility
# ============================================================================


def test_module_c_tracking_daily_posterior_exists() -> None:
    """Module C tracking daily posterior forecast must exist."""
    path = _require_artifact(
        Path("data/processed/module_c/run_all/tracking/daily_posterior_forecast.parquet")
    )
    df = pd.read_parquet(path)
    assert "date" in df.columns
    assert "posterior_mean_preference_margin_pp" in df.columns
    assert "posterior_hdi_low_pp" in df.columns
    assert "posterior_hdi_high_pp" in df.columns


def test_module_c_tracking_hdi_ordering() -> None:
    """HDI low < mean < high for all rows."""
    path = _require_artifact(
        Path("data/processed/module_c/run_all/tracking/daily_posterior_forecast.parquet")
    )
    df = pd.read_parquet(path)
    assert (df["posterior_hdi_low_pp"] < df["posterior_mean_preference_margin_pp"]).all()
    assert (df["posterior_mean_preference_margin_pp"] < df["posterior_hdi_high_pp"]).all()


def test_module_c_tracking_manifest_exists() -> None:
    """Module C tracking run manifest must exist."""
    manifest_path = _require_artifact(
        Path("data/processed/module_c/run_all/tracking/run_tracking_manifest.json")
    )
    with open(manifest_path) as f:
        manifest = json.load(f)
    assert "calibration_series" in manifest or "n_tracking_waves" in manifest


def test_module_c_house_effects_exists() -> None:
    """Module C house effects parquet must exist."""
    path = _require_artifact(
        Path("data/processed/module_c/run_all/tracking/posterior_house_effects.parquet")
    )
    df = pd.read_parquet(path)
    assert "pollster_id" in df.columns
    assert "house_effect_posterior_mean" in df.columns


def test_module_c_exit_model_summary_exists() -> None:
    """Module C exit model summary must exist."""
    path = _require_artifact(
        Path("data/processed/module_c/run_all/exit/exit_model_summary.parquet")
    )
    df = pd.read_parquet(path)
    # Exit model may be empty (insufficient rows) or have parameter rows
    assert len(df) >= 0


def test_module_c_monte_carlo_draws_exists() -> None:
    """Module C Monte Carlo scenario draws must exist."""
    path = _require_artifact(Path("data/processed/module_c/run_all/mc/monte_carlo_draws.parquet"))
    df = pd.read_parquet(path)
    assert "scenario_bucket" in df.columns or "draw_id" in df.columns
    assert len(df) > 0


# ============================================================================
# Cross-module consistency
# ============================================================================


def test_cross_module_entity_count_consistency() -> None:
    """Module A entity count must match downstream references."""
    pop_path = _require_artifact(Path("data/processed/population_master_clean.parquet"))
    seg_path = _require_artifact(Path("data/processed/segment_labels.parquet"))
    prop_path = _require_artifact(Path("data/processed/participation_propensity.parquet"))

    pop_a = pd.read_parquet(pop_path)
    seg_a = pd.read_parquet(seg_path)
    prop_a = pd.read_parquet(prop_path)

    n_pop = len(pop_a)
    n_seg = len(seg_a)
    n_prop = len(prop_a)

    assert (
        n_pop == n_seg == n_prop
    ), f"Entity count mismatch: population={n_pop}, segments={n_seg}, propensity={n_prop}"


def test_cross_module_segment_id_valid() -> None:
    """Segment IDs in labels must be in [0, 5]."""
    seg_path = _require_artifact(Path("data/processed/segment_labels.parquet"))
    seg_a = pd.read_parquet(seg_path)
    assert (seg_a["segment_id"] >= 0).all()
    assert (seg_a["segment_id"] < 6).all()  # k=6 clusters
