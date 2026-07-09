"""Interpretation gates for profile-derived segment labels (F-039).

Segment names must be earned by cluster content, not assigned by KMeans
index order. These tests verify on the real generated population that the
cluster carrying each canonical name actually exhibits the semantics the
name claims — and that the assignment is a deterministic bijection.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from population_segmentation.pipeline.models.segmentation import (
    LABEL_SCORE_WEIGHTS,
    assign_segment_labels,
    build_segmentation_frame,
    cluster_profiles,
)


@pytest.fixture(scope="module")
def fitted() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Feature frame, labels_df, and cluster profiles on a real generated sample."""
    from pathlib import Path

    import yaml
    from population_segmentation.data.cleaner import clean_population
    from population_segmentation.data.generator import generate_population
    from population_segmentation.data.raw_injector import inject_flaws
    from population_segmentation.features.behavioral import build_behavioral_features
    from population_segmentation.features.demographic import build_demographic_features
    from population_segmentation.features.reachability import build_reachability_features

    config_path = Path(__file__).parent.parent / "config" / "generation.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)
    config["sample_size"] = 6_000

    base = generate_population(config, seed=42)
    raw = inject_flaws(base, config, seed=42)
    clean = clean_population(raw, config)
    feat = build_reachability_features(build_behavioral_features(build_demographic_features(clean)))
    labels_df, _ = build_segmentation_frame(feat, k=6, random_state=42)
    merged = feat.merge(labels_df[["entity_id", "segment_label"]], on="entity_id")
    profiles = cluster_profiles(feat, labels_df["segment_id"].to_numpy())
    return merged, labels_df, profiles


def test_assignment_is_bijection(fitted) -> None:
    _, labels_df, _ = fitted
    mapping = labels_df.drop_duplicates("segment_id")[["segment_id", "segment_label"]]
    assert len(mapping) == 6
    assert mapping["segment_label"].nunique() == 6
    assert set(mapping["segment_label"]) == set(LABEL_SCORE_WEIGHTS)


def test_assignment_deterministic(fitted) -> None:
    merged, labels_df, _ = fitted
    feature_cols = [c for c in merged.columns if c != "segment_label"]
    again = assign_segment_labels(merged[feature_cols], labels_df["segment_id"].to_numpy())
    current = dict(
        labels_df.drop_duplicates("segment_id")[["segment_id", "segment_label"]].to_numpy()
    )
    assert {int(k): v for k, v in current.items()} == again


def _seg_mean(merged: pd.DataFrame, label: str, col: str) -> float:
    return float(merged.loc[merged["segment_label"] == label, col].mean())


def test_rural_committed_is_more_rural_than_urban_label(fitted) -> None:
    merged, _, _ = fitted
    urban = _seg_mean(merged, "urban_high_volatility", "rural_flag")
    assert _seg_mean(merged, "rural_committed", "rural_flag") > urban


def test_youth_volatile_lands_on_a_youth_cluster(fitted) -> None:
    """The youth_volatile label must sit on an (almost) fully-youth cluster.

    The generated population yields two all-youth clusters (rural and metro),
    so 'top youth share' can tie; the guarantee is that the label is earned
    by a genuinely youth-dominated cluster.
    """
    merged, _, _ = fitted
    assert _seg_mean(merged, "youth_volatile", "youth_flag") >= 0.9


def test_structurally_dependent_bloc_has_top_dependency(fitted) -> None:
    merged, _, _ = fitted
    by_label = merged.groupby("segment_label")["structural_dependency_encoded"].mean()
    assert by_label.idxmax() == "structurally_dependent_bloc"


def test_committed_opposition_has_top_opposition_share(fitted) -> None:
    merged, _, _ = fitted
    opp = (merged["preference_proxy_encoded"] == 1).astype(float)
    by_label = opp.groupby(merged["segment_label"]).mean()
    assert by_label.idxmax() == "committed_opposition"


def test_rural_committed_outcommits_rural_low_propensity(fitted) -> None:
    merged, _, _ = fitted
    committed = _seg_mean(merged, "rural_committed", "preference_proxy_strength")
    low = _seg_mean(merged, "rural_low_propensity", "preference_proxy_strength")
    assert committed > low


def test_profiles_z_scoring_handles_constant_feature() -> None:
    """A constant profile column must not produce NaN scores (div-by-zero guard)."""
    rng = np.random.default_rng(7)
    n = 300
    df = pd.DataFrame(
        {
            "rural_flag": rng.integers(0, 2, n),
            "metro_flag": rng.integers(0, 2, n),
            "youth_flag": np.zeros(n, dtype=int),  # constant → zero variance
            "structural_dependency_encoded": rng.integers(0, 2, n),
            "preference_proxy_strength": rng.random(n),
            # cluster_profiles reads the one-hot indicators (IMP-A02), not the
            # raw encoded scalar
            "preference_proxy_is_B": rng.integers(0, 2, n).astype(float),
            "preference_proxy_is_none": rng.integers(0, 2, n).astype(float),
            "nbi_stress_prior_scaled": rng.random(n),
        }
    )
    labels = rng.integers(0, 6, n)
    mapping = assign_segment_labels(df, labels)
    assert len(set(mapping.values())) == 6
