"""Regression: ARCHITECTURE.md includes Mermaid diagrams, five contract tables, walkthrough."""

from __future__ import annotations

import re
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_ARCH = _REPO / "ARCHITECTURE.md"

_CONTRACT_HEADINGS = (
    "#### Contract: population_master_clean.yaml",
    "#### Contract: segment_labels.yaml",
    "#### Contract: participation_propensity.yaml",
    "#### Contract: allocation_output.yaml",
    "#### Contract: polls_clean_tracking_wave.yaml",
)

_MIN_TABLE_DATA_ROWS = 20


def _architecture_text() -> str:
    return _ARCH.read_text(encoding="utf-8")


def _count_markdown_table_body_rows(section: str) -> int:
    """Count data rows in the first markdown table in section (after header separator)."""
    lines = section.splitlines()
    sep_at: int | None = None
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("|") and "---" in s:
            sep_at = i
            break
    if sep_at is None:
        return 0
    count = 0
    for line in lines[sep_at + 1 :]:
        s = line.strip()
        if not s.startswith("|"):
            break
        if s.startswith("|") and "---" in s:
            break
        if s.count("|") >= 2:
            count += 1
    return count


def _extract_contract_section(md: str, heading: str) -> str:
    start = md.find(heading)
    assert start != -1, f"Missing heading {heading!r}"
    rest = md[start + len(heading) :]
    next_h = re.search(r"\n#### Contract: |\n### Walkthrough: |\n## ", rest)
    if next_h:
        return rest[: next_h.start()]
    return rest


def test_architecture_md_has_two_mermaid_blocks() -> None:
    text = _architecture_text()
    opens = text.count("```mermaid")
    assert opens >= 2, f"Expected at least 2 ```mermaid fences, got {opens}"


def test_architecture_md_has_walkthrough_heading() -> None:
    text = _architecture_text()
    assert "### Walkthrough: one voter" in text


def test_architecture_md_contract_tables_have_minimum_rows() -> None:
    md = _architecture_text()
    for heading in _CONTRACT_HEADINGS:
        section = _extract_contract_section(md, heading)
        n = _count_markdown_table_body_rows(section)
        assert (
            n >= _MIN_TABLE_DATA_ROWS
        ), f"{heading}: expected at least {_MIN_TABLE_DATA_ROWS} table data rows, got {n}"


def test_architecture_md_links_schema_contracts() -> None:
    text = _architecture_text()
    assert "schema_contracts/" in text
