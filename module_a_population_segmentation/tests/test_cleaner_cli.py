"""CLI entry point for population_segmentation.data.cleaner (Makefile pipeline-dev)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml

CONFIG_PATH = Path(__file__).parent.parent / "config" / "generation.yaml"


@pytest.fixture
def tiny_raw_parquet(tmp_path: Path) -> Path:
    from population_segmentation.data.generator import generate_population
    from population_segmentation.data.raw_injector import inject_flaws

    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f)
    cfg["sample_size"] = 200
    base = generate_population(cfg, seed=7)
    df = inject_flaws(base, cfg, seed=7)
    p = tmp_path / "raw.parquet"
    df.to_parquet(p, index=False)
    return p


def test_cleaner_module_cli_writes_parquet(tiny_raw_parquet: Path, tmp_path: Path) -> None:
    out = tmp_path / "clean.parquet"
    cmd = [
        sys.executable,
        "-m",
        "population_segmentation.data.cleaner",
        "--input",
        str(tiny_raw_parquet),
        "--output",
        str(out),
        "--config",
        str(CONFIG_PATH),
        "--seed",
        "7",
    ]
    repo_root = Path(__file__).resolve().parents[2]
    subprocess.run(cmd, check=True, cwd=repo_root)
    assert out.is_file()
    clean = pd.read_parquet(out)
    assert len(clean) >= 200
    assert "cedula" in clean.columns
