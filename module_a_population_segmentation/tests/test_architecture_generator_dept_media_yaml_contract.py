"""Architecture contract: generator must not embed per-department media/NBI dicts in src."""

from __future__ import annotations

from pathlib import Path


def test_generator_source_has_no_legacy_dept_media_module_dicts() -> None:
    """TV/radio/NBI by department live under ``generator_dept_media_nbi`` in generation.yaml."""
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
    for name in ("_TV_BY_DEPT", "_RADIO_BY_DEPT", "_NBI_RURAL_BY_DEPT", "_NBI_URBAN_BY_DEPT"):
        assert name not in text, f"Legacy inline table {name} must not remain in generator.py"
