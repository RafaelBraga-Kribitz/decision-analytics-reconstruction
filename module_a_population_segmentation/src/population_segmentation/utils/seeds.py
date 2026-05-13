"""Seed management and RNG factory.

All random operations in this project must use an explicitly seeded RNG
rather than global state. This module provides the canonical factory.
"""

from __future__ import annotations

import os
import random

import numpy as np


def get_seed() -> int:
    """Return the project random seed from the environment or the default.

    Reads ``RANDOM_SEED`` when set; otherwise uses ``42`` so notebooks and
    pipelines stay reproducible without extra configuration.

    Args:
        None.

    Returns:
        Integer seed suitable for ``numpy.random.default_rng`` and stdlib
        ``random.seed``.

    Raises:
        ValueError: If ``RANDOM_SEED`` is set but cannot be parsed as an int.

    Example:
        >>> import os
        >>> os.environ.pop("RANDOM_SEED", None)
        >>> isinstance(get_seed(), int)
        True
    """
    raw = os.environ.get("RANDOM_SEED", "42")
    return int(raw)


def make_rng(seed: int | None = None) -> np.random.Generator:
    """Return a seeded NumPy ``Generator`` for explicit stochastic draws.

    Args:
        seed: Explicit seed. If ``None``, uses :func:`get_seed` (``RANDOM_SEED``
            env var, default ``42``).

    Returns:
        ``numpy.random.Generator`` — pass through the call stack; do not stash
        as a global singleton.

    Raises:
        ValueError: If ``seed`` or ``RANDOM_SEED`` cannot be parsed as an int.

    Example:
        >>> rng = make_rng(0)
        >>> rng.random() == rng.random()
        False
    """
    effective_seed = seed if seed is not None else get_seed()
    return np.random.default_rng(effective_seed)


def seed_stdlib(seed: int | None = None) -> None:
    """Seed the Python stdlib ``random`` module explicitly.

    Call once at the top of any entry-point that still uses ``random.*`` APIs
    so draws line up with the same integer seed used for NumPy.

    Args:
        seed: Explicit seed. If ``None``, uses :func:`get_seed`.

    Returns:
        ``None``.

    Raises:
        ValueError: If ``seed`` or ``RANDOM_SEED`` cannot be parsed as an int.

    Example:
        >>> seed_stdlib(123)
        >>> import random
        >>> isinstance(random.random(), float)
        True
    """
    effective_seed = seed if seed is not None else get_seed()
    random.seed(effective_seed)
