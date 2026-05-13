"""Unit tests for CLI and QA helpers in ``population_segmentation.data.cleaner``."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from population_segmentation.data.cleaner import _parse_cli, _write_qa_report
from population_segmentation.utils.schema import CEDULA_INVALID, MUNICIPALITY, RURAL_FLAG


def test_write_qa_report_creates_markdown(tmp_path: Path) -> None:
    n = 5
    clean_df = pd.DataFrame(
        {
            MUNICIPALITY: ["X"] * n,
            CEDULA_INVALID: [False] * n,
            RURAL_FLAG: [False] * n,
        }
    )
    raw_df = pd.DataFrame({"k": range(n)})
    _write_qa_report(clean_df, raw_df, tmp_path)
    md_files = list(tmp_path.glob("qa_report_*.md"))
    assert len(md_files) == 1
    text = md_files[0].read_text(encoding="utf-8")
    assert "QA Report" in text
    assert "Input rows: 5" in text
    assert "Output rows: 5" in text


def test_parse_cli_reads_argv(monkeypatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "cleaner",
            "--input",
            "/tmp/in.parquet",
            "--output",
            "/tmp/out.parquet",
            "--config",
            "/tmp/gen.yaml",
            "--qa-report-dir",
            "/tmp/qa",
        ],
    )
    ns = _parse_cli()
    assert ns.input == Path("/tmp/in.parquet")
    assert ns.output == Path("/tmp/out.parquet")
    assert ns.config == Path("/tmp/gen.yaml")
    assert ns.qa_report_dir == Path("/tmp/qa")
