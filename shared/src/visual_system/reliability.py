# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""The one shared reliability-diagram builder (IMP-V04 / issue #68).

Every surface that draws a predicted-vs-observed calibration diagram — the
static report generator (``scripts/generate_module_a_report_charts.py``), the
Module A dashboard (via ``population_segmentation.visualization
.calibration_curves``), and any notebook — must call this builder. A second
bespoke implementation anywhere in the repo is the V6 defect class
(``tests/test_reliability_standard.py`` re-blocks it structurally).

What the builder guarantees, per the IMP-V04 spec:

* **Geometry** — square plot region, both axes fixed to ``[0, 1]``, enforced
  equal aspect, so the reference diagonal renders at exactly 45 degrees on
  every export size.
* **Bin honesty** — marker area proportional to bin count; a Wilson binomial
  interval drawn per bin; bins under ``min_bin_count`` de-emphasized; empty
  bins omitted and never bridged by the connecting line.
* **Disclaimer travels** — the calibration caveat is drawn inside the figure
  canvas, so a PNG viewed without its surrounding page still carries it.
* **Fixed bin edges** — ``n_bins`` uniform bins on ``[0, 1]``; never
  data-dependent.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from matplotlib.figure import Figure

#: Bins with fewer observations than this render in the de-emphasized style
#: (hollow grey marker, dashed interval) — visually subordinate, still shown.
DEFAULT_MIN_BIN_COUNT: int = 30

#: z for the ~95% Wilson score interval.
_WILSON_Z: float = 1.959963984540054

#: The calibration caveat every export must carry while IMP-A01's circular
#: propensity target remains in place (soft dependency; the caveat text is
#: owned here so both surfaces render one wording).
CIRCULARITY_DISCLAIMER: str = (
    "Caveat: propensity labels derive from the same department anchors the model uses as "
    "features (IMP-A01); this diagram shows aggregate alignment, not held-out calibration."
)


def _wilson_interval(successes: float, n: float) -> tuple[float, float]:
    """95% Wilson score interval for a binomial proportion.

    Args:
        successes: Number of positive outcomes in the bin.
        n: Bin observation count (must be > 0).

    Returns:
        ``(low, high)`` bounds, each clipped to ``[0, 1]``.

    Raises:
        ValueError: If ``n`` is not positive.

    Example:
        >>> lo, hi = _wilson_interval(5, 10)
        >>> 0.0 <= lo < 0.5 < hi <= 1.0
        True
    """
    if n <= 0:
        raise ValueError("Wilson interval needs a positive bin count")
    z2 = _WILSON_Z**2
    p_hat = successes / n
    denom = 1.0 + z2 / n
    center = (p_hat + z2 / (2.0 * n)) / denom
    half = (_WILSON_Z * math.sqrt(p_hat * (1.0 - p_hat) / n + z2 / (4.0 * n * n))) / denom
    # Clamp so the interval always contains p_hat: at p_hat exactly 0 or 1 the
    # bound equals p_hat analytically, but floating-point rounding can land an
    # epsilon on the wrong side, which downstream error bars reject.
    low = min(p_hat, max(0.0, center - half))
    high = max(p_hat, min(1.0, center + half))
    return (low, high)


