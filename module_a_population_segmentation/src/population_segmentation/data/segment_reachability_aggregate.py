"""Aggregate media reachability by segment for Module A contract output.

Produces one row per segment matching schema_contracts/media_reachability_by_segment.yaml.
"""

from __future__ import annotations

from typing import cast

import pandas as pd


def _primary_reach_channel(row: pd.Series) -> str:  # type: ignore[type-arg]
    """Return the dominant reach channel for a segment row.

    Argmax of (mean_tv_penetration, mean_radio_penetration, mean_whatsapp_penetration).
    If all three are equal, returns "direct".
    """
    tv = float(row["mean_tv_penetration"])
    radio = float(row["mean_radio_penetration"])
    whatsapp = float(row["mean_whatsapp_penetration"])
    if tv == radio == whatsapp:
        return "direct"
    best = max(tv, radio, whatsapp)
    if best == tv:
        return "tv"
    if best == radio:
        return "radio"
    return "whatsapp"


def aggregate_media_reachability_by_segment(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate per-entity feature rows into one row per segment.

    Parameters
    ----------
    df:
        Entity-level DataFrame. Required columns:
        ``segment_label``, ``participation_propensity``, ``internet_access_flag``,
        ``media_penetration_tv``, ``media_penetration_radio``,
        ``media_penetration_whatsapp``, ``rural_flag``, ``jopara_flag``,
        ``structural_dependency_encoded``, ``department``.

    Returns
    -------
    pd.DataFrame
        One row per segment with all 13 contract columns from
        ``schema_contracts/media_reachability_by_segment.yaml``.
    """
    total = len(df)

    agg = (
        df.groupby("segment_label", sort=False)
        .agg(
            segment_size=("segment_label", "count"),
            mean_participation_propensity=("participation_propensity", "mean"),
            pct_internet_access=("internet_access_flag", "mean"),
            mean_tv_penetration=("media_penetration_tv", "mean"),
            mean_radio_penetration=("media_penetration_radio", "mean"),
            mean_whatsapp_penetration=("media_penetration_whatsapp", "mean"),
            pct_rural=("rural_flag", "mean"),
            pct_jopara=("jopara_flag", "mean"),
            pct_structural_dependency=("structural_dependency_encoded", "mean"),
            dominant_department=("department", lambda s: s.mode().iloc[0]),
        )
        .reset_index()
    )

    agg["segment_size_pct"] = agg["segment_size"] / total

    float_cols = [
        "mean_participation_propensity",
        "pct_internet_access",
        "mean_tv_penetration",
        "mean_radio_penetration",
        "mean_whatsapp_penetration",
        "pct_rural",
        "pct_jopara",
        "pct_structural_dependency",
        "segment_size_pct",
    ]
    for col in float_cols:
        agg[col] = agg[col].astype("float32")

    agg["primary_reach_channel"] = agg.apply(_primary_reach_channel, axis=1)

    column_order = [
        "segment_label",
        "segment_size",
        "segment_size_pct",
        "mean_participation_propensity",
        "pct_internet_access",
        "mean_tv_penetration",
        "mean_radio_penetration",
        "mean_whatsapp_penetration",
        "pct_rural",
        "pct_jopara",
        "pct_structural_dependency",
        "dominant_department",
        "primary_reach_channel",
    ]
    return cast(pd.DataFrame, agg[column_order])
