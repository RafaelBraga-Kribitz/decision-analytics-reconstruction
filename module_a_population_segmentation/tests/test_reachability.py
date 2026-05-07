"""TDD tests for reachability feature engineering."""

from __future__ import annotations

import pandas as pd


def test_build_reachability_features_adds_expected_columns() -> None:
    from population_segmentation.features.reachability import build_reachability_features

    df = pd.DataFrame(
        {
            "internet_access_flag": [True, False, True, False],
            "media_penetration_whatsapp": [0.9, 0.2, 0.7, 0.1],
            "media_penetration_tv": [0.95, 0.8, 0.6, 0.5],
            "media_penetration_radio": [0.7, 0.6, 0.8, 0.4],
            "rural_flag": [False, True, False, True],
        }
    )

    out = build_reachability_features(df)
    for col in [
        "reachability_digital",
        "reachability_broadcast_tv",
        "reachability_broadcast_radio",
        "reachability_index",
        "reachability_tier",
        "urban_digital_compound",
        "rural_offline_compound",
    ]:
        assert col in out.columns

    assert out["reachability_index"].between(0.0, 1.0).all()
    assert set(out["reachability_tier"].unique()).issubset({"low", "medium", "high"})
