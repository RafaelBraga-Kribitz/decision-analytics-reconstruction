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
