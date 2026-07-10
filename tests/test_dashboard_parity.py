"""Dashboard <-> static report parity guards (IMP-V06 / issue #70).

Asserted at builder level against the shared constants — no browser, no
Streamlit runtime:

1. The dashboard's segment-size chart ranks segments in the shared
   ``SEGMENT_DISPLAY_ORDER``, colors them from the shared palette, and
   direct-labels count + percentage — the same identity as static A1.
2. The static factory re-derives its ordering from the same shared constant
   (a change that updates one surface and strands the other fails here).
3. The SHAP tab never passes a plotting call's return value to
   ``st.pyplot``, and the explicit-capture render is deterministic on the
   pinned shap version.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "shared" / "src"))

from visual_system.palette import (  # noqa: E402 -- after sys.path insert
    SEGMENT_COLORS,
    SEGMENT_DISPLAY_ORDER,
    SEGMENT_LABELS,
)

DASHBOARD = REPO_ROOT / "module_a_population_segmentation" / "app" / "streamlit_dashboard.py"
EDA_FACTORY = REPO_ROOT / "reports" / "eda" / "generate_eda.py"


def _profile_fixture() -> pd.DataFrame:
    sizes = {label: 1000 + 100 * i for i, label in enumerate(SEGMENT_LABELS)}
    return pd.DataFrame(
        {
            "segment_label": list(sizes),
            "segment_size": list(sizes.values()),
        }
    )


def test_display_order_is_a_permutation_of_canonical_labels() -> None:
    assert sorted(SEGMENT_DISPLAY_ORDER) == sorted(SEGMENT_LABELS)


def test_dashboard_segment_chart_matches_static_identity() -> None:
    from population_segmentation.visualization.segment_profiles import segment_size_chart

    fig = segment_size_chart(_profile_fixture())
    # category rank comes from the shared display order
    assert tuple(fig.layout.yaxis.categoryarray) == tuple(SEGMENT_DISPLAY_ORDER)
    by_name = {trace.name: trace for trace in fig.data}
    assert set(by_name) == set(SEGMENT_LABELS)
    for label, trace in by_name.items():
        # shared-palette color per segment, never a library default
        assert trace.marker.color == SEGMENT_COLORS[label]
        # horizontal, direct-labeled with count and percentage
        assert trace.orientation == "h"
        text = " ".join(trace.text)
        assert re.search(r"\d[\d,]* \(\d+\.\d%\)", text)


def test_static_factory_orders_from_shared_constant() -> None:
    source = EDA_FACTORY.read_text(encoding="utf-8")
    assert "SEGMENT_DISPLAY_ORDER" in source
    assert re.search(r"SEG_ORDER\s*=\s*list\(SEGMENT_DISPLAY_ORDER\)", source), (
        "generate_eda.py must derive SEG_ORDER from the shared "
        "visual_system.palette.SEGMENT_DISPLAY_ORDER, not a local list"
    )
    # no second hardcoded ordering literal left behind
    assert source.count('"youth_volatile",\n    "urban_high_volatility"') == 0


def test_shap_tab_never_passes_plot_return_to_st_pyplot() -> None:
    source = DASHBOARD.read_text(encoding="utf-8")
    assert not re.search(r"\w+\s*=\s*shap\.summary_plot", source), (
        "shap.summary_plot returns None on the pinned shap version — its "
        "return value must never be captured and rendered"
    )
    assert "st.pyplot(fig_shap" in source  # explicit owned-figure render


def test_shap_explicit_capture_is_deterministic() -> None:
    shap = pytest.importorskip("shap")
    import io

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    rng = np.random.default_rng(0)
    x = rng.normal(size=(80, 4))
    shap_vals = rng.normal(size=(80, 4))

    def render() -> bytes:
        plt.close("all")
        shap.summary_plot(shap_vals, x, feature_names=list("abcd"), plot_type="bar", show=False)
        fig = plt.gcf()
        assert fig.axes, "summary_plot drew no axes"
        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        plt.close(fig)
        return buf.getvalue()

    assert render() == render()
