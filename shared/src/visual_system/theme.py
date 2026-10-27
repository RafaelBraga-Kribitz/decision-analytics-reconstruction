# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""The Braga design system v2.1 for every figure this repository draws.

Every chart-producing surface (the EDA factory, the Module A report charts,
the battleground investigation, the PPC plot, the reliability builder, the
decision panel) installs the design system through :func:`apply_theme`, which
is ``bk_theme.apply`` from bk-viz 2.0.0. Colours come from bk-viz roles only;
this module and its callers hold no hex value (D-053).

:func:`conform_figure` is the save-time guard every governed figure passes
through. It enforces the type rules that a 50-chart factory cannot keep by
hand at each call site:

* no text below 12px (``bk.SIZE["mono-sm"]``, 9.5pt at the 96px/in figure
  maths);
* colour lives in marks, never in type: every label is ``ink`` or ``ink-2``
  (or ``surface`` where a label sits on a dark mark); a hue handed to a text
  artist is mapped back to ink, a grey to ink-2;
* type is opaque (no alpha on text) and square (no rounded label boxes);
* titles are set in BKribitz, everything else in BKribitz Mono (bk default).
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

import bk_theme as bk

if TYPE_CHECKING:
    from matplotlib.figure import Figure

#: The type floor in points: 12px at the system's 96px/in figure maths.
TYPE_FLOOR_PT: float = bk.SIZE["mono-sm"]


def apply_theme(mode: str = "light") -> None:
    """Install the design system (bk-viz) as matplotlib rcParams.

    Args:
        mode: ``"light"`` or ``"dark"``.

    Returns:
        None.

    Raises:
        ValueError: If ``mode`` is not a design-system mode.

    Example:
        >>> apply_theme("light")
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        bk.apply(mode)


def _luminance(rgb: tuple[float, float, float]) -> float:
    def lin(x: float) -> float:
        return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def text_role_for(color: object) -> str:
    """Map any colour handed to a text artist onto a type role.

    Args:
        color: Any matplotlib colour spec.

    Returns:
        ``"ink"`` for a hue or a near-black, ``"ink-2"`` for a grey, and
        ``"surface"`` for a near-white (a label set on a dark mark).

    Raises:
        ValueError: If ``color`` is not a matplotlib colour.

    Example:
        >>> text_role_for("white")
        'surface'
    """
    from matplotlib.colors import to_rgb

    rgb = to_rgb(color)  # type: ignore[arg-type]
    for role in ("ink", "ink-2", "surface"):
        if to_rgb(bk.c(role)) == rgb:
            return role
    y = _luminance(rgb)
    if y > 0.6:
        return "surface"
    if max(rgb) - min(rgb) < 0.12:
        return "ink" if y < 0.05 else "ink-2"
    return "ink"


def conform_figure(fig: Figure) -> None:
    """Bring every text artist of ``fig`` onto the design system's type rules.

    Args:
        fig: The figure, fully drawn, just before it is saved.

    Returns:
        None.

    Raises:
        None.

    Example:
        >>> import matplotlib
        >>> matplotlib.use("Agg")
        >>> import matplotlib.pyplot as plt
        >>> fig, ax = plt.subplots()
        >>> _ = ax.set_title("t", fontsize=6, color="red")
        >>> conform_figure(fig)
        >>> ax.title.get_fontsize() >= TYPE_FLOOR_PT
        True
    """
    from matplotlib.text import Text

    titles = _title_ids(fig)
    on_image: dict[int, str] = {}
    for ax in fig.axes:
        on_image.update(_heatmap_label_roles(ax))

    for text in fig.findobj(Text):
        if text.get_text():
            _conform_text(text, on_image.get(id(text)), id(text) in titles)


def _title_ids(fig: Figure) -> set[int]:
    """Ids of the figure's axes titles and suptitle (set in BKribitz display)."""
    titles = {id(ax.title) for ax in fig.axes}
    titles |= {id(getattr(ax, "_left_title", None)) for ax in fig.axes}
    suptitle = getattr(fig, "_suptitle", None)
    if suptitle is not None:
        titles.add(id(suptitle))
    return titles


