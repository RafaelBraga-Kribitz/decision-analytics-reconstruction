# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false
"""Reachability feature engineering for Module A."""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

import pandas as pd
import yaml

_DEFAULT_MODEL_PARAMS = Path(__file__).resolve().parents[3] / "config" / "model_params.yaml"


class ReachabilityWeights(TypedDict):
    digital: float
    broadcast_tv: float
    broadcast_radio: float


def load_reachability_weights(config_path: Path | None = None) -> ReachabilityWeights:
    """Load reachability index weights from ``model_params.yaml``.

    Args:
        config_path: Optional override for the YAML path; defaults to
            ``module_a_population_segmentation/config/model_params.yaml``.

    Returns:
        Weight triple for digital, broadcast TV, and broadcast radio indices.

    Raises:
        FileNotFoundError: When ``config_path`` does not exist.
        KeyError: When ``reachability_weights`` is missing from the YAML.

    Example:
        ``load_reachability_weights()["digital"]``.
    """
    path = config_path or _DEFAULT_MODEL_PARAMS
    with open(path, encoding="utf-8") as handle:
        params = yaml.safe_load(handle)
    raw = params["reachability_weights"]
    return {
        "digital": float(raw["digital"]),
        "broadcast_tv": float(raw["broadcast_tv"]),
        "broadcast_radio": float(raw["broadcast_radio"]),
    }


def build_reachability_features(
    df: pd.DataFrame,
    *,
    reachability_weights: ReachabilityWeights | None = None,
) -> pd.DataFrame:
    """Combine digital and broadcast penetration into reachability indices and tiers.

    Args:
        df: Population frame with internet access, WhatsApp or TV or radio penetration,
            and ``rural_flag``.
        reachability_weights: Optional override for index weights; defaults to
            ``model_params.yaml`` ``reachability_weights``.

    Returns:
        Copy of ``df`` with ``reachability_*`` columns, tertile labels, and compound
        access flags for downstream propensity and media aggregates.

    Raises:
        KeyError: If required input columns are absent.

    Example::

        reachability = build_reachability_features(behavioral_frame)
    """
    out = df.copy()
    weights = reachability_weights or load_reachability_weights()

    out["reachability_digital"] = out["internet_access_flag"].astype(float) * out[
        "media_penetration_whatsapp"
    ].astype(float)
    out["reachability_broadcast_tv"] = out["media_penetration_tv"].astype(float)
    out["reachability_broadcast_radio"] = out["media_penetration_radio"].astype(float)

    # Q1 2018 Latin America digital advertising channels
    for ad_channel in ["facebook_ads", "instagram_ads", "google_ads", "linkedin_ads"]:
        col_name = f"media_penetration_{ad_channel}"
        if col_name in out.columns:
            out[f"reachability_{ad_channel}"] = out["internet_access_flag"].astype(float) * out[
                col_name
            ].astype(float)
        else:
            out[f"reachability_{ad_channel}"] = 0.0

    out["reachability_index"] = (
        weights["digital"] * out["reachability_digital"]
        + weights["broadcast_tv"] * out["reachability_broadcast_tv"]
        + weights["broadcast_radio"] * out["reachability_broadcast_radio"]
    ).clip(0.0, 1.0)

    q_low = out["reachability_index"].quantile(0.33)
    q_high = out["reachability_index"].quantile(0.66)
    out["reachability_tier"] = "medium"
    out.loc[out["reachability_index"] <= q_low, "reachability_tier"] = "low"
    out.loc[out["reachability_index"] >= q_high, "reachability_tier"] = "high"

    out["urban_digital_compound"] = (~out["rural_flag"]) & out["internet_access_flag"]
    out["rural_offline_compound"] = out["rural_flag"] & (~out["internet_access_flag"])

    return out
