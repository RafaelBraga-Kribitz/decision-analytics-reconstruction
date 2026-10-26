"""Canonical segment palette, on the Braga design system v2.1.

One ``segment_label -> color`` mapping for the six population segments,
consumed by every chart-producing surface in the repository. This module is
the *only* place a segment color, marker, hatch, or linestyle may be
assigned (``scripts/check_no_local_color_literals.py`` enforces this). It
holds no hex value: each segment names a design-system role and bk-viz
(``bk_theme``) resolves it (D-053, colours only through roles).

Assignment, in :data:`SEGMENT_DISPLAY_ORDER`: the categorical hue slots
``cat-1`` .. ``cat-4`` in slot order, then two structure greys, the dark
``catg-2`` and ``cat-other``. The fifth hue slot ``cat-5`` (brown) is not
used: under simulated tritanopia it collapses onto ``cat-2`` (ochre) to
deltaE ~10.5, below the 12.0 floor ``scripts/check_palette_cvd_contrast.py``
holds every segment pair to; the set used here clears it on all 15 pairs
under all three CVD types. The redundant marker / linestyle / hatch
encodings below carry segment identity independently of hue.

The previous per-pipeline palettes this module replaces:

- ``reports/eda/generate_eda.py``'s ``SEG_COLORS`` (RED/GREEN collide under
  deuteranopia/protanopia — the motivating defect for this module).
- ``reports/eda/build_notebook.py``'s local ``COLOR``/``SEG_COLORS``.
- The Module A dashboard's ``segment_size_chart``, which used Plotly
  Express's default colorway and ignored segment identity entirely.
- The Okabe-Ito hex assignment this module carried before the design
  system v2.1 (hex literals in chart code are retired, D-053).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

import bk_theme as bk

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

# Shared presentation order for segment charts (IMP-V06 / issue #70): the
# order the static report has always used (formerly ``generate_eda.py``'s
# local ``SEG_ORDER``), now owned here so the dashboard and every other
# surface rank segments identically. A segment's rank must never differ
# between surfaces; both the EDA factory and the dashboard import this.
SEGMENT_DISPLAY_ORDER: Final[tuple[str, ...]] = (
    "youth_volatile",
    "urban_high_volatility",
    "rural_committed",
    "rural_low_propensity",
    "structurally_dependent_bloc",
    "committed_opposition",
)

# Design-system role per segment (see the module docstring for the order and
# why ``cat-5`` is skipped). Resolved through bk-viz, never a hex literal.
SEGMENT_COLOR_ROLES: Final[dict[str, str]] = {
    "youth_volatile": "cat-1",
    "urban_high_volatility": "cat-2",
    "rural_committed": "cat-3",
    "rural_low_propensity": "cat-4",
    "structurally_dependent_bloc": "catg-2",
    "committed_opposition": "cat-other",
}

# Light-mode resolution, for callers that need a plain mapping (the dashboard,
# the CVD check). get_segment_color() resolves in the current bk mode.
SEGMENT_COLORS: Final[dict[str, str]] = {
    label: bk.COLOR["light"][role] for label, role in SEGMENT_COLOR_ROLES.items()
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
        Hex color string resolved from the segment's design-system role in
        the current bk-viz mode.

    Raises:
        UnknownSegmentError: If ``segment_label`` is not one of the six
            canonical segments.

    Example:
        >>> get_segment_color("youth_volatile") == bk.c("cat-1")
        True
    """
    role = _lookup(SEGMENT_COLOR_ROLES, segment_label, "color")
    return bk.c(str(role))


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
