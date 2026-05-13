"""Interactive Plotly HTML for daily posterior margin + shock overlay."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go


def write_scenario_explorer_html(
    daily: pd.DataFrame,
    tracking: pd.DataFrame,
    out_path: Path,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    daily_plot = daily.copy()
    daily_plot["date"] = pd.to_datetime(daily_plot["date"])
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=daily_plot["date"],
            y=daily_plot["posterior_mean_preference_margin_pp"],
            mode="lines",
            name="Posterior mean margin (pp)",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=daily_plot["date"],
            y=daily_plot["posterior_hdi_low_pp"],
            mode="lines",
            line=dict(dash="dot"),
            name="HDI low",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=daily_plot["date"],
            y=daily_plot["posterior_hdi_high_pp"],
            mode="lines",
            line=dict(dash="dot"),
            name="HDI high",
        )
    )
    if not tracking.empty and "publication_date" in tracking.columns:
        t = tracking.copy()
        t["publication_date"] = pd.to_datetime(t["publication_date"])
        fig.add_trace(
            go.Scatter(
                x=t["publication_date"],
                y=t["m_poll_pp"],
                mode="markers",
                marker=dict(size=10, symbol="diamond"),
                name="Survey waves (m_poll)",
            )
        )
    fig.update_layout(
        title="Module C — tracking posterior vs survey measurements",
        xaxis_title="Date",
        yaxis_title="Margin (percentage points)",
        legend_orientation="h",
    )
    fig.write_html(out_path, include_plotlyjs="cdn")
