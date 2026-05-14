# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false
"""Behavioral feature engineering for Module A."""

from __future__ import annotations

import pandas as pd


def build_behavioral_features(df: pd.DataFrame) -> pd.DataFrame:
    """Encode preference proxy, structural dependency, NBI stress, and language signals.

    Args:
        df: Clean population frame with preference proxy, NBI stress, language census
            bucket, jopara flag, and structural dependency proxy columns.

    Returns:
        Copy of ``df`` with scaled and encoded behavioral columns for segmentation and
        participation propensity.

    Raises:
        KeyError: If required input columns are absent.

    Example::

        behavioral = build_behavioral_features(demographic_frame)
    """
    out = df.copy()

    pref_map = {"A": 0, "B": 1, "other": 2, "none": 3}
    out["preference_proxy_encoded"] = (
        out["preference_proxy"].map(lambda x: pref_map.get(x, 3)).fillna(3).astype(int)
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
