"""Regenerate ``schema_contracts/CONFORMANCE_MATRIX.md`` from the contracts.

The matrix is a constraint x contract grid showing which declared constraint
keys the shared :mod:`contract_core` validator enforces for each contract. It is
built by the validator itself, so the artifact can never drift from what the
gate actually does — a test (``tests/test_conformance_matrix.py``) fails if the
committed file is stale.

Usage::

    poetry run python scripts/generate_conformance_matrix.py        # write
    poetry run python scripts/generate_conformance_matrix.py --check # verify only
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from contract_core import build_conformance_matrix, load_contract_files

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_CONTRACTS_DIR = REPO_ROOT / "schema_contracts"
MATRIX_PATH = SCHEMA_CONTRACTS_DIR / "CONFORMANCE_MATRIX.md"


def render() -> str:
    """Return the Markdown conformance matrix for all committed contracts."""
    contracts = load_contract_files(SCHEMA_CONTRACTS_DIR)
    return build_conformance_matrix(contracts)


def main(argv: list[str] | None = None) -> int:
    """Write (or, with ``--check``, verify) the conformance matrix artifact."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if the committed matrix is out of date instead of writing it.",
    )
    args = parser.parse_args(argv)
    rendered = render()
    if args.check:
        current = MATRIX_PATH.read_text(encoding="utf-8") if MATRIX_PATH.exists() else ""
        if current != rendered:
            print("[FAIL] CONFORMANCE_MATRIX.md is stale; run generate_conformance_matrix.py")
            return 1
        print("[PASS] CONFORMANCE_MATRIX.md is up to date")
        return 0
    MATRIX_PATH.write_text(rendered, encoding="utf-8")
    print(f"[PASS] wrote {MATRIX_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
