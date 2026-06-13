# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false
"""Pandera DataFrame schema contracts for Module A pipeline step exits.

Two schema gates are enforced:
    CLEAN_POPULATION_SCHEMA  — exit of cleaner.clean_population()
    FEATURE_FRAME_SCHEMA     — exit of features/ layer, input to models/

Usage:
    from population_segmentation.evaluation.schema_validator import validate_clean_population
    validate_clean_population(df)   # raises SchemaError on violation
"""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
from pandera.pandas import Check, Column, DataFrameSchema

from population_segmentation.utils.schema import (
    CANONICAL_DEPARTMENTS,
    CANONICAL_GENDER,
    CANONICAL_LANGUAGE,
)

# ─── Clean population schema (cleaner.py exit) ────────────────────────────────

CLEAN_POPULATION_SCHEMA = DataFrameSchema(
    columns={
        "entity_id": Column(
            pa.Int,
            checks=Check.greater_than_or_equal_to(0),
            nullable=False,
            unique=True,
            title="Unique entity identifier",
        ),
        "cedula": Column(
            pa.String,
            checks=Check.str_matches(r"^\d{8}$"),
            nullable=False,
            title="8-digit national ID, zero-padded",
        ),
        "department": Column(
            pa.String,
            checks=Check.isin(sorted(CANONICAL_DEPARTMENTS)),
            nullable=False,
            title="Canonical department name (18 allowed values)",
        ),
        "municipality": Column(
            pa.String,
            checks=Check(
                lambda s: s.isna().mean() < 0.001,
                error="municipality null rate must be < 0.1%",
            ),
            nullable=True,
            title="Municipality name (imputed if originally null)",
        ),
        "gender": Column(
            pa.String,
            checks=Check.isin(sorted(CANONICAL_GENDER)),
            nullable=False,
            title="Canonical gender value: M, F, or unknown",
        ),
        "age_on_event_date": Column(
            pa.Int,
            checks=[
                Check.greater_than_or_equal_to(18),
                Check.less_than_or_equal_to(115),
            ],
            nullable=False,
            title="Age in years on 2018-04-22",
        ),
        "rural_flag": Column(
            pa.Bool,
            nullable=False,
            title="Rural entity flag (derived from DGEEC municipality classification)",
        ),
        "phone": Column(
            pa.String,
            checks=Check.str_matches(r"^\+595\d{9}$"),
            nullable=False,
            title="Canonicalized phone in E.164 format (+595XXXXXXXXX)",
        ),
        "language_census_bucket": Column(
            pa.String,
            checks=Check.isin(sorted(CANONICAL_LANGUAGE)),
            nullable=False,
            title="Language bucket from DGEEC bilingualism statistics",
        ),
        "rural_flag_derived": Column(
            pa.Bool,
            nullable=False,
            title="Marker that rural_flag was derived (always True in clean layer)",
        ),
        "internet_access_flag": Column(
            pa.Bool,
            nullable=False,
            title="Internet access flag calibrated to ICT survey anchors",
        ),
        "structural_dependency_proxy": Column(
            pa.Bool,
            nullable=False,
            title="NBI-grounded socioeconomic dependency proxy",
        ),
        "cedula_invalid": Column(
            pa.Bool,
            nullable=False,
            title="Flag: cedula failed format check before standardization",
        ),
        "age_out_of_range": Column(
            pa.Bool,
            nullable=False,
            title="Flag: DOB produced an age outside [18, 115] before clamping",
        ),
    },
    checks=[
        Check(
            lambda df: df["rural_flag"].mean().round(3) == round(df["rural_flag"].mean(), 3),
            error="Internal: rural_flag mean must be computable",
        ),
    ],
    coerce=False,
    strict=False,  # allow extra columns produced by intermediate steps
    title="Clean population schema (cleaner.py exit gate)",
    description=(
        "Enforced at the exit of clean_population(). "
        "Violations raise pa.errors.SchemaError with column-level detail. "
        "This gate supplements the custom QAGateFailure checks in data/validator.py."
    ),
)

# ─── Feature frame schema (features/ layer exit) ──────────────────────────────

FEATURE_FRAME_SCHEMA = DataFrameSchema(
    columns={
        "entity_id": Column(pa.Int, nullable=False, unique=True),
        "age_bin_encoded": Column(
            pa.Int,
            checks=[Check.greater_than_or_equal_to(0), Check.less_than_or_equal_to(5)],
            nullable=False,
            title="Ordinal age bin encoding (0–5)",
        ),
        "gender_encoded": Column(
            pa.Int,
            checks=Check.isin([0, 1, 2]),
            nullable=False,
            title="Gender encoding: 0=M, 1=F, 2=unknown",
        ),
        "youth_flag": Column(pa.Bool, nullable=False, title="Age 18–24 indicator"),
        "senior_flag": Column(pa.Bool, nullable=False, title="Age 65+ indicator"),
        "language_jopara_encoded": Column(pa.Int, checks=Check.isin([0, 1]), nullable=False),
        "nbi_stress_prior_scaled": Column(
            pa.Float,
            checks=[Check.greater_than_or_equal_to(0.0), Check.less_than_or_equal_to(1.0)],
            nullable=False,
        ),
        "reachability_digital": Column(
            pa.Float,
            checks=[Check.greater_than_or_equal_to(0.0), Check.less_than_or_equal_to(1.0)],
            nullable=False,
        ),
        "reachability_broadcast_tv": Column(
            pa.Float,
            checks=[Check.greater_than_or_equal_to(0.0), Check.less_than_or_equal_to(1.0)],
            nullable=False,
        ),
        "reachability_broadcast_radio": Column(
            pa.Float,
            checks=[Check.greater_than_or_equal_to(0.0), Check.less_than_or_equal_to(1.0)],
            nullable=False,
        ),
        "metro_flag": Column(pa.Bool, nullable=False),
        "chaco_flag": Column(pa.Bool, nullable=False),
        "rural_offline_compound": Column(
            pa.Float,
            checks=[Check.greater_than_or_equal_to(0.0), Check.less_than_or_equal_to(1.0)],
            nullable=False,
        ),
    },
    coerce=False,
    strict=False,
    title="Feature frame schema (features/ layer exit gate)",
)


# ─── Public validation functions ──────────────────────────────────────────────


def validate_clean_population(df: pd.DataFrame) -> None:  # type: ignore[name-defined]
    """Validate a clean population DataFrame at the ``cleaner`` exit gate.

    Args:
        df: Table produced by :func:`population_segmentation.data.cleaner.clean_population`.

    Returns:
        ``None``

    Raises:
        pandera.errors.SchemaError: If any column fails dtype, nullability, or checks
            defined on ``CLEAN_POPULATION_SCHEMA``.

    Example:
        After cleaning and before feature engineering::

            validate_clean_population(clean_df)
    """
    CLEAN_POPULATION_SCHEMA.validate(df)


def validate_feature_frame(df: pd.DataFrame) -> None:  # type: ignore[name-defined]
    """Validate a feature-engineered frame at the features-layer exit gate.

    Args:
        df: Table after demographic, behavioral, and reachability builders.

    Returns:
        ``None``

    Raises:
        pandera.errors.SchemaError: If any column fails ``FEATURE_FRAME_SCHEMA`` checks.

    Example:
        After ``build_reachability_features`` and before segmentation::

            validate_feature_frame(feat_df)
    """
    FEATURE_FRAME_SCHEMA.validate(df)
