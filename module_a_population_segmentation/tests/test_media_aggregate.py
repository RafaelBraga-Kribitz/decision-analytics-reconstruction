"""TDD tests for segment_reachability_aggregate module."""

from __future__ import annotations

import numpy as np
import pandas as pd
from population_segmentation.data.segment_reachability_aggregate import (
    CHACO_DEPARTMENTS,
    DEPARTMENTS,
    SEGMENT_LABELS,
    aggregate_media_reachability_by_segment,
    aggregate_media_reachability_by_segment_department,
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


# ---------------------------------------------------------------------------
# Segment-by-department aggregator (contract grain for Module B caps)
# ---------------------------------------------------------------------------


def make_full_fixture(n_per_cell: int = 5) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    rows = []
    for seg in SEGMENT_LABELS:
        for dept in DEPARTMENTS:
            for _ in range(n_per_cell):
                rows.append(
                    {
                        "segment_label": seg,
                        "department": dept,
                        "participation_propensity": float(rng.uniform(0.2, 0.9)),
                        "internet_access_flag": bool(rng.integers(0, 2)),
                        "media_penetration_tv": float(rng.uniform(0.3, 0.95)),
                        "media_penetration_radio": float(rng.uniform(0.1, 0.7)),
                        "media_penetration_whatsapp": float(rng.uniform(0.1, 0.8)),
                        "rural_flag": bool(rng.integers(0, 2)),
                        "jopara_flag": bool(rng.integers(0, 2)),
                        "structural_dependency_encoded": float(rng.integers(0, 3)),
                    }
                )
    return pd.DataFrame(rows)


def test_dept_aggregator_row_count_is_dense() -> None:
    df = make_full_fixture()
    result = aggregate_media_reachability_by_segment_department(df)
    assert len(result) == len(SEGMENT_LABELS) * len(DEPARTMENTS)


def test_dept_aggregator_unique_key() -> None:
    df = make_full_fixture()
    result = aggregate_media_reachability_by_segment_department(df)
    assert not result.duplicated(["segment_label", "department"]).any()


def test_dept_aggregator_region_tags_chaco() -> None:
    df = make_full_fixture()
    result = aggregate_media_reachability_by_segment_department(df)
    chaco_mask = result["department"].isin(list(CHACO_DEPARTMENTS))
    assert (result.loc[chaco_mask, "region"] == "CHACO").all()
    assert (result.loc[~chaco_mask, "region"] == "ORIENTAL").all()


def test_dept_aggregator_empty_cells_have_zero_size_and_null_means() -> None:
    # Build a dataset that only covers a small subset → most cells are empty.
    df = pd.DataFrame(
        {
            "segment_label": ["rural_committed", "youth_volatile"],
            "department": ["Central", "Asuncion"],
            "participation_propensity": [0.5, 0.6],
            "internet_access_flag": [True, True],
            "media_penetration_tv": [0.9, 0.95],
            "media_penetration_radio": [0.5, 0.4],
            "media_penetration_whatsapp": [0.6, 0.7],
            "rural_flag": [True, False],
            "jopara_flag": [True, False],
            "structural_dependency_encoded": [1.0, 0.0],
        }
    )
    result = aggregate_media_reachability_by_segment_department(df)

    # Empty cells: every (segment, department) pair not in the input has size 0.
    empty = result[(result["segment_size"] == 0)]
    assert len(empty) == len(SEGMENT_LABELS) * len(DEPARTMENTS) - 2
    assert empty["mean_participation_propensity"].isna().all()
    assert empty["primary_reach_channel"].isna().all()


def test_dept_aggregator_segment_size_pct_of_segment_sums_to_one() -> None:
    df = make_full_fixture()
    result = aggregate_media_reachability_by_segment_department(df)
    sums = result.groupby("segment_label")["segment_size_pct_of_segment"].sum()
    for seg, total in sums.items():
        assert abs(total - 1.0) < 1e-4, f"segment {seg} sum = {total}"


def test_dept_aggregator_segment_size_pct_of_department_sums_to_one() -> None:
    df = make_full_fixture()
    result = aggregate_media_reachability_by_segment_department(df)
    sums = result.groupby("department")["segment_size_pct_of_department"].sum()
    for dept, total in sums.items():
        assert abs(total - 1.0) < 1e-4, f"department {dept} sum = {total}"


def test_dept_aggregator_primary_channel_argmax_when_size_positive() -> None:
    rows = []
    for dept in DEPARTMENTS:
        rows.append(
            {
                "segment_label": "rural_committed",
                "department": dept,
                "participation_propensity": 0.6,
                "internet_access_flag": True,
                "media_penetration_tv": 0.95,  # dominant
                "media_penetration_radio": 0.4,
                "media_penetration_whatsapp": 0.5,
                "rural_flag": True,
                "jopara_flag": True,
                "structural_dependency_encoded": 1.0,
            }
        )
    df = pd.DataFrame(rows)
    result = aggregate_media_reachability_by_segment_department(df)
    rural_rows = result[result["segment_label"] == "rural_committed"]
    assert (rural_rows["primary_reach_channel"] == "tv").all()
