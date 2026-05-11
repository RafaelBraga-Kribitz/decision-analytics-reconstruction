"""TDD tests for segmentation models (DBSCAN + KMeans)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml


@pytest.fixture(scope="module")
def config() -> dict:  # type: ignore[type-arg]
    path = Path(__file__).parent.parent / "config" / "generation.yaml"
    with open(path) as f:
        cfg = yaml.safe_load(f)
    cfg["sample_size"] = 10_000
    return cfg


@pytest.fixture(scope="module")
def feature_df(config: dict) -> pd.DataFrame:  # type: ignore[type-arg]
    from population_segmentation.data.cleaner import clean_population
    from population_segmentation.data.generator import generate_population
    from population_segmentation.data.raw_injector import inject_flaws
    from population_segmentation.features.behavioral import build_behavioral_features
    from population_segmentation.features.demographic import build_demographic_features
    from population_segmentation.features.reachability import build_reachability_features

    base = generate_population(config, seed=42)
    raw = inject_flaws(base, config, seed=42)
    clean = clean_population(raw, config)
    d = build_demographic_features(clean)
    b = build_behavioral_features(d)
    r = build_reachability_features(b)
    return r


def test_dbscan_noise_rate_below_threshold(feature_df: pd.DataFrame) -> None:
    from population_segmentation.models.segmentation import DBSCANNoiseFilter

    filt = DBSCANNoiseFilter(eps=0.7, min_samples=20)
    res = filt.fit_transform(feature_df)
    assert res["noise_rate"] < 0.01


def test_kmeans_silhouette_above_threshold(feature_df: pd.DataFrame) -> None:
    from population_segmentation.models.segmentation import KMeansSegmenter

    seg = KMeansSegmenter(k=6, random_state=42)
    out = seg.fit_predict(feature_df)
    assert out["silhouette"] > 0.35


def test_kmeans_bootstrap_ari_above_threshold(feature_df: pd.DataFrame) -> None:
    from population_segmentation.models.segmentation import KMeansSegmenter

    seg = KMeansSegmenter(k=6, random_state=42)
    out = seg.fit_predict(feature_df)
    assert out["bootstrap_ari"] > 0.80


def test_segment_size_coverage(feature_df: pd.DataFrame) -> None:
    from population_segmentation.models.segmentation import KMeansSegmenter

    seg = KMeansSegmenter(k=6, random_state=42)
    out = seg.fit_predict(feature_df)
    min_share = out["segment_share"].min()
    assert min_share >= 0.01


def test_build_segmentation_frame_columns(feature_df: pd.DataFrame) -> None:
    from population_segmentation.models.segmentation import (
        SEGMENT_LABEL_MAP,
        build_segmentation_frame,
    )

    labels_df, metrics = build_segmentation_frame(feature_df)
    for col in ["entity_id", "segment_id", "segment_label", "dbscan_noise_flag"]:
        assert col in labels_df.columns, f"Missing column: {col}"
    assert set(labels_df["segment_label"]) <= set(SEGMENT_LABEL_MAP.values())
    assert labels_df["dbscan_noise_flag"].dtype == bool


def test_build_segmentation_frame_noise_rate(feature_df: pd.DataFrame) -> None:
    from population_segmentation.models.segmentation import build_segmentation_frame

    labels_df, metrics = build_segmentation_frame(feature_df)
    assert metrics["noise_rate"] < 0.01


def test_build_segmentation_frame_metrics_keys(feature_df: pd.DataFrame) -> None:
    from population_segmentation.models.segmentation import build_segmentation_frame

    _, metrics = build_segmentation_frame(feature_df)
    for key in ["silhouette", "bootstrap_ari", "noise_rate", "segment_share"]:
        assert key in metrics, f"Missing metric key: {key}"


def test_build_segmentation_frame_row_count(feature_df: pd.DataFrame) -> None:
    from population_segmentation.models.segmentation import build_segmentation_frame

    labels_df, _ = build_segmentation_frame(feature_df)
    assert len(labels_df) == len(feature_df)
