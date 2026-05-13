"""Architecture contract: cleaner must not embed imputation priors as literals."""

from __future__ import annotations

from pathlib import Path


def test_cleaner_source_has_no_inline_imputation_magic_numbers() -> None:
    """Imputation rates belong in generation.yaml (language_priors, cleaner_synthetic_defaults)."""
    repo_root = Path(__file__).resolve().parents[2]
    cleaner_path = (
        repo_root
        / "module_a_population_segmentation"
        / "src"
        / "population_segmentation"
        / "data"
        / "cleaner.py"
    )
    text = cleaner_path.read_text(encoding="utf-8")
    banned_snippets = (
        "p=[0.46, 0.34, 0.15, 0.05]",
        "rng.random(len(df)) < 0.383",
        "rng.random(len(df)) < 0.25",
    )
    for snippet in banned_snippets:
        assert snippet not in text, f"Found literal imputation prior in cleaner: {snippet!r}"
