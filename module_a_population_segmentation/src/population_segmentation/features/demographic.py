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
    out = df.copy()
    out["age_bin"] = out["age_on_event_date"].astype(int).map(_age_bin)

    age_order = {
        "18_24": 0,
        "25_34": 1,
        "35_49": 2,
        "50_64": 3,
        "65_plus": 4,
    }
    out["age_bin_encoded"] = out["age_bin"].replace(age_order).astype(int)

    gender_map = {"M": 1.0, "F": 0.0, "unknown": 0.5}
    out["gender_encoded"] = out["gender"].replace(gender_map).fillna(0.5).astype(float)

    out["youth_flag"] = out["age_on_event_date"].between(18, 24)
    out["senior_flag"] = out["age_on_event_date"] >= 65

    chaco = {"Presidente Hayes", "Boqueron", "Alto Paraguay"}
    out["chaco_flag"] = out["department"].isin(list(chaco))
    out["department_region"] = out["chaco_flag"].replace({True: "CHACO", False: "ORIENTAL"})

    metro = {"Central", "Asuncion"}
    out["metro_flag"] = out["department"].isin(list(metro))

    return out
