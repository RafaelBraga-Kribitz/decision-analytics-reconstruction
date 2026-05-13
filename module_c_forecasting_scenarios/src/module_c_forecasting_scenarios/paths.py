"""Repository and module-local path helpers."""

from __future__ import annotations

from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parent
_MODULE_ROOT = _PKG_ROOT.parent.parent
_REPO_ROOT = _MODULE_ROOT.parent


def repo_root() -> Path:
    return _REPO_ROOT


def module_config_dir() -> Path:
    return _MODULE_ROOT / "config"


def schema_contracts_dir() -> Path:
    return _REPO_ROOT / "schema_contracts"
