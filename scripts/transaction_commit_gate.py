#!/usr/bin/env python3
"""Deterministic transaction commit gate: reconcile staged files with unit lock (plan SSOT).

Exit codes: 0 pass, 1 fail (reconcile/revert), 2 usage/configuration error.

If the unit lock file is missing, checks are skipped (exit 0) so human commits
without harness state are not blocked.

See `.cursor/rules/10-transaction-boundaries.mdc` and `.cursor/runtime/README.md`.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
_DEFAULT_LOCK = _REPO / ".cursor" / "runtime" / "current_unit.json"

_CONVENTIONAL_SUBJECT = re.compile(
    r"^(feat|fix|docs|refactor|test|build|ci|chore|perf|style)(\([^)]+\))?: .+"
)


def _norm_relpath(p: str) -> str:
    """Normalize to POSIX-style path relative to repo root."""
    x = p.strip().replace("\\", "/").lstrip("./")
    return x


def _load_lock(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"transaction_commit_gate: invalid lock JSON: {e}", file=sys.stderr)
        return None
    if not isinstance(data, dict):
        print("transaction_commit_gate: lock root must be an object", file=sys.stderr)
        return None
    return data


def _git_staged_names(cwd: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(cwd), "diff", "--cached", "--name-only", "-z"],
        check=False,
        capture_output=True,
    )
    if proc.returncode != 0:
        print(proc.stderr.decode("utf-8", errors="replace"), file=sys.stderr)
        return []
    raw = proc.stdout.split(b"\0")
    out: list[str] = []
    for b in raw:
        if not b:
            continue
        out.append(b.decode("utf-8", errors="replace"))
    return out


def _git_current_branch(cwd: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(cwd), "rev-parse", "--abbrev-ref", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return ""
    return (proc.stdout or "").strip()


def _path_matches_allowed(relpath: str, allowed_patterns: list[str]) -> bool:
    """Return True if path matches at least one allowed pattern (prefix or glob)."""
    rp = _norm_relpath(relpath)
    for pat in allowed_patterns:
        p = pat.strip().replace("\\", "/")
        if not p:
            continue
        if p.endswith("/"):
            if rp == p.rstrip("/") or rp.startswith(p):
                return True
            continue
        if any(ch in p for ch in "*?[]"):
            if fnmatch.fnmatch(rp, p):
                return True
            continue
        if rp == p or rp.startswith(p + "/"):
            return True
    return False


def validate_staged(
    lock: dict[str, Any],
    staged: list[str],
    *,
    branch: str,
    strict_budget: bool,
    allow_large: bool,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    norm_staged = [_norm_relpath(x) for x in staged if x.strip()]
    if not norm_staged:
        # e.g. `pre-commit run --all-files` with an empty index — nothing to validate
        return True, []

    status = str(lock.get("status", ""))
    if status == "closed":
        errors.append("unit lock status is 'closed'; open a new unit before committing")
    elif status not in ("declared", "in_progress"):
        errors.append(f"unit lock status must be 'declared' or 'in_progress', got {status!r}")

    unit_id = str(lock.get("unit_id", "")).strip()
    if not unit_id:
        errors.append("lock missing unit_id")

    impact_raw = lock.get("unit_impact_set", [])
    if not isinstance(impact_raw, list):
        errors.append("unit_impact_set must be a JSON array")
        impact: set[str] = set()
    else:
        impact = {_norm_relpath(str(x)) for x in impact_raw if str(x).strip()}

    if not errors and not impact:
        errors.append("unit_impact_set must not be empty when enforcing transactions")

    allowed_raw = lock.get("allowed_paths", [])
    if not isinstance(allowed_raw, list):
        errors.append("allowed_paths must be a JSON array")
        allowed: list[str] = []
    else:
        allowed = [str(x) for x in allowed_raw]

    if branch in ("main", "master"):
        errors.append(f"commits on {branch!r} are blocked under transaction rules; use a branch")

    if impact and norm_staged:
        for s in norm_staged:
            if s not in impact:
                errors.append(f"staged file {s!r} is not in unit_impact_set")

    if allowed and norm_staged and not errors:
        for s in norm_staged:
            if not _path_matches_allowed(s, allowed):
                errors.append(f"staged file {s!r} does not match any allowed_paths pattern")

    budget_raw = lock.get("diff_budget_max", 15)
    try:
        budget = int(budget_raw)
    except (TypeError, ValueError):
        budget = 15

    if norm_staged and budget > 0 and len(norm_staged) > budget:
        msg = (
            f"staged file count {len(norm_staged)} exceeds diff_budget_max {budget}; "
            "expand unit_impact_set/plan or set TRANSACTION_ALLOW_LARGE=1"
        )
        if strict_budget or not allow_large:
            errors.append(msg)
        else:
            print(f"transaction_commit_gate: WARNING: {msg}", file=sys.stderr)

    return (len(errors) == 0, errors)


def validate_message(
    lock: dict[str, Any],
    message: str,
    *,
    require_conventional: bool,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    unit_id = str(lock.get("unit_id", "")).strip()
    if not unit_id:
        errors.append("lock missing unit_id")
        return False, errors

    if unit_id not in message:
        errors.append(f"commit message must contain UNIT_ID string {unit_id!r}")

    first_line = (message.splitlines() or [""])[0].strip()
    if require_conventional and first_line and not _CONVENTIONAL_SUBJECT.match(first_line):
        errors.append(
            "first line should follow Conventional Commits, e.g. feat(scope): subject",
        )

    return (len(errors) == 0, errors)


def main() -> int:
    parser = argparse.ArgumentParser(description="Transaction commit gate (plan reconciliation).")
    parser.add_argument(
        "--unit-lock",
        type=Path,
        default=_DEFAULT_LOCK,
        help="Path to current_unit.json",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=_REPO,
        help="Repository root (git -C)",
    )
    parser.add_argument(
        "--check-staged",
        action="store_true",
        help="Verify staged files vs lock (pre-commit stage).",
    )
    parser.add_argument(
        "--check-message",
        action="store_true",
        help="Verify COMMIT_MSG / file contains unit_id (commit-msg stage).",
    )
    parser.add_argument(
        "--commit-msg-file",
        type=Path,
        default=None,
        help="Path to file with commit message (Git hook / pre-commit commit-msg).",
    )
    parser.add_argument(
        "--no-conventional",
        action="store_true",
        help="Do not require Conventional Commits on first line.",
    )
    args, rest = parser.parse_known_args()
    # pre-commit commit-msg hooks append the message file path as an extra argument
    if args.check_message and args.commit_msg_file is None and rest:
        args.commit_msg_file = Path(rest[0])

    lock_path: Path = args.unit_lock
    if not lock_path.is_absolute():
        lock_path = (args.repo / lock_path).resolve()

    lock = _load_lock(lock_path)
    if lock is None:
        print(
            "transaction_commit_gate: no unit lock — skipping enforcement " f"({lock_path})",
            file=sys.stderr,
        )
        return 0

    repo: Path = args.repo.resolve()
    allow_large = os.environ.get("TRANSACTION_ALLOW_LARGE", "").strip() in ("1", "true", "yes")
    strict_budget = os.environ.get("TRANSACTION_STRICT_BUDGET", "").strip() in ("1", "true", "yes")

    if args.check_staged:
        staged = _git_staged_names(repo)
        branch = _git_current_branch(repo)
        ok, errors = validate_staged(
            lock,
            staged,
            branch=branch,
            strict_budget=strict_budget,
            allow_large=allow_large,
        )
        if not ok:
            for e in errors:
                print(f"transaction_commit_gate: {e}", file=sys.stderr)
            return 1
    if args.check_message:
        if args.commit_msg_file is not None:
            msg_path: Path = args.commit_msg_file
            if not msg_path.is_file():
                print(
                    f"transaction_commit_gate: missing commit message file {msg_path}",
                    file=sys.stderr,
                )
                return 1
            message = msg_path.read_text(encoding="utf-8", errors="replace")
        else:
            message = os.environ.get("TRANSACTION_COMMIT_MSG", "")
        ok_m, m_errors = validate_message(
            lock,
            message,
            require_conventional=not args.no_conventional,
        )
        if not ok_m:
            for e in m_errors:
                print(f"transaction_commit_gate: {e}", file=sys.stderr)
            return 1

    if not args.check_staged and not args.check_message:
        print(
            "transaction_commit_gate: specify --check-staged and/or --check-message",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
