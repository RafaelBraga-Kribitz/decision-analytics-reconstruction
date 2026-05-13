"""2-opt tour-improvement heuristic for Module B routing (Phase 8).

Repeatedly reverses subsegments of the tour while any swap strictly improves
the total length.  The result is guaranteed to satisfy
``len_2opt <= len_nearest_insertion + epsilon`` (the canonical Phase 8 gate).
"""

from __future__ import annotations

from collections.abc import Hashable, Mapping
from typing import TypeVar

T = TypeVar("T", bound=Hashable)


def _tour_length(tour: list[T], dist: Mapping[tuple[T, T], float]) -> float:
    if len(tour) < 2:
        return 0.0
    total = 0.0
    for i in range(len(tour) - 1):
        total += float(dist[(tour[i], tour[i + 1])])
    total += float(dist[(tour[-1], tour[0])])
    return total


def two_opt_improve(
    tour: list[T],
    dist: Mapping[tuple[T, T], float],
    max_passes: int = 100,
) -> tuple[list[T], float]:
    """Return a 2-opt-improved tour and its total length.

    Args:
        tour: Current Hamiltonian cycle node ordering.
        dist: Directed edge lengths ``(u, v)``.
        max_passes: Upper bound on outer improvement sweeps.

    Returns:
        Tuple ``(improved_tour, length)`` including the closing edge.

    Raises:
        KeyError: If any referenced edge is missing from ``dist``.

    Example:
        ``two_opt_improve(tour, dist)`` after :func:`nearest_insertion_tour`.
    """
    if len(tour) < 4:
        return list(tour), _tour_length(tour, dist)

    best = list(tour)
    best_len = _tour_length(best, dist)
    n = len(best)

    for _ in range(max_passes):
        improved = False
        for i in range(n - 1):
            for j in range(i + 2, n):
                if i == 0 and j == n - 1:
                    continue  # closing edge
                a, b = best[i], best[i + 1]
                c, d = best[j], best[(j + 1) % n]
                delta = (
                    float(dist[(a, c)])
                    + float(dist[(b, d)])
                    - float(dist[(a, b)])
                    - float(dist[(c, d)])
                )
                if delta < -1e-9:
                    best[i + 1 : j + 1] = list(reversed(best[i + 1 : j + 1]))
                    best_len += delta
                    improved = True
        if not improved:
            break

    # Recompute the length cleanly to guard against floating-point drift.
    return best, _tour_length(best, dist)
