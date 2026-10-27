"""Shared visual system: one canonical palette and figure template.

Every figure is drawn on the Braga design system v2.1 through bk-viz
(``bk_theme``): :func:`apply_theme` installs it, :func:`conform_figure` is
the save-time type guard (``visual_system.theme``).

Single source of truth for the six-segment colorblind-safe palette and the
figure-template conventions (margins, source-attribution watermark, legend
placement, redundant non-color encodings) consumed by every chart-producing
surface in this repository:

- ``reports/eda/generate_eda.py`` (the canonical static-PNG figure factory),
- ``reports/eda/build_notebook.py`` (the notebook pipeline),
- the Module A dashboard
  (``population_segmentation.visualization.segment_profiles``).

See ``governance/improvement_plan/IMP-V01_visual-system.md`` for the spec
this package implements.
"""

from __future__ import annotations

from visual_system.figure_template import (
    SOURCE_TEXT,
    annotate_source,
    apply_figure_template,
)
from visual_system.palette import (
    SEGMENT_COLOR_ROLES,
    SEGMENT_COLORS,
    SEGMENT_HATCHES,
    SEGMENT_LABELS,
    SEGMENT_LINESTYLES,
    SEGMENT_MARKERS,
    UnknownSegmentError,
    get_segment_color,
    get_segment_hatch,
    get_segment_linestyle,
    get_segment_marker,
)
from visual_system.reliability import (
    CIRCULARITY_DISCLAIMER,
    reliability_diagram,
    reliability_frame,
)
from visual_system.theme import TYPE_FLOOR_PT, apply_theme, conform_figure

__all__ = [
    "CIRCULARITY_DISCLAIMER",
    "SEGMENT_COLORS",
    "SEGMENT_COLOR_ROLES",
    "SEGMENT_HATCHES",
    "SEGMENT_LABELS",
    "SEGMENT_LINESTYLES",
    "SEGMENT_MARKERS",
    "SOURCE_TEXT",
    "TYPE_FLOOR_PT",
    "UnknownSegmentError",
    "annotate_source",
    "apply_figure_template",
    "apply_theme",
    "conform_figure",
    "get_segment_color",
    "get_segment_hatch",
    "get_segment_linestyle",
    "get_segment_marker",
    "reliability_diagram",
    "reliability_frame",
]
