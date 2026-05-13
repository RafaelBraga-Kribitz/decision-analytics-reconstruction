"""Regression: root Makefile `test` runs pytest with coverage (DRY via COV_FLAGS)."""

from __future__ import annotations

import re
from pathlib import Path

_MAKEFILE = Path(__file__).resolve().parents[1] / "Makefile"


def _makefile_text() -> str:
    return _MAKEFILE.read_text(encoding="utf-8")


def _test_target_body(text: str) -> str:
    match = re.search(r"^test:\n((?:\t[^\n]*\n)+)", text, re.MULTILINE)
    assert match is not None, "Makefile target test: not found"
    return match.group(1)


def _cov_flags_line(text: str) -> str:
    match = re.search(r"^COV_FLAGS\s*:=\s*(.+)$", text, re.MULTILINE)
    assert match is not None, "Makefile COV_FLAGS variable not found"
    return match.group(1)


def test_makefile_test_target_invokes_pytest_with_coverage() -> None:
    text = _makefile_text()
    body = _test_target_body(text)
    assert "poetry run pytest" in body, "test: must invoke poetry run pytest"
    assert (
        '-m "not slow"' in body or "-m 'not slow'" in body
    ), "test: must exclude slow marker for default dev/CI speed"
    assert (
        "$(COV_FLAGS)" in body
    ), "test: must append $(COV_FLAGS) for coverage (DRY with coverage target)"

    cov = _cov_flags_line(text)
    for src_var in ("$(MODULE_A_SRC)", "$(MODULE_B_SRC)", "$(MODULE_C_SRC)"):
        needle = f"--cov={src_var}"
        assert needle in cov, f"COV_FLAGS must include {needle!r}, got {cov!r}"
    assert "--cov-report=term-missing" in cov
    assert "--cov-report=xml" in cov


def test_makefile_coverage_target_reuses_cov_flags() -> None:
    text = _makefile_text()
    match = re.search(r"^coverage:\n((?:\t[^\n]*\n)+)", text, re.MULTILINE)
    assert match is not None, "Makefile target coverage: not found"
    body = match.group(1)
    assert "poetry run pytest" in body
    assert "$(COV_FLAGS)" in body, "coverage: must use $(COV_FLAGS) same as test (DRY)"
    assert "-m" not in body, "coverage: must not filter markers (full suite vs make test)"
