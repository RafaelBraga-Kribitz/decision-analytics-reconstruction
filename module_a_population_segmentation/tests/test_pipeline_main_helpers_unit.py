"""Unit tests for ``population_segmentation.pipeline.__main__._resolve_defaults``."""

from __future__ import annotations

from pathlib import Path

from population_segmentation.pipeline.__main__ import _resolve_defaults


def test_resolve_defaults_uses_cwd_when_none(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    c, a, o = _resolve_defaults(None, None, None)
    gen = tmp_path / "module_a_population_segmentation/config/generation.yaml"
    anc = tmp_path / "module_a_population_segmentation/config/calibration_anchors.yaml"
    assert c == gen.resolve()
    assert a == anc.resolve()
    assert o == (tmp_path / "data/processed").resolve()


def test_resolve_defaults_explicit_paths(tmp_path: Path) -> None:
    p1 = tmp_path / "g.yaml"
    p2 = tmp_path / "a.yaml"
    p3 = tmp_path / "out"
    p1.write_text("x: 1\n")
    p2.write_text("y: 2\n")
    p3.mkdir()
    c, a, o = _resolve_defaults(p1, p2, p3)
    assert c == p1.resolve()
    assert a == p2.resolve()
    assert o == p3.resolve()
