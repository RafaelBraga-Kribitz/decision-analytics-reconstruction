"""Architecture contract: generator synthetic draws read YAML, not inline literals."""

from __future__ import annotations

from pathlib import Path


def test_generator_source_has_no_literal_structural_ballot_enc_rates() -> None:
    """Structural, ballot blank, and enc_source_raw rates belong in generation.yaml."""
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
    banned = (
        "np.where(rural_flags, 0.35, 0.12)",
        "rng.random(n) < 0.0241",
        "rng.random(n) < 0.0848",
        "p=[0.45, 0.50, 0.05]",
    )
    for snippet in banned:
        assert snippet not in text, f"Found literal synthetic rate in generator: {snippet!r}"
