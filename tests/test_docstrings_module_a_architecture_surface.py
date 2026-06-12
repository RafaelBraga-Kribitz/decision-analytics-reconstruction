"""Regression: Module A architecture-surface public callables use Google-style docstrings.

Mirrors the file list in ``tests/test_architecture_module_a_surface.py`` (required
``population_segmentation`` sources under ``module_a_population_segmentation/src``).
Each public function must include the section headers ``Args:``, ``Returns:``,
``Raises:``, and ``Example:`` (Project Action List code-quality gate).
"""

from __future__ import annotations

import ast
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SRC = _REPO / "module_a_population_segmentation" / "src" / "population_segmentation"

_REQUIRED_UNDER_SRC = [
    _SRC / "data" / "generator.py",
    _SRC / "data" / "raw_injector.py",
    _SRC / "data" / "cleaner.py",
    _SRC / "data" / "validator.py",
    _SRC / "features" / "demographic.py",
    _SRC / "features" / "behavioral.py",
    _SRC / "features" / "reachability.py",
    _SRC / "models" / "segmentation.py",
    _SRC / "models" / "propensity.py",
    _SRC / "evaluation" / "schema_validator.py",
    _SRC / "pipeline" / "export.py",
    _SRC / "pipeline" / "__main__.py",
]

_GOOGLE_MARKERS = ("Args:", "Returns:", "Raises:", "Example:")


def _is_public_method(item: ast.AST) -> bool:
    if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False
    if item.name.startswith("__") and item.name.endswith("__"):
        return item.name == "__init__"
    return not item.name.startswith("_")


def _iter_public_functions(tree: ast.AST):
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith(
            "_"
        ):
            yield node
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if _is_public_method(item):
                    yield item


def _google_docstring_complete(doc: str) -> bool:
    text = doc.strip()
    if len(text) < 40:
        return False
    return all(marker in text for marker in _GOOGLE_MARKERS)


def test_module_a_architecture_surface_public_functions_have_google_docstrings() -> None:
    missing: list[str] = []
    incomplete: list[str] = []
    for path in _REQUIRED_UNDER_SRC:
        assert path.is_file(), f"Missing Module A source file: {path.relative_to(_REPO)}"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        rel = path.relative_to(_REPO)
        for fn in _iter_public_functions(tree):
            doc = ast.get_docstring(fn)
            label = f"{rel}:{fn.lineno} {fn.name}"
            if not doc or not doc.strip():
                missing.append(label)
            elif not _google_docstring_complete(doc):
                incomplete.append(label)

    assert not missing, "Public functions missing docstrings:\n" + "\n".join(missing)
    assert (
        not incomplete
    ), "Public functions missing Google sections (Args/Returns/Raises/Example):\n" + "\n".join(
        incomplete
    )
