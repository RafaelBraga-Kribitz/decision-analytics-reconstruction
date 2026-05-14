# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false
"""Reachability feature engineering for Module A."""

from __future__ import annotations

import pandas as pd


def build_reachability_features(df: pd.DataFrame) -> pd.DataFrame:
    """Combine digital and broadcast penetration into reachability indices and tiers.

    Args:
        df: Population frame with internet access, WhatsApp or TV or radio penetration,
            and ``rural_flag``.

    Returns:
        Copy of ``df`` with ``reachability_*`` columns, tertile labels, and compound
        access flags for downstream propensity and media aggregates.

    Raises:
        KeyError: If required input columns are absent.

    Example::

        reachability = build_reachability_features(behavioral_frame)
    """
    out = df.copy()

    out["reachability_digital"] = out["internet_access_flag"].astype(float) * out[
        "media_penetration_whatsapp"
    ].astype(float)
    out["reachability_broadcast_tv"] = out["media_penetration_tv"].astype(float)
    out["reachability_broadcast_radio"] = out["media_penetration_radio"].astype(float)

    # Q1 2018 Latin America digital advertising channels
    for ad_channel in ["facebook_ads", "instagram_ads", "google_ads", "linkedin_ads"]:
        col_name = f"media_penetration_{ad_channel}"
        if col_name in out.columns:
            out[f"reachability_{ad_channel}"] = (
                out["internet_access_flag"].astype(float)
                * out[col_name].astype(float)
            )
        else:
            out[f"reachability_{ad_channel}"] = 0.0

    out["reachability_index"] = (
        0.25 * out["reachability_digital"]
        + 0.25 * out["reachability_broadcast_tv"]
        + 0.15 * out["reachability_broadcast_radio"]
        + 0.15 * out["reachability_facebook_ads"]
        + 0.10 * out["reachability_instagram_ads"]
        + 0.10 * out["reachability_google_ads"]
    ).clip(0.0, 1.0)

    q_low = out["reachability_index"].quantile(0.33)
    q_high = out["reachability_index"].quantile(0.66)
    out["reachability_tier"] = "medium"
    out.loc[out["reachability_index"] <= q_low, "reachability_tier"] = "low"
    out.loc[out["reachability_index"] >= q_high, "reachability_tier"] = "high"

    out["urban_digital_compound"] = (~out["rural_flag"]) & out["internet_access_flag"]
    out["rural_offline_compound"] = out["rural_flag"] & (~out["internet_access_flag"])

    return out
