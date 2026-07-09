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

    # generator.py clips raw NBI stress to the fixed [0, 1] range
    # (np.clip(nbi_vals + nbi_noise, 0.0, 1.0), data/generator.py:335). Scale
    # against that contractual bound, not the sample's own min()/max(), so the
    # same raw value maps identically across sample sizes and seeds (IMP-A05).
    out["nbi_stress_prior_scaled"] = out["nbi_stress_prior"].clip(0.0, 1.0)

    out["language_jopara_encoded"] = out["jopara_flag"].astype(int)
    out["language_guarani_flag"] = out["language_census_bucket"] == "guarani_only"

    return out
