"""Interactive Plotly HTML for daily posterior margin + shock overlay."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from module_c_forecasting_scenarios.config import load_sampler_config

#: Nominal HDI level, from the same sampler config every other surface reads —
#: the interval label must always match the configured probability, never a
#: hardcoded string (IMP-V05 / issue #69).
_HDI_PROB: float = float(load_sampler_config().get("hdi_prob", 0.94))
_HDI_LABEL: str = f"{round(_HDI_PROB * 100)}% HDI"


def write_scenario_explorer_html(
    daily: pd.DataFrame,
    tracking: pd.DataFrame,
    out_path: Path,
) -> None:
    """Write the interactive tracking-posterior explorer HTML.

    Args:
        daily: Daily posterior frame with ``date``,
            ``posterior_mean_preference_margin_pp``, ``posterior_hdi_low_pp``,
            and ``posterior_hdi_high_pp`` columns.
        tracking: Cleaned tracking frame (may be empty) whose
            ``publication_date``/``m_poll_pp`` rows render as survey markers.
        out_path: Destination HTML path (parents created if needed).

    Returns:
        None.

    Raises:
        KeyError: If ``daily`` lacks the posterior columns.

    Example:
        ``write_scenario_explorer_html(daily, tracking, Path("explorer.html"))``
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    daily_plot = daily.copy()
    daily_plot["date"] = pd.to_datetime(daily_plot["date"])
    fig = go.Figure()
    # HDI as a filled band (IMP-V05 / issue #69): the interactive surface
    # renders the same estimand the static charts shade — two dotted lines
    # with empty space between them misread as separate series.
    fig.add_trace(
        go.Scatter(
            x=daily_plot["date"],
            y=daily_plot["posterior_hdi_low_pp"],
            mode="lines",
            line={"width": 0},
            showlegend=False,
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=daily_plot["date"],
            y=daily_plot["posterior_hdi_high_pp"],
            mode="lines",
            line={"width": 0},
            fill="tonexty",
            fillcolor="rgba(0,114,178,0.18)",
            name=_HDI_LABEL,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=daily_plot["date"],
            y=daily_plot["posterior_mean_preference_margin_pp"],
            mode="lines",
            line={"color": "#0072B2"},
            name="Posterior mean margin (pp)",
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
                marker={"size": 10, "symbol": "diamond"},
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
