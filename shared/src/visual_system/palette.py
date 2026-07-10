"""Canonical, colorblind-safe segment palette.

One ``segment_label -> color`` mapping for the six population segments,
consumed by every chart-producing surface in the repository. This module is
the *only* place a segment color, marker, hatch, or linestyle may be
hard-coded (``scripts/check_no_local_color_literals.py`` enforces this).

Hex values are drawn from the Okabe-Ito colorblind-safe qualitative palette
(Okabe, M. & Ito, K. (2008), "Color Universal Design (CUD): How to make
figures and presentations that are friendly to colorblind people"), minus
black (reserved for text/foreground) and yellow (poor contrast on a white
figure background). The remaining six hues are, by construction, pairwise
separable under simulated protanopia, deuteranopia, and tritanopia — see
``scripts/check_palette_cvd_contrast.py``, which asserts this for the exact
assignment below rather than relying on the source palette's reputation
alone.

The previous per-pipeline palettes this module replaces:

- ``reports/eda/generate_eda.py``'s ``SEG_COLORS`` (RED/GREEN collide under
  deuteranopia/protanopia — the motivating defect for this module).
- ``reports/eda/build_notebook.py``'s local ``COLOR``/``SEG_COLORS``.
- The Module A dashboard's ``segment_size_chart``, which used Plotly
  Express's default colorway and ignored segment identity entirely.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

# A matplotlib linestyle: either a named style ("solid", "dashed", ...) or a
# dash tuple ``(offset, (on, off, on, off, ...))``.
Linestyle = str | tuple[float, tuple[float, ...]]

# Canonical segment order. Must exactly match
# ``population_segmentation.utils.schema.CANONICAL_SEGMENT_LABELS`` — see
# ``tests/test_visual_system_palette.py`` for the drift guard (this module
# intentionally does not import from module_a to keep ``shared`` dependency
# free of any one module).
SEGMENT_LABELS: Final[tuple[str, ...]] = (
    "rural_committed",
    "urban_high_volatility",
    "structurally_dependent_bloc",
    "committed_opposition",
    "rural_low_propensity",
    "youth_volatile",
)

# Okabe-Ito colorblind-safe qualitative palette (vermillion, blue, orange,
# reddish purple, bluish green, sky blue — the six-hue subset commonly
# recommended for categorical charts once black and yellow are excluded).
SEGMENT_COLORS: Final[dict[str, str]] = {
    "rural_committed": "#D55E00",  # vermillion
    "urban_high_volatility": "#0072B2",  # blue
    "structurally_dependent_bloc": "#E69F00",  # orange
    "committed_opposition": "#CC79A7",  # reddish purple
    "rural_low_propensity": "#009E73",  # bluish green
    "youth_volatile": "#56B4E9",  # sky blue
}

# Redundant, non-color encodings for charts whose legend is the *only*
# channel separating all six segments simultaneously (A10 PCA biplot, A12
# reachability step histogram, S2 propensity x reachability matrix — IMP-V01
# Scenario: "Legend-only charts carry a redundant encoding").
SEGMENT_MARKERS: Final[dict[str, str]] = {
    "rural_committed": "o",
    "urban_high_volatility": "s",
    "structurally_dependent_bloc": "^",
    "committed_opposition": "D",
    "rural_low_propensity": "P",
    "youth_volatile": "X",
}

SEGMENT_LINESTYLES: Final[dict[str, Linestyle]] = {
    "rural_committed": "solid",
    "urban_high_volatility": "dashed",
    "structurally_dependent_bloc": "dotted",
    "committed_opposition": "dashdot",
    "rural_low_propensity": (0.0, (3.0, 1.0, 1.0, 1.0)),
    "youth_volatile": (0.0, (1.0, 1.0)),
}

SEGMENT_HATCHES: Final[dict[str, str]] = {
    "rural_committed": "",
    "urban_high_volatility": "//",
    "structurally_dependent_bloc": "xx",
    "committed_opposition": "\\\\",
    "rural_low_propensity": "..",
    "youth_volatile": "++",
}


class UnknownSegmentError(KeyError):
    """Raised when a ``segment_label`` outside the canonical six is requested.

    The prior per-pipeline behavior (``SEG_COLORS.get(seg, GREY)``) silently
    substituted a grey fallback for any unmapped segment, hiding a data
    completeness gap. This module fails loudly instead (IMP-V01 data
    integrity requirement): an unmapped ``segment_label`` reaching a chart is
    a defect to surface, not a cosmetic default to paper over.
    """


def _lookup(mapping: Mapping[str, object], segment_label: str, what: str) -> object:
    try:
        return mapping[segment_label]
    except KeyError as exc:
        raise UnknownSegmentError(
            f"segment_label={segment_label!r} is not one of the six canonical "
            f"segments {sorted(SEGMENT_COLORS)}; no {what} is defined for it. "
            "Add it to shared/src/visual_system/palette.py before charting it."
        ) from exc


def get_segment_color(segment_label: str) -> str:
    """Look up the canonical color for a segment_label.

    Args:
        segment_label: One of the six canonical population segment labels
            (see :data:`SEGMENT_LABELS`).

    Returns:
        Hex color string, e.g. ``"#D55E00"``.

    Raises:
        UnknownSegmentError: If ``segment_label`` is not one of the six
            canonical segments.

    Example:
        >>> get_segment_color("rural_committed")
        '#D55E00'
    """
    return _lookup(SEGMENT_COLORS, segment_label, "color")  # type: ignore[return-value]


def get_segment_marker(segment_label: str) -> str:
    """Look up the redundant marker shape for a segment_label.

    Args:
        segment_label: One of the six canonical population segment labels.

    Returns:
        A matplotlib marker code, e.g. ``"o"``.

    Raises:
        UnknownSegmentError: If ``segment_label`` is not one of the six
            canonical segments.

    Example:
        >>> get_segment_marker("urban_high_volatility")
        's'
    """
    return _lookup(SEGMENT_MARKERS, segment_label, "marker")  # type: ignore[return-value]


def get_segment_linestyle(segment_label: str) -> Linestyle:
    """Look up the redundant linestyle for a segment_label.

    Args:
        segment_label: One of the six canonical population segment labels.

    Returns:
        A matplotlib linestyle string or dash-tuple.

    Raises:
        UnknownSegmentError: If ``segment_label`` is not one of the six
            canonical segments.

    Example:
        >>> get_segment_linestyle("committed_opposition")
        'dashdot'
    """
    return _lookup(SEGMENT_LINESTYLES, segment_label, "linestyle")  # type: ignore[return-value]


def get_segment_hatch(segment_label: str) -> str:
    """Look up the redundant hatch pattern for a segment_label.

    Args:
        segment_label: One of the six canonical population segment labels.

    Returns:
        A matplotlib hatch pattern string (``""`` for no hatch).

    Raises:
        UnknownSegmentError: If ``segment_label`` is not one of the six
            canonical segments.

    Example:
        >>> get_segment_hatch("youth_volatile")
        '++'
    """
    return _lookup(SEGMENT_HATCHES, segment_label, "hatch")  # type: ignore[return-value]
