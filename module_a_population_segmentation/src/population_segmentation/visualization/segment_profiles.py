# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false
"""Segment profile plotting helpers."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
from plotly.graph_objects import Figure


def segment_profile_table(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate key behavioral and reachability metrics by ``segment_label``.

    Args:
        df: Population frame with segment assignment and propensity columns.

    Returns:
        One row per segment with size, means, and composition percentages.

    Raises:
        KeyError: If required columns are missing.

    Example:
        Source table for :func:`segment_size_chart` and stakeholder dashboards.
    """
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


def segment_size_chart(profile_df: pd.DataFrame) -> Figure:
    """Bar chart of segment sizes from a profile table.

    Args:
        profile_df: Output of :func:`segment_profile_table`.

    Returns:
        Plotly Express bar figure.

    Raises:
        KeyError: If ``segment_label`` or ``segment_size`` is missing.

    Example:
        Quick QA plot after re-running segmentation with a new ``k``.
    """
    return px.bar(profile_df, x="segment_label", y="segment_size", title="Segment size")
