# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false
"""Segment profile plotting helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
from plotly.graph_objects import Figure

# Shared visual system (IMP-V01 / issue #66): the dashboard's segment chart
# uses the one canonical colorblind-safe palette instead of Plotly Express's
# default colorway, so it matches the static report and the notebook. See
# shared/src/visual_system/ and scripts/check_no_local_color_literals.py.
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "src"))
from visual_system.palette import SEGMENT_COLORS, SEGMENT_DISPLAY_ORDER


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
    """Bar chart of segment sizes, visually identical in identity to static A1.

    One metric, one visual identity (IMP-V06 / issue #70): horizontal bars in
    the shared ``SEGMENT_DISPLAY_ORDER``, colored by the shared palette, and
    direct-labeled with count and percentage — the same conventions the static
    ``A1_segment_sizes.png`` uses, so a segment never changes color or rank
    between the dashboard and the report.

    Args:
        profile_df: Output of :func:`segment_profile_table`.

    Returns:
        Plotly Express horizontal bar figure with count + percentage labels.

    Raises:
        KeyError: If ``segment_label`` or ``segment_size`` is missing.

    Example:
        Quick QA plot after re-running segmentation with a new ``k``.
    """
    present = set(profile_df["segment_label"])
    order = [label for label in SEGMENT_DISPLAY_ORDER if label in present]
    total = max(1, int(profile_df["segment_size"].sum()))
    work = profile_df.copy()
    work["size_label"] = work["segment_size"].map(
        lambda n: f"{int(n):,} ({100.0 * n / total:.1f}%)"
    )
    fig = px.bar(
        work,
        x="segment_size",
        y="segment_label",
        orientation="h",
        title="Segment size",
        color="segment_label",
        color_discrete_map=SEGMENT_COLORS,
        category_orders={"segment_label": order},
        text="size_label",
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    # Pin the axis to the shared order bottom-to-top, matching matplotlib
    # barh in static A1 (px would otherwise reverse it for horizontal bars).
    fig.update_yaxes(categoryorder="array", categoryarray=list(order))
    fig.update_layout(showlegend=False, yaxis_title=None, xaxis_title="Population count")
    return fig
