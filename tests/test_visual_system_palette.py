"""Shared visual-system guards (IMP-V01 / issue #66).

The shared palette (``shared/src/visual_system/palette.py``) is the single
source of truth for segment colors and their redundant non-color encodings.
These tests pin three invariants:

1. The palette's segment set never drifts from Module A's canonical labels.
2. Every canonical segment has a color, marker, linestyle, and hatch, and the
   colors are distinct.
3. The two static checks that enforce the palette at rest
   (``check_palette_cvd_contrast.py`` CVD separation and
   ``check_no_local_color_literals.py`` no-local-literals) exit ``0`` on the
   current tree — so ``make test`` fails if either regresses, not only
   ``make verify``.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from population_segmentation.utils.schema import CANONICAL_SEGMENT_LABELS

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "shared" / "src"))

from visual_system import palette  # noqa: E402
from visual_system.figure_template import annotate_source  # noqa: E402


def test_palette_labels_match_canonical() -> None:
    assert set(palette.SEGMENT_LABELS) == set(CANONICAL_SEGMENT_LABELS)


def test_every_segment_has_every_encoding() -> None:
    for label in palette.SEGMENT_LABELS:
        assert palette.get_segment_color(label).startswith("#")
        assert palette.get_segment_marker(label)
        assert palette.get_segment_linestyle(label) is not None
        # hatch may legitimately be "" (no hatch) for the reference segment
        assert isinstance(palette.get_segment_hatch(label), str)


def test_colors_are_distinct() -> None:
    colors = [palette.get_segment_color(label) for label in palette.SEGMENT_LABELS]
    assert len(set(colors)) == len(colors)


def test_unknown_segment_raises() -> None:
    with pytest.raises(palette.UnknownSegmentError):
        palette.get_segment_color("not_a_real_segment")


def test_annotate_source_rejects_non_figure() -> None:
    with pytest.raises(TypeError):
        annotate_source(object())  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "script",
    ["scripts/check_palette_cvd_contrast.py", "scripts/check_no_local_color_literals.py"],
)
def test_static_check_passes(script: str) -> None:
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / script)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"{script} failed:\n{proc.stdout}\n{proc.stderr}"
    assert "[PASS]" in proc.stdout
