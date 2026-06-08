"""Regression: governance gate() resolves finding IDs and enforces closed ratchet."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]


def _load_governance_check():
    path = _REPO / "scripts" / "_governance_check.py"
    spec = importlib.util.spec_from_file_location("_governance_check", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_governance_check"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_status_resolves_suffixed_finding_yaml() -> None:
    mod = _load_governance_check()
    assert mod._status("F-001") == "closed"
    assert mod._status("F-002") == "closed"
    assert mod._status("F-CHARTER-SIZE") is None
    assert mod._status("F-CLAUDE-MD") is None


def test_gate_fails_regression_when_finding_closed() -> None:
    mod = _load_governance_check()
    rc = mod.gate("F-001", "test_ratchet.py", False, "simulated charter sprawl")
    assert rc == 1


def test_check_scripts_use_canonical_finding_ids() -> None:
    charter = (_REPO / "scripts" / "check_charter_size.py").read_text(encoding="utf-8")
    claude = (_REPO / "scripts" / "check_claude_md.py").read_text(encoding="utf-8")
    assert "F-001" in charter
    assert "F-CHARTER-SIZE" not in charter
    assert "F-002" in claude
    assert "F-CLAUDE-MD" not in claude
