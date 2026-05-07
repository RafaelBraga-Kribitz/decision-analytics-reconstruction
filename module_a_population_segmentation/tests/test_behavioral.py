"""TDD tests for behavioral feature engineering."""

from __future__ import annotations

import pandas as pd


def test_build_behavioral_features_adds_expected_columns() -> None:
    from population_segmentation.features.behavioral import build_behavioral_features

    df = pd.DataFrame(
        {
            "preference_proxy": ["A", "B", "other", "none"],
            "preference_proxy_strength": [0.9, 0.4, 0.1, 0.7],
            "structural_dependency_proxy": [True, False, True, False],
            "nbi_stress_prior": [0.2, 0.6, 0.9, 0.1],
            "language_census_bucket": [
                "jopara_bilingual",
                "guarani_only",
                "spanish_only",
                "other",
            ],
            "jopara_flag": [True, False, False, False],
        }
    )

    out = build_behavioral_features(df)

    assert out["preference_proxy_encoded"].tolist() == [0, 1, 2, 3]
    assert out["structural_dependency_encoded"].tolist() == [1, 0, 1, 0]
    assert out["language_jopara_encoded"].tolist() == [1, 0, 0, 0]
    assert out["language_guarani_flag"].tolist() == [False, True, False, False]
    assert out["nbi_stress_prior_scaled"].between(0.0, 1.0).all()
