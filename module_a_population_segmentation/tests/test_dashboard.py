"""Tests for the Streamlit dashboard module.

Covers: smoke build, required output columns (parity with export pipeline),
and the national-rate reference label helper semantics.
"""

from __future__ import annotations

import pytest

pytest.importorskip(
    "shap",
    reason="install poetry with --extras explainability for dashboard SHAP tab",
)

from module_a_population_segmentation.app.streamlit_dashboard import (
    _build_sample,
    _make_national_reference_labels,
)


def test_dashboard_data_builder_smoke() -> None:
    raw, feat, seg, prop, anc = _build_sample(5000)
    assert len(raw) > 0
    assert len(feat) > 0
    assert "silhouette" in seg
    assert "metrics" in prop
    assert "national" in anc


def test_build_sample_segment_columns_present() -> None:
    """_build_sample must return feat with segment_id and dbscan_noise_flag.

    The dashboard previously dropped these two columns that the export pipeline
    attaches.  This test guards against regression so the dashboard output
    mirrors the contract artifacts consumed by Module B/C.
    """
    _, feat, _, _, _ = _build_sample(5000)
    for col in ("segment_label", "segment_id", "dbscan_noise_flag"):
        assert col in feat.columns, f"_build_sample feat missing column: {col}"


def test_build_sample_segment_id_valid_range() -> None:
    """segment_id must be in [0, k-1] = [0, 5] for k=6."""
    _, feat, _, _, _ = _build_sample(5000)
    assert feat["segment_id"].between(0, 5).all(), "segment_id values outside [0, 5] for k=6"


def test_build_sample_dbscan_noise_flag_dtype() -> None:
    """dbscan_noise_flag must be boolean, consistent with export contract."""
    _, feat, _, _, _ = _build_sample(5000)
    assert (
        feat["dbscan_noise_flag"].dtype == bool
    ), f"dbscan_noise_flag dtype is {feat['dbscan_noise_flag'].dtype}, expected bool"


def test_build_sample_propensity_in_unit_interval() -> None:
    _, feat, _, _, _ = _build_sample(5000)
    assert (
        feat["participation_propensity"].between(0.0, 1.0).all()
    ), "participation_propensity out of [0, 1]"


# ---------------------------------------------------------------------------
# _make_national_reference_labels
# ---------------------------------------------------------------------------


def test_reference_labels_shape() -> None:
    labels = _make_national_reference_labels(1000, 0.6125, seed=0)
    assert labels.shape == (1000,)


def test_reference_labels_dtype_binary() -> None:
    labels = _make_national_reference_labels(500, 0.5, seed=1)
    assert set(labels).issubset({0, 1}), "Labels must be binary (0 or 1)"


def test_reference_labels_mean_near_national_rate() -> None:
    """At large n the empirical mean should be within 2 pp of the target rate."""
    national_rate = 0.6125
    labels = _make_national_reference_labels(50_000, national_rate, seed=42)
    empirical = float(labels.mean())
    assert (
        abs(empirical - national_rate) < 0.02
    ), f"Reference label mean {empirical:.4f} deviates more than 2 pp from {national_rate}"


def test_reference_labels_deterministic() -> None:
    """Same seed must produce identical results."""
    a = _make_national_reference_labels(200, 0.5, seed=7)
    b = _make_national_reference_labels(200, 0.5, seed=7)
    assert (a == b).all()


def test_reference_labels_different_seeds_differ() -> None:
    a = _make_national_reference_labels(200, 0.5, seed=7)
    b = _make_national_reference_labels(200, 0.5, seed=8)
    assert not (a == b).all()


# ---------------------------------------------------------------------------
# SHAP feature importance fields
# ---------------------------------------------------------------------------


def test_build_sample_prop_includes_shap_artifacts() -> None:
    """_build_sample prop dict must include fitted_model, scaler, feature_names, x_all_scaled."""
    _, _, _, prop, _ = _build_sample(3000)
    for key in ("fitted_model", "scaler", "feature_names", "x_all_scaled"):
        assert key in prop, f"prop missing SHAP artifact key: {key}"


def test_build_sample_feature_names_count() -> None:
    """feature_names must have 11 elements (9 base + 2 derived)."""
    _, _, _, prop, _ = _build_sample(3000)
    assert (
        len(prop["feature_names"]) == 11
    ), f"Expected 11 feature names, got {len(prop['feature_names'])}"