def reliability_frame(y_true: np.ndarray, y_prob: np.ndarray, *, n_bins: int = 10) -> pd.DataFrame:
    """Bin predictions on fixed uniform edges and summarize observed outcomes.

    Args:
        y_true: Binary outcomes (0/1).
        y_prob: Predicted probabilities, all finite and within ``[0, 1]``.
        n_bins: Number of uniform bins on ``[0, 1]`` (fixed edges — never
            data-dependent).

    Returns:
        One row per **non-empty** bin (empty bins are omitted, per the spec's
        edge case) with columns ``bin``, ``predicted_mean``, ``observed_mean``,
        ``count``, ``ci_low``, ``ci_high`` (95% Wilson interval).

    Raises:
        ValueError: On NaN/non-finite predictions, predictions outside
            ``[0, 1]``, non-binary outcomes, or mismatched lengths — the
            builder aborts rather than silently dropping rows.

    Example:
        ``reliability_frame(labels, scores)`` feeding :func:`reliability_diagram`.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_prob = np.asarray(y_prob, dtype=float)
    if y_true.shape != y_prob.shape:
        raise ValueError(f"length mismatch: y_true {y_true.shape} vs y_prob {y_prob.shape}")
    if not np.all(np.isfinite(y_prob)):
        raise ValueError("y_prob contains NaN/inf — aborting rather than silently dropping rows")
    if np.any((y_prob < 0.0) | (y_prob > 1.0)):
        raise ValueError("y_prob outside [0, 1]")
    if not np.all(np.isin(y_true[np.isfinite(y_true)], (0.0, 1.0))) or np.any(~np.isfinite(y_true)):
        raise ValueError("y_true must be binary 0/1")

    edges = np.linspace(0.0, 1.0, n_bins + 1)
    rows: list[dict[str, float]] = []
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        mask = (y_prob >= lo) & (y_prob < hi if i < n_bins - 1 else y_prob <= hi)
        n = int(mask.sum())
        if n == 0:
            continue
        successes = float(y_true[mask].sum())
        ci_low, ci_high = _wilson_interval(successes, n)
        rows.append(
            {
                "bin": float(i),
                "predicted_mean": float(y_prob[mask].mean()),
                "observed_mean": successes / n,
                "count": float(n),
                "ci_low": ci_low,
                "ci_high": ci_high,
            }
        )
    return pd.DataFrame(rows)


def reliability_diagram(
    frame: pd.DataFrame,
    *,
    disclaimer: str = CIRCULARITY_DISCLAIMER,
    title: str = "Reliability diagram",
    subtitle: str | None = None,
    min_bin_count: int = DEFAULT_MIN_BIN_COUNT,
) -> Figure:
    """Render the shared, geometrically honest reliability diagram.

    Args:
        frame: Output of :func:`reliability_frame`.
        disclaimer: Calibration caveat drawn **inside** the figure canvas so
            every export carries it. Defaults to the IMP-A01 circularity
            caveat; pass a fuller string to extend, never an empty one.
        title: Axes title.
        subtitle: Optional second title line (e.g. the label-source note).
        min_bin_count: Bins with fewer observations render de-emphasized.

    Returns:
        A matplotlib ``Figure`` with square ``[0, 1] x [0, 1]`` axes and
        enforced equal aspect — the 45-degree reference is exactly diagonal
        at any export size. Marker area scales with bin count; each bin
        carries its Wilson interval; consecutive-bin gaps break the line.

    Raises:
        ValueError: If ``frame`` is empty or ``disclaimer`` is blank.

    Example:
        ``reliability_diagram(reliability_frame(y, p)).savefig("out.png")``
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from visual_system.figure_template import annotate_source

    if frame.empty:
        raise ValueError("reliability frame has no populated bins")
    if not disclaimer.strip():
        raise ValueError("a reliability diagram must carry its calibration disclaimer")

    fig, ax = plt.subplots(figsize=(7.0, 7.0))
    ax.plot([0, 1], [0, 1], "--", color="#25282b", lw=1.2, label="Perfect calibration", zorder=1)

    frame = frame.sort_values("bin").reset_index(drop=True)
    counts = frame["count"].to_numpy()
    # Marker area proportional to bin count (spec: bin 5 at 4,800 obs must
    # visually dominate bin 9 at 12).
    max_count = float(counts.max())
    sizes = 20.0 + 380.0 * (counts / max_count)
    emphasized = counts >= float(min_bin_count)

    # Connecting line: break wherever a bin is missing so the line never
    # bridges empty bins as if data existed.
    xs: list[float] = []
    ys: list[float] = []
    prev_bin: float | None = None
    for _, row in frame.iterrows():
        cur_bin = float(row["bin"])
        if prev_bin is not None and cur_bin != prev_bin + 1:
            xs.append(float("nan"))
            ys.append(float("nan"))
        xs.append(float(row["predicted_mean"]))
        ys.append(float(row["observed_mean"]))
        prev_bin = cur_bin
    ax.plot(xs, ys, "-", color="#0072B2", lw=1.4, zorder=2)

    groups: tuple[tuple[np.ndarray, str, float, str, str], ...] = (
        (emphasized, "#0072B2", 0.95, "#25282b", f"Bins (n >= {min_bin_count}, area ~ n)"),
        (~emphasized, "#adb5bd", 0.55, "#adb5bd", f"Sparse bins (n < {min_bin_count})"),
    )
    for mask, color, alpha, edgecolor, label in groups:
        sub = frame[mask]
        if sub.empty:
            continue
        ax.errorbar(
            sub["predicted_mean"],
            sub["observed_mean"],
            yerr=np.vstack(
                [
                    sub["observed_mean"] - sub["ci_low"],
                    sub["ci_high"] - sub["observed_mean"],
                ]
            ),
            fmt="none",
            ecolor=color,
            elinewidth=1.4,
            capsize=3,
            alpha=alpha,
            zorder=3,
        )
        ax.scatter(
            sub["predicted_mean"],
            sub["observed_mean"],
            s=sizes[mask],
            zorder=4,
            label=label,
            color=color,
            alpha=alpha,
            edgecolors=edgecolor,
        )

    # The geometry invariant: square [0,1]x[0,1], equal aspect — asserted by
    # tests/test_reliability_standard.py from the figure metadata.
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Predicted mean propensity (bin)")
    ax.set_ylabel("Observed rate")
    ax.set_title(title if subtitle is None else f"{title}\n{subtitle}")
    ax.legend(fontsize=8, loc="upper left")

    # Disclaimer inside the canvas so PNG exports keep it.
    ax.text(
        0.98,
        0.02,
        "\n".join(_wrap(disclaimer, 58)),
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=7.0,
        color="#495057",
        style="italic",
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "#f8f9fa", "edgecolor": "#adb5bd"},
    )
    annotate_source(fig)
    fig.subplots_adjust(bottom=0.12)
    return fig


def _wrap(text: str, width: int) -> list[str]:
    """Greedy word-wrap for the in-canvas disclaimer box.

    Args:
        text: Disclaimer string.
        width: Approximate characters per line.

    Returns:
        Wrapped lines.

    Raises:
        None.

    Example:
        >>> _wrap("a b c", 3)
        ['a b', 'c']
    """
    words = text.split()
    lines: list[str] = []
    cur = ""
    for word in words:
        if cur and len(cur) + 1 + len(word) > width:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    if cur:
        lines.append(cur)
    return lines
