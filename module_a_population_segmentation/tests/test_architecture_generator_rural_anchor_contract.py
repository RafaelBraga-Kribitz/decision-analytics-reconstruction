"""Architecture contract: rural rake anchor and urban fallback must not be literals in generator."""

from __future__ import annotations

from pathlib import Path


def test_generator_source_has_no_literal_rural_anchor_or_urban_fallback() -> None:
    """Rural rake anchor and urban fallback must come from YAML, not inline literals."""
    repo_root = Path(__file__).resolve().parents[2]
    gen_path = (
        repo_root
        / "module_a_population_segmentation"
        / "src"
        / "population_segmentation"
        / "data"
        / "generator.py"
    )
    text = gen_path.read_text(encoding="utf-8")
    banned = ("target=0.383", "get(dept, 0.617)")
    for snippet in banned:
        assert snippet not in text, f"Found literal rural/urban anchor in generator: {snippet!r}"
