"""Residual chart-encoding guards (IMP-V05 / issue #69).

Static negative constraints from the spec, pinned so the retired encodings
cannot come back:

* no twin-axis (``twinx``) chart in the canonical figure factory;
* no alpha-only nested-interval stacking in the PPC plot (bands must differ
  in lightness, with direct level labels);
* A4's heatmap color scale is observed-range with on-figure disclosure, not
  a fixed [0, 1] span;
* the Plotly explorer renders the HDI as a filled band labeled from the
  configured ``hdi_prob``, not dotted boundary lines;
* S2's quadrant labels are derived from quadrant position, not hand-written
  strings (the AUD-S2 defect class).
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EDA_FACTORY = REPO_ROOT / "reports" / "eda" / "generate_eda.py"
PPC_PLOT = (
    REPO_ROOT
    / "module_c_forecasting_scenarios"
    / "src"
    / "module_c_forecasting_scenarios"
    / "viz"
    / "ppc_plot.py"
)
EXPLORER = PPC_PLOT.parent / "plotly_explorer.py"


def test_no_twinx_in_canonical_library() -> None:
    source = EDA_FACTORY.read_text(encoding="utf-8")
    assert ".twinx(" not in source, (
        "twin-axis charts pair unrelated quantitative scales and are banned "
        "from the canonical figure factory (IMP-V05) — use small multiples"
    )


def test_ppc_bands_are_lightness_stepped_not_alpha_only() -> None:
    source = PPC_PLOT.read_text(encoding="utf-8")
    fills = re.findall(r'fill_between\([^)]*color="(#[0-9a-fA-F]{6})"', source)
    band_colors = re.findall(r'\(q\w+, q\w+, "(#[0-9a-fA-F]{6})", "\d+%"\)', source)
    colors = band_colors or fills
    assert len(colors) >= 3, "expected three nested PPC interval bands"
    assert len(set(colors)) == len(colors), (
        "nested PPC intervals share one color — alpha-only stacking is not a "
        "permitted encoding (IMP-V05); use distinct lightness steps"
    )
    # direct right-edge level labels, decodable without the legend
    for level in ("95%", "80%", "50%"):
        assert f'"{level}"' in source


def test_a4_scale_is_observed_range_with_disclosure() -> None:
    source = EDA_FACTORY.read_text(encoding="utf-8")
    a4 = re.search(r'@safe_chart\("A4"\).*?@safe_chart\("A5"\)', source, re.S)
    assert a4 is not None
    block = a4.group(0)
    assert "vmin=0, vmax=1" not in block, "A4 must not pin a fixed [0,1] scale"
    assert "nanmin" in block and "nanmax" in block, "A4 scale must derive from observed range"
    assert "observed range" in block, "A4 must disclose its color-scale range on the figure"


def test_explorer_hdi_is_filled_band_with_configured_level() -> None:
    source = EXPLORER.read_text(encoding="utf-8")
    assert 'fill="tonexty"' in source, "explorer HDI must render as a filled band"
    assert 'dash="dot"' not in source, "dotted HDI boundary lines were retired (IMP-V05)"
    assert (
        "hdi_prob" in source and "load_sampler_config" in source
    ), "the HDI label must derive from the configured hdi_prob"
    assert (
        '"95% HDI"' not in source and "'95% HDI'" not in source
    ), "hardcoded interval labels are banned — derive from hdi_prob"


def test_s2_quadrant_labels_are_derived_not_hardcoded() -> None:
    source = EDA_FACTORY.read_text(encoding="utf-8")
    s2 = re.search(r'@safe_chart\("S2"\).*?@safe_chart\("S3"\)', source, re.S)
    assert s2 is not None
    block = s2.group(0)
    # the AUD-S2 defect class: four hand-written quadrant strings that can
    # disagree with their placement. Labels must be computed from the same
    # booleans that position them.
    assert re.search(
        r"for reach_high in .*for prop_high in", block, re.S
    ), "S2 quadrant labels must be derived from quadrant position"
    assert "High Reach\\nHigh Propensity" not in block
    assert "median" in block, "S2 must disclose the median-split semantics"
