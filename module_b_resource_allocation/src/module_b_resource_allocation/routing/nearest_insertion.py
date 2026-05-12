"""Seeded nearest-insertion TSP heuristic for Module B routing (Phase 8).

Public API
----------

``nearest_insertion_tour(nodes, dist, seed) -> (tour, length)``
    Build a tour by:
    1. Starting from a seed-selected node.
    2. Repeatedly inserting the unvisited node that minimizes the increase
       in tour length at the best position.

The tour is a closed loop returned as a list of nodes in visit order; the
length is the total edge weight including the closing edge.
"""

from __future__ import annotations

import random
from collections.abc import Hashable, Iterable, Mapping
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


def nearest_insertion_tour(
    nodes: Iterable[T],
    dist: Mapping[tuple[T, T], float],
    seed: int = 42,
) -> tuple[list[T], float]:
    """Build a closed tour via nearest insertion.

    Parameters
    ----------
    nodes:
        Iterable of node ids.
    dist:
        Mapping ``(u, v) -> distance``.  Self-edges may be omitted.
    seed:
        Random seed; chooses the start node and tie-breaks insertions.

    Returns
    -------
    tuple[list[T], float]
        Closed tour (including return to start) and total edge length.

    Raises
    ------
    KeyError
        If ``dist`` lacks a required directed edge while expanding the tour.

    Examples
    --------
    ``nearest_insertion_tour(nodes, dist, seed=42)`` inside routing QA scripts.
    """
    node_list = list(nodes)
    if not node_list:
        return [], 0.0
    if len(node_list) == 1:
        return node_list, 0.0

    rng = random.Random(seed)
    start = node_list[rng.randrange(len(node_list))]
    tour: list[T] = [start]
    remaining = set(node_list) - {start}

    # Seed the tour with the two closest nodes.
    nearest = min(remaining, key=lambda n: dist[(start, n)])
    tour.append(nearest)
    remaining.discard(nearest)

    while remaining:
        # Pick the unvisited node closest to any node already in the tour.
        candidate = min(
            remaining,
            key=lambda n: min(dist[(t, n)] for t in tour),
        )
        # Insert candidate at the position minimizing the insertion cost.
        best_pos = 0
        best_delta = float("inf")
        for i in range(len(tour)):
            u = tour[i]
            v = tour[(i + 1) % len(tour)]
            delta = dist[(u, candidate)] + dist[(candidate, v)] - dist[(u, v)]
            if delta < best_delta:
                best_delta = delta
                best_pos = i + 1
        tour.insert(best_pos, candidate)
        remaining.discard(candidate)

    length = _tour_length(tour, dist)
    return tour, length
