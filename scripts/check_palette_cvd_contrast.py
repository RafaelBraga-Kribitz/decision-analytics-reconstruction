#!/usr/bin/env python3
"""IMP-V01 static check: palette pairwise contrast under CVD simulation.

Simulates protanopia, deuteranopia, and tritanopia over every pairwise
comparison of the six canonical segment colors
(``shared/src/visual_system/palette.py::SEGMENT_COLORS``) and asserts each
pair's simulated perceptual distance (CIE76 deltaE in Lab space) exceeds a
documented minimum threshold. This is the recurrence guard for the
motivating defect: the prior six-color brand palette
(``reports/eda/generate_eda.py``'s former ``SEG_COLORS``, which paired RED
#e60000 with GREEN #2ca02c and PURPLE #9467bd with BLUE #1a6eb5) has pairs
that collapse toward the same perceived color under simulated dichromacy —
its worst pair falls to deltaE ~2.67, well below the threshold. The
Okabe-Ito-class replacement palette clears the threshold on all pairs. The
motivating-case sanity check in ``main()`` re-derives the old palette's
collapse on every run so the guard cannot silently rot.

Pure color math — no model fitting, no data load. Must complete in well
under the 5s budget IMP-V01 sets for this check.

Run standalone:
    poetry run python scripts/check_palette_cvd_contrast.py
"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "shared" / "src"))

from visual_system.palette import SEGMENT_COLORS  # noqa: E402

# Minimum acceptable CIE76 deltaE (Euclidean distance in CIE Lab space)
# between two segment colors *as simulated* under a given CVD type. A
# deltaE of ~2.3 is the commonly-cited single "just noticeable difference"
# threshold for one observer under ideal conditions; a six-way categorical
# legend read at a glance under simulated dichromacy needs much more margin
# than that, so this check requires at least 12.0 — roughly 5x JND.
#
# Calibration (see the module docstring's evidence and the motivating-case
# sanity check in main()): under the Machado matrices below, the retired
# six-color brand palette (generate_eda.py's former ``SEG_COLORS``) collapses
# to deltaE ~2.67 on its worst pair (purple vs blue under protanopia) and
# ~9.88 on its second-worst — both below 12.0, so this check would have
# caught it. The Okabe-Ito-class replacement palette clears 12.0 on all 15
# pairs under all three CVD types with margin (its worst comparison is
# ~15.7). The threshold therefore sits in the gap between the two palettes:
# the old one fails, the new one passes.
MIN_DELTA_E: float = 12.0

# Machado, Oliveira & Fernandes (2009), "A Physiologically-based Model for
# Simulation of Color Vision Deficiency" (IEEE TVCG), severity-1.0 (dichromat)
# transform matrices. These operate on LINEAR (gamma-decoded) sRGB, which is
# exactly the space this module converts into before applying them, and are
# the matrices embedded in widely-used CVD simulators. Unlike the simplified
# constant-luminance matrices, these correctly reproduce the red-green
# confusion the old palette suffered from (verified in the motivating-case
# sanity check below).
_CVD_MATRICES: dict[str, tuple[tuple[float, float, float], ...]] = {
    "protanopia": (
        (0.152286, 1.052583, -0.204868),
        (0.114503, 0.786281, 0.099216),
        (-0.003882, -0.048116, 1.051998),
    ),
    "deuteranopia": (
        (0.367322, 0.860646, -0.227968),
        (0.280085, 0.672501, 0.047413),
        (-0.011820, 0.042940, 0.968881),
    ),
    "tritanopia": (
        (1.255528, -0.076749, -0.178779),
        (-0.078411, 0.930809, 0.147602),
        (0.004733, 0.691367, 0.303900),
    ),
}

# Motivating case: the retired six-color brand palette that this module
# replaces (generate_eda.py's former ``SEG_COLORS`` — RED/BLUE/ORANGE/PURPLE/
# TEAL/GREEN). Documented here as literals, not imported, so this check's
# evidence trail survives even after the shared module changes. At least one
# of its pairs must fall below MIN_DELTA_E under simulation, or the check has
# lost the ability to catch the defect it was written for.
_MOTIVATING_OLD_PALETTE: dict[str, str] = {
    "rural_committed": "#e60000",  # RED — the motivating red-green collision
    "urban_high_volatility": "#1a6eb5",  # BLUE
    "structurally_dependent_bloc": "#ff7f0e",  # ORANGE
    "committed_opposition": "#9467bd",  # PURPLE
    "rural_low_propensity": "#17becf",  # TEAL
    "youth_volatile": "#2ca02c",  # GREEN — the motivating red-green collision
}


def _hex_to_srgb(hexcode: str) -> tuple[float, float, float]:
    hexcode = hexcode.lstrip("#")
    r = int(hexcode[0:2], 16) / 255.0
    g = int(hexcode[2:4], 16) / 255.0
    b = int(hexcode[4:6], 16) / 255.0
    return (r, g, b)


def _srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _matmul(
    m: tuple[tuple[float, float, float], ...], v: tuple[float, float, float]
) -> tuple[float, float, float]:
    r = tuple(sum(m[i][j] * v[j] for j in range(3)) for i in range(3))
    return (r[0], r[1], r[2])


def simulate_cvd(hexcode: str, cvd_type: str) -> tuple[float, float, float]:
    """Simulate a hex color as perceived under a given CVD type.

    Args:
        hexcode: sRGB hex color string, e.g. ``"#D55E00"``.
        cvd_type: One of ``"protanopia"``, ``"deuteranopia"``, ``"tritanopia"``.

    Returns:
        A linear-RGB tuple (post gamma-decode, pre gamma-encode) representing
        the simulated color, still in linear-light space (used directly for
        Lab conversion rather than round-tripped back to sRGB, since Lab
        conversion also expects linear-light input).

    Raises:
        KeyError: If ``cvd_type`` is not a recognized simulation matrix.

    Example:
        >>> simulate_cvd("#e60000", "deuteranopia")[0] > 0
        True
    """
    matrix = _CVD_MATRICES[cvd_type]
    srgb = _hex_to_srgb(hexcode)
    linear = tuple(_srgb_to_linear(c) for c in srgb)
    return _matmul(matrix, linear)  # type: ignore[return-value]


# sRGB D65 reference white, linear-RGB -> XYZ (IEC 61966-2-1).
_RGB_TO_XYZ = (
    (0.4124564, 0.3575761, 0.1804375),
    (0.2126729, 0.7151522, 0.0721750),
    (0.0193339, 0.1191920, 0.9503041),
)
_WHITE_XYZ = (0.95047, 1.00000, 1.08883)


def _xyz_to_lab(xyz: tuple[float, float, float]) -> tuple[float, float, float]:
    def f(t: float) -> float:
        delta = 6 / 29
        return t ** (1 / 3) if t > delta**3 else t / (3 * delta**2) + 4 / 29

    x, y, z = (xyz[i] / _WHITE_XYZ[i] for i in range(3))
    fx, fy, fz = f(x), f(y), f(z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def linear_rgb_to_lab(linear_rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    """Convert linear-light sRGB to CIE Lab (D65 white point).

    Args:
        linear_rgb: Linear-light RGB tuple, each component in roughly [0, 1]
            (may exceed the range slightly for out-of-gamut CVD-simulated
            colors; not clipped, since Lab distance still meaningfully
            orders "how different" two out-of-gamut simulated colors are).

    Returns:
        ``(L, a, b)`` tuple.

    Raises:
        None.

    Example:
        >>> l, a, b = linear_rgb_to_lab((1.0, 1.0, 1.0))
        >>> round(l)
        100
    """
    xyz = _matmul(_RGB_TO_XYZ, linear_rgb)
    return _xyz_to_lab(xyz)


def delta_e76(lab1: tuple[float, float, float], lab2: tuple[float, float, float]) -> float:
    """CIE76 deltaE: Euclidean distance between two Lab colors.

    Args:
        lab1: First color in Lab space.
        lab2: Second color in Lab space.

    Returns:
        Non-negative deltaE distance.

    Raises:
        None.

    Example:
        >>> delta_e76((50, 0, 0), (50, 0, 0))
        0.0
    """
    return sum((a - b) ** 2 for a, b in zip(lab1, lab2, strict=True)) ** 0.5


def pairwise_cvd_distances(colors: dict[str, str]) -> list[tuple[str, str, str, float]]:
    """Compute simulated-CVD pairwise deltaE for every segment pair and CVD type.

    Args:
        colors: ``segment_label -> hex color`` mapping.

    Returns:
        List of ``(seg_a, seg_b, cvd_type, delta_e)`` tuples, one per
        pairwise comparison per CVD type.

    Raises:
        None.

    Example:
        >>> rows = pairwise_cvd_distances({"a": "#D55E00", "b": "#0072B2"})
        >>> len(rows)
        3
    """
    rows: list[tuple[str, str, str, float]] = []
    for cvd_type in _CVD_MATRICES:
        for seg_a, seg_b in itertools.combinations(sorted(colors), 2):
            lab_a = linear_rgb_to_lab(simulate_cvd(colors[seg_a], cvd_type))
            lab_b = linear_rgb_to_lab(simulate_cvd(colors[seg_b], cvd_type))
            rows.append((seg_a, seg_b, cvd_type, delta_e76(lab_a, lab_b)))
    return rows


def main() -> int:
    rows = pairwise_cvd_distances(SEGMENT_COLORS)
    failures = [r for r in rows if r[3] < MIN_DELTA_E]

    # Motivating-case sanity check: the retired six-color brand palette must
    # itself have at least one pair below MIN_DELTA_E under simulation. If it
    # no longer does, the threshold or matrices have drifted to the point
    # where this check would have waved the original defect through — a
    # self-test of the guard, documenting why the threshold sits where it does.
    old_rows = pairwise_cvd_distances(_MOTIVATING_OLD_PALETTE)
    old_worst = min(old_rows, key=lambda r: r[3])
    motivating_intact = old_worst[3] < MIN_DELTA_E

    n_segments = len(SEGMENT_COLORS)
    n_pairs = n_segments * (n_segments - 1) // 2
    print(
        f"check_palette_cvd_contrast: {n_segments} segments, {n_pairs} pairs x "
        f"{len(_CVD_MATRICES)} CVD types = {len(rows)} comparisons, "
        f"threshold deltaE >= {MIN_DELTA_E}"
    )

    if not motivating_intact:
        print(
            "[FAIL] motivating-case sanity check broken: the retired brand palette's "
            f"worst pair ({old_worst[0]} vs {old_worst[1]} under {old_worst[2]}, "
            f"deltaE={old_worst[3]:.2f}) no longer falls below {MIN_DELTA_E} — threshold "
            "or matrices drifted; check_palette_cvd_contrast.py would no longer catch "
            "the original defect"
        )
        return 1

    if failures:
        print(f"[FAIL] check_palette_cvd_contrast.py: {len(failures)} pair(s) below threshold")
        for seg_a, seg_b, cvd_type, d in sorted(failures, key=lambda r: r[3]):
            print(f"       {seg_a} vs {seg_b} under {cvd_type}: deltaE={d:.2f} < {MIN_DELTA_E}")
        return 1

    worst = min(rows, key=lambda r: r[3])
    print(
        f"[PASS] check_palette_cvd_contrast.py: all {len(rows)} comparisons >= {MIN_DELTA_E} "
        f"(worst: {worst[0]} vs {worst[1]} under {worst[2]}, deltaE={worst[3]:.2f})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
