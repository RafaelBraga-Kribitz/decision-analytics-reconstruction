# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""Posterior predictive check plot for the tracking model."""

from __future__ import annotations

from pathlib import Path

import arviz as az
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def generate_ppc_plot(
    idata: az.InferenceData,
    tracking: pd.DataFrame,
    out_path: Path,
) -> Path:
    """Write a PPC fan-chart PNG overlaying posterior predictive vs. observed polls.

    Args:
        idata: InferenceData with ``posterior_predictive`` group (group name ``obs``).
        tracking: Cleaned tracking frame with ``m_poll_pp``, ``publication_date``,
            ``poll_wave_id``.
        out_path: Destination PNG path (parent directories created if needed).

    Returns:
        Resolved path to the written PNG.
    """
    if not hasattr(idata, "posterior_predictive"):
        raise ValueError("idata has no posterior_predictive group — refit with sample_ppc=True")

    ppc_samples = np.asarray(idata.posterior_predictive["obs"].values).reshape(  # type: ignore[union-attr]
        -1, len(tracking)
    )

    sorted_df = tracking.sort_values("publication_date")
    original_idx = sorted_df.index.to_numpy()
    ordered = sorted_df.reset_index(drop=True)
    obs = ordered["m_poll_pp"].to_numpy(dtype=np.float64)
    dates = pd.to_datetime(ordered["publication_date"]).dt.date.tolist()
    x = np.arange(len(ordered))

    fig, ax = plt.subplots(figsize=(9, 5))

    ppc_ordered = ppc_samples[:, original_idx]
    q025 = np.percentile(ppc_ordered, 2.5, axis=0)
    q10 = np.percentile(ppc_ordered, 10.0, axis=0)
    q25 = np.percentile(ppc_ordered, 25.0, axis=0)
    q50 = np.percentile(ppc_ordered, 50.0, axis=0)
    q75 = np.percentile(ppc_ordered, 75.0, axis=0)
    q90 = np.percentile(ppc_ordered, 90.0, axis=0)
    q975 = np.percentile(ppc_ordered, 97.5, axis=0)

    # Nested intervals in distinct lightness steps of one hue (IMP-V05 /
    # issue #69): decodable in grayscale, where the old alpha-only stacking
    # of a single color was not. Each band also carries a direct right-edge
    # label so no legend lookup is needed.
    band_specs = (
        (q025, q975, "#c6dbef", "95%"),
        (q10, q90, "#6baed6", "80%"),
        (q25, q75, "#2171b5", "50%"),
    )
    for lo, hi, color, level in band_specs:
        ax.fill_between(x, lo, hi, color=color, alpha=1.0, label=f"{level} PPC interval")
        ax.annotate(
            level,
            xy=(float(x[-1]), float((lo[-1] + hi[-1]) / 2.0)),
            xytext=(6, 0),
            textcoords="offset points",
            va="center",
            fontsize=8,
            color="#25282b",
        )
    ax.plot(x, q50, color="#08306b", linewidth=1.5, linestyle="--", label="PPC median")
    ax.scatter(x, obs, color="#EF553B", zorder=5, s=80, label="Observed polls (pp)")

    ax.set_xticks(x)
    ax.set_xticklabels([str(d) for d in dates], rotation=20, ha="right", fontsize=9)
    ax.set_xlabel("Poll publication date", fontsize=11)
    ax.set_ylabel("Margin (percentage points, A − B)", fontsize=11)
    ax.set_title(
        "Posterior Predictive Check — tracking model vs. observed polls\n"
        f"(Series A · Paraguay 2018 reconstruction · n={len(ordered)} waves)",
        fontsize=12,
    )
    ax.axhline(0, color="#888", linewidth=0.8, linestyle=":")
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    fig.tight_layout()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_path.resolve()
