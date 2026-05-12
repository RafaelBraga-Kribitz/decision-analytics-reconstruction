"""Schema and calibration validation gates for Module A."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import pandas as pd

from population_segmentation.utils.schema import CANONICAL_DEPARTMENTS, CANONICAL_GENDER


class QAGateFailure(Exception):  # noqa: N818  # Stable QA API symbol; not renamed to *Error.
    """Raised when any QA gate fails."""


@dataclass(frozen=True)
class AnchorCheck:
    name: str
    observed: float
    expected: float
    tolerance: float
    passed: bool


def validate_schema(df: pd.DataFrame) -> None:
    """Validate that ``df`` satisfies the Module A clean-population column contract.

    Args:
        df: Clean or nearly-clean population table after ``clean_population``.

    Returns:
        ``None``.

    Raises:
        QAGateFailure: If required columns are missing, formats are invalid, or
            canonical value sets are violated.

    Example:
        Intended for use immediately after ``clean_population``; supply anchors from
        ``calibration_anchors.yaml`` before downstream modeling.
    """
    required = [
        "entity_id",
        "cedula",
        "department",
        "municipality",
        "gender",
        "age_on_event_date",
        "rural_flag",
        "phone",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise QAGateFailure(f"Missing required columns: {missing}")

    if not df["cedula"].astype(str).str.match(r"^\d{8}$").all():
        raise QAGateFailure("cedula must match ^\\d{8}$ for all rows")

    if bool(df["department"].isna().any()):
        raise QAGateFailure("department contains null values")
    bad_departments = set(df["department"].dropna().unique()) - CANONICAL_DEPARTMENTS
    if bad_departments:
        raise QAGateFailure(f"Non-canonical departments found: {sorted(bad_departments)}")

    if df["municipality"].isna().mean() >= 0.001:
        raise QAGateFailure("municipality null rate must be < 0.1%")

    bad_gender = set(df["gender"].dropna().unique()) - CANONICAL_GENDER
    if bad_gender:
        raise QAGateFailure(f"Non-canonical gender values: {sorted(bad_gender)}")

    if not df["age_on_event_date"].between(18, 115).all():
        raise QAGateFailure("age_on_event_date must be within [18, 115]")

    if bool(df["rural_flag"].isna().any()):
        raise QAGateFailure("rural_flag cannot be null")

    if not df["phone"].astype(str).str.match(r"^\+595\d{9}$").all():
        raise QAGateFailure("phone must match +595XXXXXXXXX")


def validate_calibration_anchors(df: pd.DataFrame, anchors: dict[str, Any]) -> dict[str, Any]:
    """Compare ``df`` marginals to YAML calibration anchors with sampling-aware tolerances.

    Args:
        df: Population frame containing ``rural_flag``, ``gender``,
            ``language_census_bucket``, etc.
        anchors: Parsed ``calibration_anchors.yaml`` (demographics, language, tolerances).

    Returns:
        Dict with keys ``passed`` (bool), ``checks`` (list of serialized
        :class:`AnchorCheck`), and ``failed`` (list of failed checks).

    Raises:
        KeyError: If ``anchors`` is missing expected nested keys.

    Example:
        Compare rural share, male share, and language bucket rates to anchors before
        exporting propensity or segment artifacts.
    """
    checks: list[AnchorCheck] = []
    n = max(len(df), 1)
    # Sampling-aware floor so dev sample sizes do not fail on random noise.
    sampling_floor = 2.0 / math.sqrt(n)

    # Rural share
    expected_rural = float(anchors["demographics"]["rural_share"])
    tol_rural = max(float(anchors["tolerances"]["rural_share_pp"]), sampling_floor)
    obs_rural = float(df["rural_flag"].mean())
    checks.append(
        AnchorCheck(
            "rural_share",
            obs_rural,
            expected_rural,
            tol_rural,
            abs(obs_rural - expected_rural) <= tol_rural,
        )
    )

    # Gender shares
    expected_m = float(anchors["demographics"]["male_share"])
    obs_m = float((df["gender"] == "M").mean())
    tol_gender = max(float(anchors["tolerances"]["gender_rate_pp"]), sampling_floor)
    checks.append(
        AnchorCheck(
            "male_share", obs_m, expected_m, tol_gender, abs(obs_m - expected_m) <= tol_gender
        )
    )

    # Language shares
    tol_lang = max(float(anchors["tolerances"]["language_share_pp"]), sampling_floor)
    for k in ("jopara_bilingual", "guarani_only", "spanish_only"):
        expected = float(anchors["language"][k])
        observed = float((df["language_census_bucket"] == k).mean())
        checks.append(
            AnchorCheck(
                f"language_{k}", observed, expected, tol_lang, abs(observed - expected) <= tol_lang
            )
        )

    failed = [c for c in checks if not c.passed]
    return {
        "passed": len(failed) == 0,
        "checks": [c.__dict__ for c in checks],
        "failed": [c.__dict__ for c in failed],
    }


def run_all_validations(df: pd.DataFrame, anchors: dict[str, Any]) -> dict[str, Any]:
    """Run :func:`validate_schema` then :func:`validate_calibration_anchors`.

    Args:
        df: Population frame to validate.
        anchors: Parsed calibration anchors YAML.

    Returns:
        Anchor check report dict (same shape as :func:`validate_calibration_anchors`).

    Raises:
        QAGateFailure: If schema validation fails or any anchor check is outside tolerance.

    Example:
        Call from export or QA scripts after schema checks and before writing parquet.
    """
    validate_schema(df)
    anchor_res = validate_calibration_anchors(df, anchors)
    if not anchor_res["passed"]:
        raise QAGateFailure(f"Calibration anchor validation failed: {anchor_res['failed']}")
    return anchor_res
