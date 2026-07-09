"""Cross-run comparability of fixed-reference features (IMP-A05 / issue #56).

reachability_tier and nbi_stress_prior_scaled must be pure per-row functions
of the raw inputs — identical for the same row regardless of the surrounding
sample's size or distribution.
"""

from __future__ import annotations

import pandas as pd

from population_segmentation.features.behavioral import build_behavioral_features
from population_segmentation.features.reachability import (
    build_reachability_features,
    check_reachability_tier_drift,
    load_reachability_tier_bounds,
)


def _base_rows() -> pd.DataFrame:
    """Shared raw rows present in both differently-sized samples."""
    return pd.DataFrame(
        {
            "entity_id": ["s1", "s2", "s3", "s4"],
            "internet_access_flag": [True, False, True, False],
            "media_penetration_whatsapp": [0.9, 0.1, 0.5, 0.2],
            "media_penetration_tv": [0.8, 0.3, 0.5, 0.9],
            "media_penetration_radio": [0.2, 0.9, 0.5, 0.4],
            "rural_flag": [False, True, False, True],
            "preference_proxy": ["A", "none", "B", "other"],
            "preference_proxy_strength": [0.8, 0.0, 0.5, 0.3],
            "structural_dependency_proxy": [False, True, False, True],
            "nbi_stress_prior": [0.05, 0.85, 0.40, 0.60],
            "jopara_flag": [True, False, True, False],
            "language_census_bucket": ["jopara", "guarani_only", "jopara", "spanish_only"],
        }
    )


def _filler_rows(n: int, seed_offset: int) -> pd.DataFrame:
    """Distribution-shifting filler distinct between the two runs."""
    base = _base_rows().iloc[[0]].copy()
    rows = pd.concat([base] * n, ignore_index=True)
    rows["entity_id"] = [f"f{seed_offset}_{i}" for i in range(n)]
    # push the filler's index values toward one extreme so sample quantiles
    # (the old behavior) would move between the two runs
    rows["media_penetration_whatsapp"] = 0.05 + (seed_offset * 0.3)
    rows["nbi_stress_prior"] = 0.02 + (seed_offset * 0.45)
    return rows


def _features_for(sample: pd.DataFrame) -> pd.DataFrame:
    return build_reachability_features(build_behavioral_features(sample))


def test_shared_rows_identical_across_sample_sizes() -> None:
    small = pd.concat([_base_rows(), _filler_rows(6, 1)], ignore_index=True)
    large = pd.concat([_base_rows(), _filler_rows(60, 2)], ignore_index=True)

    f_small = _features_for(small).set_index("entity_id")
    f_large = _features_for(large).set_index("entity_id")

    shared = ["s1", "s2", "s3", "s4"]
    for col in ("reachability_tier", "nbi_stress_prior_scaled"):
        left = f_small.loc[shared, col]
        right = f_large.loc[shared, col]
        pd.testing.assert_series_equal(left, right, check_names=False)


def test_tiers_follow_frozen_bounds_not_sample() -> None:
    bounds = load_reachability_tier_bounds()
    frame = _features_for(pd.concat([_base_rows(), _filler_rows(20, 1)], ignore_index=True))
    low = frame[frame["reachability_index"] <= bounds["low_max"]]
    high = frame[frame["reachability_index"] >= bounds["high_min"]]
    assert (low["reachability_tier"] == "low").all()
    assert (high["reachability_tier"] == "high").all()


def test_nbi_scaled_is_identity_on_contract_range() -> None:
    frame = build_behavioral_features(_base_rows())
    pd.testing.assert_series_equal(
        frame["nbi_stress_prior_scaled"],
        frame["nbi_stress_prior"].clip(0.0, 1.0),
        check_names=False,
    )


def test_drift_check_flags_out_of_band_tier() -> None:
    # A frame where every row lands in one tier must warn for all three tiers
    # (one over max_share, two under min_share).
    frame = _features_for(_filler_rows(30, 0))
    warnings = check_reachability_tier_drift(frame)
    assert len(warnings) == 3
    assert all("drift" in w for w in warnings)
