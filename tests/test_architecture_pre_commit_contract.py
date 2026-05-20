"""Regression: pre-commit config lists Ruff, Black, Pyright, and a pytest smoke hook."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_REPO = Path(__file__).resolve().parents[1]
_PRE_COMMIT = _REPO / ".pre-commit-config.yaml"


def _hook(repos: list[dict[str, Any]], repo_url: str, hook_id: str) -> dict[str, Any]:
    for r in repos:
        if r.get("repo") != repo_url:
            continue
        for h in r.get("hooks", []):
            if h.get("id") == hook_id:
                return h
    raise AssertionError(f"hook {hook_id!r} not found under {repo_url!r}")


def test_pre_commit_config_lists_core_hooks() -> None:
    data = yaml.safe_load(_PRE_COMMIT.read_text(encoding="utf-8"))
    repos = data["repos"]
    urls = {r["repo"] for r in repos if isinstance(r.get("repo"), str)}
    assert "https://github.com/psf/black" in urls
    assert "https://github.com/astral-sh/ruff-pre-commit" in urls

    locals_ = [r for r in repos if r.get("repo") == "local"]
    assert len(locals_) == 1
    hooks = locals_[0]["hooks"]
    ids = {h["id"] for h in hooks}
    assert "pyright" in ids
    assert "pytest-smoke" in ids
    assert "transaction-gate-staged" in ids
    assert "transaction-gate-commit-msg" in ids

    black_hook = _hook(repos, "https://github.com/psf/black", "black")
    assert "tests/test_eda.py" in " ".join(black_hook.get("args", []))

    ruff_hook = _hook(repos, "https://github.com/astral-sh/ruff-pre-commit", "ruff")
    joined = " ".join(ruff_hook.get("args", []))
    assert "test_eda.py" in joined
    assert "--fix" not in joined, "pre-commit ruff should match make lint (check-only, no --fix)"

    nb_repo = next(r for r in repos if r.get("repo") == "https://github.com/kynan/nbstripout")
    nb_hook = nb_repo["hooks"][0]
    files_pat = str(nb_hook.get("files", ""))
    assert "module_a_population_segmentation" in files_pat
    assert "reports" not in files_pat


def test_pre_commit_ruff_rev_tracks_poetry_lock() -> None:
    """Avoid drift: ruff-pre-commit rev major.minor should match poetry.lock ruff."""
    data = yaml.safe_load(_PRE_COMMIT.read_text(encoding="utf-8"))
    ruff_repo = next(
        r for r in data["repos"] if r.get("repo") == "https://github.com/astral-sh/ruff-pre-commit"
    )
    rev = str(ruff_repo["rev"]).lstrip("v")
    lock = (_REPO / "poetry.lock").read_text(encoding="utf-8")
    needle = 'name = "ruff"\nversion = "'
    assert needle in lock
    i = lock.index(needle) + len(needle)
    j = lock.index('"', i)
    lock_ver = lock[i:j]
    assert rev == lock_ver, f"pre-commit ruff rev {rev!r} != poetry.lock {lock_ver!r}"
