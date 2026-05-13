"""Unit tests for thin I/O helpers in ``population_segmentation.data.generator``."""

from __future__ import annotations

from pathlib import Path

from population_segmentation.data.generator import _load_config


def test_load_config_reads_yaml(tmp_path: Path) -> None:
    cfg_path = tmp_path / "generation.yaml"
    cfg_path.write_text("sample_size: 42\nfoo: bar\n", encoding="utf-8")
    cfg = _load_config(cfg_path)
    assert cfg["sample_size"] == 42
    assert cfg["foo"] == "bar"
