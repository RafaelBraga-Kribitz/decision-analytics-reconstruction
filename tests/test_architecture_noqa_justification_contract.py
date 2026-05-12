"""Regression: Ruff noqa directives must list rule codes and a trailing justification."""

from __future__ import annotations

import re
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]

_LINT_ROOTS = (
    _REPO / "module_a_population_segmentation" / "src",
    _REPO / "module_a_population_segmentation" / "tests",
    _REPO / "module_a_population_segmentation" / "app",
    _REPO / "module_b_resource_allocation" / "src",
    _REPO / "module_b_resource_allocation" / "tests",
    _REPO / "module_c_forecasting_scenarios" / "src",
    _REPO / "module_c_forecasting_scenarios" / "tests",
    _REPO / "tests",
    _REPO / "scripts",
)

_SKIP_NAMES = {"test_eda.py"}

_NOQA_ANY = re.compile(r"#\s*noqa\b", re.IGNORECASE)
_NOQA_CODES = re.compile(r"#\s*noqa\s*:\s*([A-Z0-9,\s]+)", re.IGNORECASE)


def _iter_py_files() -> list[Path]:
    out: list[Path] = []
    for root in _LINT_ROOTS:
        if not root.is_dir():
            continue
        for path in root.rglob("*.py"):
            if path.name in _SKIP_NAMES:
                continue
            if "__pycache__" in path.parts:
                continue
            out.append(path)
    return out


def _noqa_tail_justified(tail: str) -> bool:
    """True if tail after rule codes starts with a second comment or double-dash reason."""
    t = tail.strip()
    if t.startswith("--"):
        return len(t.strip("-").strip()) >= 3
    if t.startswith("#"):
        return len(t[1:].strip()) >= 3
    return False


def test_noqa_directives_use_codes_and_justification() -> None:
    """Reject blanket noqa markers and code-only markers without a reason tail."""
    bad: list[str] = []
    for path in _iter_py_files():
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if _NOQA_ANY.search(line) is None:
                continue
            m = _NOQA_CODES.search(line)
            if m is None:
                bad.append(f"{path.relative_to(_REPO)}:{i}: noqa without rule codes")
                continue
            tail = line[m.end() :]
            if not _noqa_tail_justified(tail):
                bad.append(f"{path.relative_to(_REPO)}:{i}: noqa missing justification after codes")
    assert not bad, "\n".join(bad)


def test_pyproject_selects_ruf100_unused_noqa() -> None:
    text = (_REPO / "pyproject.toml").read_text(encoding="utf-8")
    assert '"RUF100"' in text or "'RUF100'" in text or "RUF100" in text
    assert "[tool.ruff.lint]" in text
    assert "select" in text
