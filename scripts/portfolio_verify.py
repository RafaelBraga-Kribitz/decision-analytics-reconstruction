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
    "maintainer/evidence/",
    "maintainer/archive/",
)


def maintainer_path_allowed(path: str) -> bool:
    if path == "maintainer/pre_public_cleanup_manifest.md":
        return True
    return any(path.startswith(p) for p in MAINTAINER_ALLOWED_PREFIXES)


def main() -> int:
    proc = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    )
    files = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    bad: list[str] = []
    for f in files:
        if any(f.startswith(p) or f.startswith(p.lstrip("./")) for p in DENY_PREFIXES):
            bad.append(f)
            continue
        if f.startswith("maintainer/") and not maintainer_path_allowed(f):
            bad.append(f)
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