def _heatmap_label_roles(ax: object) -> dict[int, str]:
    """For a heatmap axes: drop its gridlines and pick ink/surface per cell label.

    A label on a heatmap cell reads in ink or surface, whichever contrasts
    with that cell's colour; hairline gridlines never sit on a heatmap.
    """
    import numpy as np

    images = getattr(ax, "images", [])
    if not images:
        return {}
    ax.grid(False)  # type: ignore[attr-defined]
    im = images[0]
    arr = im.get_array()
    if arr is None or arr.ndim != 2:
        return {}
    roles: dict[int, str] = {}
    for t in ax.texts:  # type: ignore[attr-defined]
        if t.get_transform() != ax.transData:  # type: ignore[attr-defined]
            continue
        x, y = t.get_position()
        i, j = round(float(y)), round(float(x))
        inside = 0 <= i < arr.shape[0] and 0 <= j < arr.shape[1]
        if inside and not np.ma.is_masked(arr[i, j]) and np.isfinite(arr[i, j]):
            roles[id(t)] = label_on(im.to_rgba(arr[i, j]))
    return roles


def _conform_text(text: object, on_mark: str | None, is_title: bool) -> None:
    """Apply the type rules to one text artist (see :func:`conform_figure`)."""
    from matplotlib.patches import FancyBboxPatch

    if on_mark is not None:
        text.set_color(on_mark)  # type: ignore[attr-defined]
    text.set_fontsize(max(text.get_fontsize(), TYPE_FLOOR_PT))  # type: ignore[attr-defined]
    text.set_color(bk.c(text_role_for(text.get_color())))  # type: ignore[attr-defined]
    text.set_alpha(None)  # type: ignore[attr-defined]
    if is_title:
        size = text.get_fontsize()  # type: ignore[attr-defined]
        text.set_fontproperties(bk.font("display", "bold", size))  # type: ignore[attr-defined]
    box = text.get_bbox_patch()  # type: ignore[attr-defined]
    if isinstance(box, FancyBboxPatch):
        box.set_boxstyle("square", pad=0.35)
        box.set_facecolor(bk.c("surface-2"))
        box.set_edgecolor(bk.c("rule-c"))
        box.set_alpha(None)


def parts_of_whole(n: int) -> list[str]:
    """Structure greys for ``n`` parts of a whole (IBCS), darkest first.

    Samples the four ``categorical-grey`` stops evenly so two or three parts
    stay far apart in lightness; wraps past four via ``bk.neutral_ramp``.

    Args:
        n: Number of parts.

    Returns:
        ``n`` colours resolved in the current bk mode.

    Raises:
        None.

    Example:
        >>> len(parts_of_whole(3))
        3
    """
    stops = bk.palette("categorical-grey")
    if n <= 1:
        return stops[:1]
    if n > len(stops):
        return bk.neutral_ramp(n)
    step = (len(stops) - 1) / (n - 1)
    return [stops[round(i * step)] for i in range(n)]


def label_on(facecolor: object) -> str:
    """Ink or surface, whichever reads better on ``facecolor`` (a label on a mark).

    Args:
        facecolor: The mark's fill, any matplotlib colour spec.

    Returns:
        ``bk.c("ink")`` or ``bk.c("surface")``.

    Raises:
        ValueError: If ``facecolor`` is not a matplotlib colour.

    Example:
        >>> label_on(bk.c("ink")) == bk.c("surface")
        True
    """
    from matplotlib.colors import to_rgb

    def ratio(a: object, b: object) -> float:
        la, lb = _luminance(to_rgb(a)), _luminance(to_rgb(b))  # type: ignore[arg-type]
        return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)

    return max((bk.c("ink"), bk.c("surface")), key=lambda t: ratio(t, facecolor))


def scale_cmap(name: str, *, reverse: bool = False, n: int = 256) -> object:
    """A matplotlib colormap built from a design-system scale.

    Args:
        name: ``"seq"`` (index 0 darkest), ``"div"`` (good to bad), ``"two"``
            (ultramarine to ochre, neither side good), ``"long"`` or ``"short"``.
        reverse: Reverse the stop order (``seq`` reversed runs light to dark,
            so a larger value reads darker).
        n: Colormap resolution.

    Returns:
        A ``LinearSegmentedColormap``; NaN cells render in ``surface-3``.

    Raises:
        KeyError: If ``name`` is not a bk-viz scale.

    Example:
        >>> scale_cmap("seq", reverse=True).name
        'bk_seq'
    """
    from matplotlib.colors import LinearSegmentedColormap

    cmap = LinearSegmentedColormap.from_list(f"bk_{name}", bk.palette(name, reverse=reverse), N=n)
    cmap.set_bad(bk.c("surface-3"))
    return cmap
