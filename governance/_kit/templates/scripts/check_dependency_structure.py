"""Verify module dependency rules defined in .importlinter are not violated.

If .importlinter does not exist, reports a [GAP] — file F-DEPENDENCY-VIOLATION
and define your contracts before this check can enforce anything.

Gate: F-DEPENDENCY-VIOLATION (dependency_violation category)

Run with --baseline to print setup instructions for .importlinter without gating.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

IMPORTLINTER_CFG = REPO_ROOT / ".importlinter"

_SETUP_HINT = """
To define dependency contracts, create .importlinter at the repo root.
Example (Clean Architecture — domain never imports infrastructure):

  [importlinter]
  root_packages =
      src

  [importlinter:contract:domain-independence]
  name = Domain layer must not import infrastructure
  type = forbidden
  source_modules =
      src.domain
  forbidden_modules =
      src.infrastructure
      src.adapters

Then run: pip install import-linter && lint-imports
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", action="store_true")
    args = parser.parse_args()

    if args.baseline:
        if IMPORTLINTER_CFG.exists():
            print("[BASELINE] check_dependency_structure.py: .importlinter found — run lint-imports to see current violations")
        else:
            print("[BASELINE] check_dependency_structure.py: .importlinter not found")
            print(_SETUP_HINT)
        return 0

    if not IMPORTLINTER_CFG.exists():
        return gate(
            "F-DEPENDENCY-VIOLATION", "check_dependency_structure.py", False,
            ".importlinter not found — no dependency contracts defined yet",
        )

    try:
        result = subprocess.run(
            ["lint-imports"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        print("[SKIP] check_dependency_structure.py: import-linter not installed (pip install import-linter)")
        return 0

    fixed = result.returncode == 0
    output_lines = (result.stdout + result.stderr).strip().splitlines()
    gap = output_lines[-1] if output_lines and not fixed else ""
    return gate(
        "F-DEPENDENCY-VIOLATION", "check_dependency_structure.py", fixed,
        f"lint-imports failed: {gap}",
    )


if __name__ == "__main__":
    sys.exit(main())
