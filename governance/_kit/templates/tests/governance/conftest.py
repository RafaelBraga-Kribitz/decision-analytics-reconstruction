"""Make the governance test directory importable as a package shim.

This lets `from _ratchet import REPO_ROOT, ratchet` resolve in test_f*.py files
without manipulating sys.path in every test.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
