"""Reliability-diagram standard guards (IMP-V04 / issue #68).

Pins the shared builder's spec invariants from rendered-figure metadata:
square [0,1]x[0,1] axes at enforced equal aspect (the 45-degree diagonal),
count-proportional markers with Wilson intervals, sub-minimum-bin
de-emphasis, empty-bin omission (no line bridging), the in-canvas
disclaimer, fail-loud input validation — and, structurally, that no second
predicted-vs-observed implementation exists outside the shared builder (the
V6 defect class).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "shared" / "src"))

from visual_system.reliability import (  # noqa: E402 -- after sys.path insert
    CIRCULARITY_DISCLAIMER,
    reliability_diagram,
    reliability_frame,
)


def _fixture_frame(n: int = 5000, seed: int = 7):
    rng = np.random.default_rng(seed)
    y_prob = rng.beta(4, 3, size=n)
    y_true = (rng.random(n) < y_prob).astype(int)
    return reliability_frame(y_true, y_prob)


def test_geometry_square_unit_axes_equal_aspect() -> None:
    fig = reliability_diagram(_fixture_frame())
    ax = fig.axes[0]
    assert ax.get_xlim() == (0.0, 1.0)
    assert ax.get_ylim() == (0.0, 1.0)
    # matplotlib reports enforced equal aspect as 1.0
    assert float(ax.get_aspect()) == 1.0


def test_wilson_intervals_present_and_ordered() -> None:
    frame = _fixture_frame()
    assert {"ci_low", "ci_high", "count"} <= set(frame.columns)
    assert (frame["ci_low"] <= frame["observed_mean"]).all()
    assert (frame["observed_mean"] <= frame["ci_high"]).all()
    assert (frame["ci_low"] >= 0).all() and (frame["ci_high"] <= 1).all()
    # sparse bins get wider intervals than dense bins of similar rate
    widths = frame["ci_high"] - frame["ci_low"]
    assert widths[frame["count"].idxmin()] > widths[frame["count"].idxmax()]


def test_marker_area_scales_with_count() -> None:
    fig = reliability_diagram(_fixture_frame())
    ax = fig.axes[0]
    sizes = np.concatenate(
        [c.get_sizes() for c in ax.collections if hasattr(c, "get_sizes") and len(c.get_sizes())]
    )
    assert sizes.max() > sizes.min()  # unequal bins must not get equal weight


def test_empty_bins_break_the_line() -> None:
    # Bimodal predictions leave middle bins empty; the connecting line must
    # carry a NaN break instead of bridging the gap.
    rng = np.random.default_rng(3)
    y_prob = np.concatenate([rng.uniform(0.0, 0.15, 400), rng.uniform(0.85, 1.0, 400)])
    y_true = (rng.random(800) < y_prob).astype(int)
    frame = reliability_frame(y_true, y_prob)
    assert len(frame) < 10  # middle bins omitted, not interpolated
    fig = reliability_diagram(frame)
    ax = fig.axes[0]
    model_lines = [ln for ln in ax.get_lines() if len(ln.get_xdata()) > 2]
    assert model_lines and any(np.isnan(ln.get_ydata()).any() for ln in model_lines)


def test_disclaimer_rendered_inside_canvas() -> None:
    fig = reliability_diagram(_fixture_frame())
    ax = fig.axes[0]
    texts = " ".join(t.get_text() for t in ax.texts)
    assert "IMP-A01" in texts  # circularity caveat travels with every export


def test_blank_disclaimer_rejected() -> None:
    with pytest.raises(ValueError):
        reliability_diagram(_fixture_frame(), disclaimer="   ")


@pytest.mark.parametrize(
    ("y_true", "y_prob"),
    [
        (np.array([0, 1]), np.array([0.2, float("nan")])),
        (np.array([0, 1]), np.array([0.2, 1.3])),
        (np.array([0, 2]), np.array([0.2, 0.4])),
        (np.array([0, 1, 1]), np.array([0.2, 0.4])),
    ],
)
def test_invalid_inputs_abort(y_true: np.ndarray, y_prob: np.ndarray) -> None:
    with pytest.raises(ValueError):
        reliability_frame(y_true, y_prob)


def test_no_second_reliability_implementation() -> None:
    """The V6 recurrence guard: predicted-vs-observed drawing exists once.

    Any first-party file (outside the shared builder) that draws the
    calibration diagonal — a ``[0, 1], [0, 1]`` reference line — is a second
    reliability implementation and fails this test.
    """
    diagonal = re.compile(r"\[\s*0\s*,\s*1\s*\]\s*,\s*\[\s*0\s*,\s*1\s*\]")
    scan_dirs = (
        "reports",
        "scripts",
        "module_a_population_segmentation/src",
        "module_a_population_segmentation/app",
        "module_b_resource_allocation/src",
        "module_c_forecasting_scenarios/src",
    )
    allowed = REPO_ROOT / "shared" / "src" / "visual_system" / "reliability.py"
    offenders: list[str] = []
    for rel in scan_dirs:
        base = REPO_ROOT / rel
        if not base.is_dir():
            continue
        for path in base.rglob("*.py"):
            if path.resolve() == allowed:
                continue
            if diagonal.search(path.read_text(encoding="utf-8")):
                offenders.append(str(path.relative_to(REPO_ROOT)))
    assert not offenders, (
        "second predicted-vs-observed implementation(s) found — call "
        f"visual_system.reliability instead: {offenders}"
    )


def test_shared_wording_reexported_by_module_a() -> None:
    from population_segmentation.visualization.calibration_curves import (
        CIRCULARITY_DISCLAIMER as MODULE_A_DISCLAIMER,
    )

    assert MODULE_A_DISCLAIMER == CIRCULARITY_DISCLAIMER
