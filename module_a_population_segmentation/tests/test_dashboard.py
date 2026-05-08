"""Smoke tests for Streamlit dashboard module."""

from __future__ import annotations

from module_a_population_segmentation.app.streamlit_dashboard import _build_sample


def test_dashboard_data_builder_smoke() -> None:
    raw, feat, seg, prop, anc = _build_sample(5000)
    assert len(raw) > 0
    assert len(feat) > 0
    assert "silhouette" in seg
    assert "metrics" in prop
    assert "national" in anc
