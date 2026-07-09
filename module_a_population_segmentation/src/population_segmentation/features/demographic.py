# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false
"""Demographic feature engineering for Module A."""

from __future__ import annotations

import pandas as pd


def _age_bin(age: int) -> str:
    if age <= 24:
        return "18_24"
    if age <= 34:
        return "25_34"
    if age <= 49:
        return "35_49"
    if age <= 64:
        return "50_64"
    return "65_plus"


def build_demographic_features(df: pd.DataFrame) -> pd.DataFrame:
    """Derive age bins, gender encoding, youth or senior flags, and region indicators.

    Args:
        df: Clean population frame with ``age_on_event_date``, ``gender``, and
            ``department``.

    Returns:
        Copy of ``df`` with demographic feature columns (for example ``age_bin``,
        ``gender_encoded``, ``chaco_flag``, ``metro_flag``).

    Raises:
        KeyError: If required input columns are absent.

    Example::

        demographic = build_demographic_features(clean_df)
    """
    out = df.copy()
    out["age_bin"] = out["age_on_event_date"].astype(int).map(_age_bin)

    age_order = {
        "18_24": 0,
        "25_34": 1,
        "35_49": 2,
        "50_64": 3,
        "65_plus": 4,
    }
    out["age_bin_encoded"] = out["age_bin"].map(lambda x: age_order.get(x, 0)).astype(int)

    gender_map = {"M": 1.0, "F": 0.0, "unknown": 0.5}
    out["gender_encoded"] = out["gender"].map(lambda x: gender_map.get(x, 0.5)).astype(float)

    # One-hot indicators for the clustering matrix (IMP-A02): the scalar
    # encoding above places "unknown" at the arithmetic midpoint of M/F —
    # a false metric relationship for Euclidean methods. Full one-hot keeps
    # every pairwise cross-category distance equal.
    _gender_norm = out["gender"].map(lambda x: x if x in gender_map else "unknown")
    for _cat in ("M", "F", "unknown"):
        out[f"gender_is_{_cat}"] = _gender_norm.eq(_cat).astype(float)

    out["youth_flag"] = out["age_on_event_date"].between(18, 24)
    out["senior_flag"] = out["age_on_event_date"] >= 65

    chaco = {"Presidente Hayes", "Boqueron", "Alto Paraguay"}
    out["chaco_flag"] = out["department"].isin(list(chaco))
    out["department_region"] = out["chaco_flag"].map(lambda x: "CHACO" if x else "ORIENTAL")

    metro = {"Central", "Asuncion"}
    out["metro_flag"] = out["department"].isin(list(metro))

    return out
