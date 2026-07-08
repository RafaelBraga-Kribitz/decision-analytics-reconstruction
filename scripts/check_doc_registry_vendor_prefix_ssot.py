#!/usr/bin/env python3
"""F-076 gate: registry builder and verifier share one VENDOR_PREFIXES source.

The two scripts drifted when ``.github/`` was added to the verifier's exclusion
list but not the builder's, so ``make verify`` failed on a registry the build
step itself had just written. Closure invariant: neither script defines its own
prefix tuple; both import the shared constant from ``scripts.doc_registry_schema``,
and a build → verify round-trip exits clean.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCRIPTS = (
    ROOT / "scripts" / "build_docs_registry.py",
    ROOT / "scripts" / "verify_doc_registry.py",
)
IMPORT_RE = re.compile(r"^from scripts\.doc_registry_schema import VENDOR_PREFIXES\b", re.MULTILINE)
LOCAL_DEF_RE = re.compile(r"^_?VENDOR_PREFIXES\s*=\s*\(", re.MULTILINE)


def main() -> int:
    problems: list[str] = []

    for path in SCRIPTS:
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT)
        if not IMPORT_RE.search(text):
            problems.append(f"{rel}: must import VENDOR_PREFIXES from scripts.doc_registry_schema")
        if LOCAL_DEF_RE.search(text):
            problems.append(f"{rel}: defines a local VENDOR_PREFIXES tuple (drift risk)")

    schema_text = (ROOT / "scripts" / "doc_registry_schema.py").read_text(encoding="utf-8")
    for prefix in ("governance/_kit/", ".github/"):
        if prefix not in schema_text:
            problems.append(f"scripts/doc_registry_schema.py: VENDOR_PREFIXES missing {prefix!r}")

    if not problems:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "verify_doc_registry.py")],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            problems.append(
                "verify_doc_registry.py failed after build:\n" + proc.stdout + proc.stderr
            )

    if problems:
        print("[FAIL] check_doc_registry_vendor_prefix_ssot:\n  " + "\n  ".join(problems))
        return 1
    print("[PASS] check_doc_registry_vendor_prefix_ssot: F-076 clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
