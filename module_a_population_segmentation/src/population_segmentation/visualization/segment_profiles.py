"""Segment profile plotting helpers."""

from __future__ import annotations

import pandas as pd
import plotly.express as px


def segment_profile_table(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "segment_label",
        "participation_propensity",
        "reachability_index",
        "rural_flag",
        "jopara_flag",
    ]
    work = df[cols].copy()
    agg = (
        work.groupby("segment_label", dropna=False)
        .agg(
            segment_size=("segment_label", "size"),
            mean_participation_propensity=("participation_propensity", "mean"),
            mean_reachability_index=("reachability_index", "mean"),
            pct_rural=("rural_flag", "mean"),
            pct_jopara=("jopara_flag", "mean"),
        )
        .reset_index()
    )
    agg["segment_size_pct"] = agg["segment_size"] / max(1, agg["segment_size"].sum())
    return agg


def segment_size_chart(profile_df: pd.DataFrame):
    return px.bar(profile_df, x="segment_label", y="segment_size", title="Segment size")
