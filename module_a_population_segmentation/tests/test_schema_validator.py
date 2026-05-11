"""Tests for pandera runtime schema contracts (evaluation/schema_validator.py).

TDD: each test was written to a failing assertion, then schema_validator.py was
implemented to make it pass.
"""

from __future__ import annotations

import pandas as pd
import pytest
from pandera.errors import SchemaError

from population_segmentation.evaluation.schema_validator import (
    validate_clean_population,
    validate_feature_frame,
)


# ─── Fixtures ────────────────────────────────────────────────────────────────


def _valid_clean_row() -> dict:
    return {
        "entity_id": 1,
        "cedula": "12345678",
        "department": "Central",
        "municipality": "Luque",
        "gender": "M",
        "age_on_event_date": 35,
        "rural_flag": False,
        "phone": "+595971234567",
        "language_census_bucket": "jopara_bilingual",
        "rural_flag_derived": True,
        "internet_access_flag": True,
        "structural_dependency_proxy": False,
        "cedula_invalid": False,
        "age_out_of_range": False,
    }


def _valid_clean_df(n: int = 5) -> pd.DataFrame:
    rows = []
    for i in range(n):
        row = _valid_clean_row()
        row["entity_id"] = i
        row["cedula"] = str(10000000 + i).zfill(8)
        rows.append(row)
    return pd.DataFrame(rows)


def _valid_feature_row() -> dict:
    return {
        "entity_id": 1,
        "age_bin_encoded": 2,
        "gender_encoded": 0,
        "youth_flag": False,
        "senior_flag": False,
        "language_jopara_encoded": 1,
        "nbi_stress_prior_scaled": 0.25,
        "reachability_digital": 0.73,
        "reachability_broadcast_tv": 0.80,
        "reachability_broadcast_radio": 0.60,
        "metro_flag": True,
        "chaco_flag": False,
        "rural_offline_compound": 0.10,
    }


def _valid_feature_df(n: int = 5) -> pd.DataFrame:
    rows = []
    for i in range(n):
        row = _valid_feature_row()
        row["entity_id"] = i
        rows.append(row)
    return pd.DataFrame(rows)


# ─── Clean population schema ─────────────────────────────────────────────────


class TestCleanPopulationSchemaValid:
    def test_valid_dataframe_passes(self) -> None:
        validate_clean_population(_valid_clean_df())

    def test_allows_extra_columns(self) -> None:
        df = _valid_clean_df()
        df["extra_col"] = "ignored"
        validate_clean_population(df)

    def test_passes_with_unknown_gender(self) -> None:
        df = _valid_clean_df(3)
        df["gender"] = "unknown"
        validate_clean_population(df)

    def test_passes_with_guarani_only_language(self) -> None:
        df = _valid_clean_df(3)
        df["language_census_bucket"] = "guarani_only"
        validate_clean_population(df)


class TestCleanPopulationSchemaViolations:
    def test_invalid_cedula_format_raises(self) -> None:
        df = _valid_clean_df()
        df.loc[0, "cedula"] = "1234"  # too short
        with pytest.raises(SchemaError):
            validate_clean_population(df)

    def test_non_canonical_department_raises(self) -> None:
        df = _valid_clean_df()
        df.loc[0, "department"] = "Cordilera"  # typo variant
        with pytest.raises(SchemaError):
            validate_clean_population(df)

    def test_age_below_18_raises(self) -> None:
        df = _valid_clean_df()
        df.loc[0, "age_on_event_date"] = 15
        with pytest.raises(SchemaError):
            validate_clean_population(df)

    def test_age_above_115_raises(self) -> None:
        df = _valid_clean_df()
        df.loc[0, "age_on_event_date"] = 120
        with pytest.raises(SchemaError):
            validate_clean_population(df)

    def test_non_canonical_gender_raises(self) -> None:
        df = _valid_clean_df()
        df.loc[0, "gender"] = "Masculino"  # unnormalized variant
        with pytest.raises(SchemaError):
            validate_clean_population(df)

    def test_non_canonical_language_raises(self) -> None:
        df = _valid_clean_df()
        df.loc[0, "language_census_bucket"] = "bilingual"  # non-canonical
        with pytest.raises(SchemaError):
            validate_clean_population(df)

    def test_malformed_phone_raises(self) -> None:
        df = _valid_clean_df()
        df.loc[0, "phone"] = "0971234567"  # missing +595 prefix
        with pytest.raises(SchemaError):
            validate_clean_population(df)

    def test_duplicate_entity_id_raises(self) -> None:
        df = _valid_clean_df()
        df.loc[1, "entity_id"] = df.loc[0, "entity_id"]  # force duplicate
        with pytest.raises(SchemaError):
            validate_clean_population(df)

    def test_null_rural_flag_raises(self) -> None:
        df = _valid_clean_df()
        df["rural_flag"] = df["rural_flag"].astype(object)
        df.loc[0, "rural_flag"] = None
        with pytest.raises(SchemaError):
            validate_clean_population(df)


# ─── Feature frame schema ─────────────────────────────────────────────────────


class TestFeatureFrameSchemaValid:
    def test_valid_dataframe_passes(self) -> None:
        validate_feature_frame(_valid_feature_df())

    def test_allows_extra_columns(self) -> None:
        df = _valid_feature_df()
        df["extra"] = 0.0
        validate_feature_frame(df)

    def test_zero_reachability_is_valid(self) -> None:
        df = _valid_feature_df()
        df["reachability_digital"] = 0.0
        validate_feature_frame(df)

    def test_max_reachability_is_valid(self) -> None:
        df = _valid_feature_df()
        df["reachability_digital"] = 1.0
        validate_feature_frame(df)


class TestFeatureFrameSchemaViolations:
    def test_reachability_above_1_raises(self) -> None:
        df = _valid_feature_df()
        df.loc[0, "reachability_digital"] = 1.5
        with pytest.raises(SchemaError):
            validate_feature_frame(df)

    def test_reachability_below_0_raises(self) -> None:
        df = _valid_feature_df()
        df.loc[0, "reachability_broadcast_tv"] = -0.1
        with pytest.raises(SchemaError):
            validate_feature_frame(df)

    def test_nbi_above_1_raises(self) -> None:
        df = _valid_feature_df()
        df.loc[0, "nbi_stress_prior_scaled"] = 1.2
        with pytest.raises(SchemaError):
            validate_feature_frame(df)

    def test_invalid_gender_encoded_raises(self) -> None:
        df = _valid_feature_df()
        df.loc[0, "gender_encoded"] = 9  # not in {0, 1, 2}
        with pytest.raises(SchemaError):
            validate_feature_frame(df)

    def test_age_bin_encoded_out_of_range_raises(self) -> None:
        df = _valid_feature_df()
        df.loc[0, "age_bin_encoded"] = 10
        with pytest.raises(SchemaError):
            validate_feature_frame(df)
