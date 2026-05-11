"""TDD tests for segment_reachability_aggregate module."""

from __future__ import annotations

import numpy as np
import pandas as pd
from population_segmentation.data.segment_reachability_aggregate import (
    aggregate_media_reachability_by_segment,
)

REQUIRED_COLUMNS = [
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
ALLOWED_CHANNELS = {"tv", "radio", "whatsapp", "direct"}
ALLOWED_SEGMENTS = {
    "rural_committed",
    "urban_high_volatility",
    "youth_volatile",
    "structurally_dependent_bloc",
    "rural_low_propensity",
    "committed_opposition",
}


def make_fixture(n_per_segment: int = 20) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    segments = list(ALLOWED_SEGMENTS) * n_per_segment
    n = len(segments)
    return pd.DataFrame(
        {
            "segment_label": segments,
            "participation_propensity": rng.uniform(0.2, 0.9, n),
            "internet_access_flag": rng.integers(0, 2, n).astype(bool),
            "media_penetration_tv": rng.uniform(0.3, 0.9, n),
            "media_penetration_radio": rng.uniform(0.1, 0.7, n),
            "media_penetration_whatsapp": rng.uniform(0.1, 0.8, n),
            "rural_flag": rng.integers(0, 2, n).astype(bool),
            "jopara_flag": rng.integers(0, 2, n).astype(bool),
            "structural_dependency_encoded": rng.integers(0, 3, n).astype(float),
            "department": rng.choice(["Central", "Presidente Hayes", "Alto Parana"], n),
        }
    )


def test_columns_present() -> None:
    df = make_fixture()
    result = aggregate_media_reachability_by_segment(df)
    for col in REQUIRED_COLUMNS:
        assert col in result.columns, f"Missing column: {col}"


def test_primary_reach_channel_values() -> None:
    df = make_fixture()
    result = aggregate_media_reachability_by_segment(df)
    assert set(result["primary_reach_channel"]).issubset(ALLOWED_CHANNELS)


def test_segment_label_values() -> None:
    df = make_fixture()
    result = aggregate_media_reachability_by_segment(df)
    assert set(result["segment_label"]).issubset(ALLOWED_SEGMENTS)


def test_segment_size_pct_sums_to_one() -> None:
    df = make_fixture()
    result = aggregate_media_reachability_by_segment(df)
    assert abs(result["segment_size_pct"].sum() - 1.0) < 1e-5


def test_segment_size_matches_input_counts() -> None:
    df = make_fixture(n_per_segment=20)
    result = aggregate_media_reachability_by_segment(df)
    assert result["segment_size"].sum() == len(df)


def test_one_row_per_segment() -> None:
    df = make_fixture()
    result = aggregate_media_reachability_by_segment(df)
    assert len(result) == len(df["segment_label"].unique())
    assert result["segment_label"].nunique() == len(result)


def test_float32_columns() -> None:
    df = make_fixture()
    result = aggregate_media_reachability_by_segment(df)
    float_cols = [
        "mean_participation_propensity",
        "pct_internet_access",
        "mean_tv_penetration",
        "mean_radio_penetration",
        "mean_whatsapp_penetration",
        "pct_rural",
        "pct_jopara",
        "pct_structural_dependency",
        "segment_size_pct",
    ]
    for col in float_cols:
        assert result[col].dtype == "float32", f"{col} should be float32"


def test_direct_channel_when_equal() -> None:
    """When all three penetration means are equal, primary_reach_channel must be 'direct'."""
    rng = np.random.default_rng(0)
    segments = ["rural_committed"] * 10
    n = len(segments)
    df = pd.DataFrame(
        {
            "segment_label": segments,
            "participation_propensity": rng.uniform(0.4, 0.6, n),
            "internet_access_flag": [True] * n,
            "media_penetration_tv": [0.5] * n,
            "media_penetration_radio": [0.5] * n,
            "media_penetration_whatsapp": [0.5] * n,
            "rural_flag": [True] * n,
            "jopara_flag": [False] * n,
            "structural_dependency_encoded": [1.0] * n,
            "department": ["Central"] * n,
        }
    )
    result = aggregate_media_reachability_by_segment(df)
    assert result.iloc[0]["primary_reach_channel"] == "direct"
