#!/usr/bin/env python3
"""Verify tracked paths that must not ship in a public portfolio ZIP."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Tracked files under these prefixes should not exist in a portfolio-clean remote.
# Note: this repository may intentionally track a minimal `.cursor/` subset for harness
# parity — that is governed by `maintainer/pre_public_cleanup_manifest.md`, not this script.
DENY_PREFIXES: tuple[str, ...] = ("graphify-out/",)

# Other paths under maintainer/ must not be tracked publicly (see manifest M10/M12).
MAINTAINER_ALLOWED_PREFIXES: tuple[str, ...] = (
    "maintainer/doc_debt/",
)


def maintainer_path_allowed(path: str) -> bool:
    return any(path.startswith(p) for p in MAINTAINER_ALLOWED_PREFIXES)


def _is_forbidden_path(path: str) -> bool:
    if any(path.startswith(p) or path.startswith(p.lstrip("./")) for p in DENY_PREFIXES):
        return True
    return path.startswith("maintainer/") and not maintainer_path_allowed(path)


def main() -> int:
    proc = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    )
    files = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    bad = [f for f in files if _is_forbidden_path(f)]
    if bad:
        print("portfolio-verify FAILED — forbidden tracked paths:")
        for b in bad[:200]:
            print(" ", b)
        if len(bad) > 200:
            print(f" ... and {len(bad) - 200} more")
        return 1
    print("portfolio-verify OK (no forbidden tracked prefixes in git index).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
