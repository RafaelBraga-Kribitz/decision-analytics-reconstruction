"""Behavioral feature engineering for Module A."""

from __future__ import annotations

import pandas as pd


def build_behavioral_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    pref_map = {"A": 0, "B": 1, "other": 2, "none": 3}
    out["preference_proxy_encoded"] = (
        out["preference_proxy"].replace(pref_map).fillna(3).astype(int)
    )

    out["structural_dependency_encoded"] = out["structural_dependency_proxy"].astype(int)

    min_val = out["nbi_stress_prior"].min()
    max_val = out["nbi_stress_prior"].max()
    if max_val == min_val:
        out["nbi_stress_prior_scaled"] = 0.0
    else:
        out["nbi_stress_prior_scaled"] = (out["nbi_stress_prior"] - min_val) / (max_val - min_val)

    out["language_jopara_encoded"] = out["jopara_flag"].astype(int)
    out["language_guarani_flag"] = out["language_census_bucket"] == "guarani_only"

    return out
