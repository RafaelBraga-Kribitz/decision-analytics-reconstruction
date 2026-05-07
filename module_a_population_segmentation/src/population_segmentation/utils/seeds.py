"""Seed management and RNG factory.

All random operations in this project must use an explicitly seeded RNG
rather than global state. This module provides the canonical factory.
"""

from __future__ import annotations

import os
import random

import numpy as np


def get_seed() -> int:
    """Return the project random seed from environment or default 42."""
    raw = os.environ.get("RANDOM_SEED", "42")
    return int(raw)


def make_rng(seed: int | None = None) -> np.random.Generator:
    """Return a seeded numpy Generator.

    Args:
        seed: Explicit seed. If None, reads RANDOM_SEED env var (default 42).

    Returns:
        numpy.random.Generator — pass this explicitly through the call stack.
        Never store as global state.
    """
    effective_seed = seed if seed is not None else get_seed()
    return np.random.default_rng(effective_seed)


def seed_stdlib(seed: int | None = None) -> None:
    """Seed the Python stdlib ``random`` module explicitly.

    Call this once at the top of any entry-point that uses stdlib random.
    Do not rely on global state — call before the operations that need it.
    """
    effective_seed = seed if seed is not None else get_seed()
    random.seed(effective_seed)
