"""The committed conformance matrix must match what the validator generates."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_MATRIX = _REPO_ROOT / "schema_contracts" / "CONFORMANCE_MATRIX.md"
_SCRIPT = _REPO_ROOT / "scripts" / "generate_conformance_matrix.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("generate_conformance_matrix", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_conformance_matrix_committed_and_current() -> None:
    assert _MATRIX.is_file(), "schema_contracts/CONFORMANCE_MATRIX.md is missing"
    module = _load_script()
    assert _MATRIX.read_text(encoding="utf-8") == module.render(), (
        "CONFORMANCE_MATRIX.md is stale; run "
        "`poetry run python scripts/generate_conformance_matrix.py`"
    )


def test_conformance_matrix_lists_enforced_constraints() -> None:
    text = _MATRIX.read_text(encoding="utf-8")
    for constraint in ("nullable", "allowed_values", "pattern", "row_count", "unique_key"):
        assert constraint in text
