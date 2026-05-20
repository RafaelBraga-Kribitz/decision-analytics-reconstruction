"""Regression: transaction boundary harness (unit lock gate + docs pointers)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import yaml

_REPO = Path(__file__).resolve().parents[1]
_PRE_COMMIT = _REPO / ".pre-commit-config.yaml"
_RULE_TXN = _REPO / ".cursor" / "rules" / "10-transaction-boundaries.mdc"
_TASK_TXN = _REPO / ".cursor" / "commands" / "task-transaction.md"
_PLAYBOOK = _REPO / "docs" / "ai_harness" / "CONTROLLED_WORKFLOW_PLAYBOOK.md"


def _load_gate_module() -> Any:
    path = _REPO / "scripts" / "transaction_commit_gate.py"
    spec = importlib.util.spec_from_file_location("transaction_commit_gate", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_transaction_rule_and_command_exist() -> None:
    text = _RULE_TXN.read_text(encoding="utf-8")
    assert "alwaysApply: true" in text
    assert "UNIT_ID" in text
    assert _TASK_TXN.is_file()
    assert "task-transaction" in _PLAYBOOK.read_text(encoding="utf-8")


def test_pre_commit_lists_transaction_hooks() -> None:
    data = yaml.safe_load(_PRE_COMMIT.read_text(encoding="utf-8"))
    locals_ = [r for r in data["repos"] if r.get("repo") == "local"]
    ids = {h["id"] for h in locals_[0]["hooks"]}
    assert "transaction-gate-staged" in ids
    assert "transaction-gate-commit-msg" in ids
    txn_pre = next(h for h in locals_[0]["hooks"] if h["id"] == "transaction-gate-staged")
    assert txn_pre.get("stages") == ["pre-commit"]
    txn_msg = next(h for h in locals_[0]["hooks"] if h["id"] == "transaction-gate-commit-msg")
    assert txn_msg.get("stages") == ["commit-msg"]


def test_validate_staged_allows_subset() -> None:
    mod = _load_gate_module()
    lock = {
        "unit_id": "TASK-TEST-01",
        "status": "in_progress",
        "unit_impact_set": ["scripts/foo.py", "tests/bar.py"],
        "allowed_paths": ["scripts/", "tests/"],
        "diff_budget_max": 15,
    }
    ok, errs = mod.validate_staged(
        lock,
        ["scripts/foo.py"],
        branch="feat/x",
        strict_budget=False,
        allow_large=False,
    )
    assert ok and not errs


def test_validate_staged_rejects_extra_file() -> None:
    mod = _load_gate_module()
    lock = {
        "unit_id": "TASK-TEST-01",
        "status": "in_progress",
        "unit_impact_set": ["scripts/foo.py"],
        "allowed_paths": ["scripts/"],
        "diff_budget_max": 15,
    }
    ok, errs = mod.validate_staged(
        lock,
        ["scripts/foo.py", "other.md"],
        branch="feat/x",
        strict_budget=False,
        allow_large=False,
    )
    assert not ok
    assert any("not in unit_impact_set" in e for e in errs)


def test_validate_staged_skips_when_no_staged() -> None:
    mod = _load_gate_module()
    lock = {
        "unit_id": "TASK-TEST-01",
        "status": "in_progress",
        "unit_impact_set": [],
        "allowed_paths": [],
    }
    ok, errs = mod.validate_staged(
        lock,
        [],
        branch="feat/x",
        strict_budget=False,
        allow_large=False,
    )
    assert ok and not errs


def test_validate_message_requires_unit_id() -> None:
    mod = _load_gate_module()
    lock = {"unit_id": "TASK-TEST-01"}
    ok, errs = mod.validate_message(lock, "fix: typo\n", require_conventional=True)
    assert not ok
    assert any("UNIT_ID" in e or "unit_id" in e.lower() for e in errs)


def test_validate_message_passes_with_unit_id() -> None:
    mod = _load_gate_module()
    lock = {"unit_id": "TASK-TEST-01"}
    ok, errs = mod.validate_message(
        lock,
        "fix(test): TASK-TEST-01 correct assertion\n",
        require_conventional=True,
    )
    assert ok and not errs


def test_runtime_readme_documents_lock_fields() -> None:
    readme = (_REPO / ".cursor" / "runtime" / "README.md").read_text(encoding="utf-8")
    assert "current_unit.json" in readme
    assert "unit_impact_set" in readme
