# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnnecessaryIsInstance=false
"""Shared figure-template conventions.

Margins, the source-attribution watermark zone, legend placement, and the
direct-labeling preference for categorical charts with four or more series —
factored out of ``reports/eda/generate_eda.py`` (which previously scattered
``annotate_source(ax)`` calls and raw ``fig.text(0.5, -0.01/-0.02, SOURCE,
...)`` literals across the file) so every chart-producing surface applies
the same conventions instead of reinventing them per chart (triage row
``AUD-XCUT-004``, root cause ``figure_template``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

#: Standard source-attribution string stamped on every governed chart.
SOURCE_TEXT: Final[str] = "Source: Paraguay Campaign Data Pipeline 2018 | April 2026"

#: Muted grey used for the watermark/source text — matches the repo's brand
#: GREY (``#adb5bd``) without importing matplotlib rc state.
SOURCE_COLOR: Final[str] = "#adb5bd"
SOURCE_FONTSIZE: Final[float] = 7.5

#: Default y-offset (axes-fraction) for a per-Axes source stamp.
AXES_SOURCE_Y: Final[float] = -0.13
#: Default y-offset (figure-fraction) for a per-Figure source stamp, used by
#: multi-panel charts that stamp the source once for the whole figure.
FIGURE_SOURCE_Y: Final[float] = -0.02

#: Legend placement convention for charts whose legend is the primary key
#: for >=4 categorical series: outside the axes, upper-right anchored, so it
#: never overlaps plotted data.
LEGEND_LOC: Final[str] = "upper left"
LEGEND_BBOX_TO_ANCHOR: Final[tuple[float, float]] = (1.01, 1.0)

#: Minimum number of simultaneously-legended categorical series above which
#: a chart must carry a redundant non-color encoding (marker/hatch/
#: linestyle/direct label) in addition to the shared palette.
REDUNDANT_ENCODING_SERIES_THRESHOLD: Final[int] = 4


def annotate_source(target: Axes | Figure, source: str = SOURCE_TEXT) -> None:
    """Stamp the standard source-attribution watermark.

    Accepts either a matplotlib ``Axes`` (stamped in axes-fraction
    coordinates below the plot) or a ``Figure`` (stamped in figure-fraction
    coordinates, for multi-panel charts that stamp once for the whole
    figure) so every chart-producing surface uses one watermark convention.

    Args:
        target: The ``Axes`` or ``Figure`` to stamp.
        source: Source-attribution text. Defaults to :data:`SOURCE_TEXT`.

    Returns:
        None.

    Raises:
        TypeError: If ``target`` is neither an ``Axes`` nor a ``Figure``.

    Example:
        >>> import matplotlib
        >>> matplotlib.use("Agg")
        >>> import matplotlib.pyplot as plt
        >>> fig, ax = plt.subplots()
        >>> annotate_source(ax)
    """
    # Local import: matplotlib is an optional/heavy dependency of this
    # otherwise-pure module, and callers already import it themselves.
    from matplotlib.axes import Axes as _Axes
    from matplotlib.figure import Figure as _Figure

    if isinstance(target, _Axes):
        target.annotate(
            source,
            xy=(0.5, AXES_SOURCE_Y),
            xycoords="axes fraction",
            ha="center",
            fontsize=SOURCE_FONTSIZE,
            color=SOURCE_COLOR,
        )
    elif isinstance(target, _Figure):
        target.text(
            0.5, FIGURE_SOURCE_Y, source, ha="center", fontsize=SOURCE_FONTSIZE, color=SOURCE_COLOR
        )
    else:
        raise TypeError(f"annotate_source() expects an Axes or Figure, got {type(target)!r}")


def apply_figure_template(
    fig: Figure,
    *,
    source: str = SOURCE_TEXT,
    bottom_margin: float = 0.14,
    stamp_source: bool = True,
) -> None:
    """Apply the shared margin and source-attribution convention to a figure.

    Args:
        fig: The figure to template.
        source: Source-attribution text. Defaults to :data:`SOURCE_TEXT`.
        bottom_margin: Fraction of figure height reserved at the bottom for
            the source-attribution band, matching the convention used across
            ``generate_eda.py``'s multi-panel charts.
        stamp_source: If ``True`` (default), stamp the source text via
            :func:`annotate_source`. Set to ``False`` when the caller stamps
            per-Axes instead (e.g. single-panel charts using
            ``annotate_source(ax)`` directly), to avoid a duplicate stamp.

    Returns:
        None.

    Raises:
        None.

    Example:
        >>> import matplotlib
        >>> matplotlib.use("Agg")
        >>> import matplotlib.pyplot as plt
        >>> fig, ax = plt.subplots()
        >>> apply_figure_template(fig)
    """
    fig.subplots_adjust(bottom=bottom_margin)
    if stamp_source:
        annotate_source(fig, source)


def place_legend(ax: Axes, *, title: str | None = None, fontsize: int = 9) -> None:
    """Place a legend using the shared outside-upper-left convention.

    Args:
        ax: The axes whose legend to place.
        title: Optional legend title (e.g. ``"Segment"``).
        fontsize: Legend font size.

    Returns:
        None.

    Raises:
        None.

    Example:
        >>> import matplotlib
        >>> matplotlib.use("Agg")
        >>> import matplotlib.pyplot as plt
        >>> fig, ax = plt.subplots()
        >>> ax.plot([0, 1], [0, 1], label="a")
        [...]
        >>> place_legend(ax, title="Segment")
    """
    ax.legend(title=title, bbox_to_anchor=LEGEND_BBOX_TO_ANCHOR, loc=LEGEND_LOC, fontsize=fontsize)
