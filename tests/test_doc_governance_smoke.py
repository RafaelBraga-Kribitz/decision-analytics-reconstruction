"""Smoke-check documentation governance scripts exit 0 against the committed registry."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(script: str) -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script)],
        check=True,
        cwd=ROOT,
    )


def test_verify_doc_registry_ok() -> None:
    _run("verify_doc_registry.py")


def test_check_doc_frontmatter_ok() -> None:
    _run("check_doc_frontmatter.py")


def test_check_doc_drift_ok() -> None:
    _run("check_doc_drift.py")
