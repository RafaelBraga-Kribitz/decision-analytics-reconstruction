"""Reachability feature engineering for Module A."""

from __future__ import annotations

import pandas as pd


def build_reachability_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    out["reachability_digital"] = out["internet_access_flag"].astype(float) * out[
        "media_penetration_whatsapp"
    ].astype(float)
    out["reachability_broadcast_tv"] = out["media_penetration_tv"].astype(float)
    out["reachability_broadcast_radio"] = out["media_penetration_radio"].astype(float)

    out["reachability_index"] = (
        0.40 * out["reachability_digital"]
        + 0.35 * out["reachability_broadcast_tv"]
        + 0.25 * out["reachability_broadcast_radio"]
    ).clip(0.0, 1.0)

    q_low = out["reachability_index"].quantile(0.33)
    q_high = out["reachability_index"].quantile(0.66)
    out["reachability_tier"] = "medium"
    out.loc[out["reachability_index"] <= q_low, "reachability_tier"] = "low"
    out.loc[out["reachability_index"] >= q_high, "reachability_tier"] = "high"

    out["urban_digital_compound"] = (~out["rural_flag"]) & out["internet_access_flag"]
    out["rural_offline_compound"] = out["rural_flag"] & (~out["internet_access_flag"])

    return out
