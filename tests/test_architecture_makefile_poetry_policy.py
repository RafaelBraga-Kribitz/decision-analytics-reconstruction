"""Regression: root Makefile uses Poetry for Python and pre-commit."""

from __future__ import annotations

import re
from pathlib import Path

_MAKEFILE = Path(__file__).resolve().parents[1] / "Makefile"


def _makefile_text() -> str:
    return _MAKEFILE.read_text(encoding="utf-8")


def test_makefile_has_no_python_variable_recipes() -> None:
    text = _makefile_text()
    assert "PYTHON :=" not in text, "Remove PYTHON :=; use poetry run python in recipes"
    assert "$(PYTHON)" not in text, "Makefile must not invoke $(PYTHON); use poetry run python"


def test_makefile_precommit_uses_poetry_run() -> None:
    text = _makefile_text()
    assert (
        "\tpre-commit install" not in text
    ), "precommit target should use poetry run pre-commit install"
    assert "\tpre-commit run" not in text, "precommit target should use poetry run pre-commit run"
    match = re.search(r"^precommit:\n((?:\t[^\n]*\n)+)", text, re.MULTILINE)
    assert match is not None, "precommit target not found"
    body = match.group(1)
    assert "poetry run pre-commit install" in body
    assert "poetry run pre-commit run" in body


def test_generate_and_pipeline_dev_use_poetry_python() -> None:
    text = _makefile_text()
    for name in ("generate-dev", "pipeline-dev"):
        m = re.search(rf"^{name}:\n((?:\t[^\n]*\n)+)", text, re.MULTILINE)
        assert m is not None, f"target {name} not found"
        block = m.group(1)
        for line in block.strip().split("\n"):
            if not line.startswith("\t") or line.strip().startswith("#"):
                continue
            inner = line.lstrip("\t ")
            if not inner or inner.startswith(("\\", "-")):
                continue
            assert inner.startswith("poetry run python"), (name, line)
