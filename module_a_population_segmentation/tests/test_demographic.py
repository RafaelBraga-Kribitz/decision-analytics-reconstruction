"""TDD tests for demographic feature engineering."""

from __future__ import annotations

import pandas as pd


def test_build_demographic_features_adds_expected_columns_and_encodings() -> None:
    from population_segmentation.features.demographic import build_demographic_features

    df = pd.DataFrame(
        {
            "age_on_event_date": [19, 29, 40, 58, 72],
            "gender": ["M", "F", "unknown", "F", "M"],
            "department": ["Central", "Asuncion", "Boqueron", "Guaira", "Alto Paraguay"],
        }
    )

    out = build_demographic_features(df)

    expected_cols = {
        "age_bin",
        "age_bin_encoded",
        "gender_encoded",
        "youth_flag",
        "senior_flag",
        "department_region",
        "metro_flag",
        "chaco_flag",
    }
    assert expected_cols.issubset(set(out.columns))

    assert out["age_bin"].tolist() == ["18_24", "25_34", "35_49", "50_64", "65_plus"]
    assert out["age_bin_encoded"].tolist() == [0, 1, 2, 3, 4]
    assert out["gender_encoded"].tolist() == [1.0, 0.0, 0.5, 0.0, 1.0]
    assert out["youth_flag"].tolist() == [True, False, False, False, False]
    assert out["senior_flag"].tolist() == [False, False, False, False, True]
    assert out["metro_flag"].tolist() == [True, True, False, False, False]
    assert out["chaco_flag"].tolist() == [False, False, True, False, True]
