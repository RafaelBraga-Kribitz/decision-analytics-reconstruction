"""Regression: raw_injector must not subscript DataFrames with bare column string literals."""

from __future__ import annotations

import re
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_RAW_INJECTOR = (
    _REPO
    / "module_a_population_segmentation"
    / "src"
    / "population_segmentation"
    / "data"
    / "raw_injector.py"
)


def test_raw_injector_has_no_df_string_column_subscripts() -> None:
    """Column access must go through schema.py names (e.g. df[CEDULA]), not df["cedula"]."""
    text = _RAW_INJECTOR.read_text(encoding="utf-8")
    assert (
        re.search(r"\bdf\[\s*['\"]", text) is None
    ), "Use schema constants for DataFrame columns, not df['literal'] / df[\"literal\"]"
    assert (
        re.search(r"\.loc\[[^\]]*,\s*['\"]", text) is None
    ), "Use schema constants in df.loc[..., COL], not string literals for column axis"
    assert (
        re.search(r"\.at\[[^\]]*,\s*['\"]", text) is None
    ), "Use schema constants in df.at[row, COL], not string literals for column axis"


def test_raw_injector_imports_schema_module() -> None:
    text = _RAW_INJECTOR.read_text(encoding="utf-8")
    assert "from population_segmentation.utils.schema import" in text
    assert "CEDULA" in text and "DEPARTMENT" in text
