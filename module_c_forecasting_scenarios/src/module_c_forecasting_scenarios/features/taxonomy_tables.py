"""Canonical pollster_id and bias_family tags for synthetic / fixture rows."""

from __future__ import annotations

from collections.abc import Callable

POLLSTER_BIAS_FAMILY: dict[str, str] = {
    "capli": "capli",
    "capli_first": "capli",
    "ati_snead": "ati_snead",
    "ica": "ica",
    "grau": "grau",
    "ecodat": "default",
    "market": "default",
    "prologo": "default",
    "exit_consortium": "default",
}


def _match_capli(d: str) -> bool:
    return "capli" in d or "first análisis" in d or "first analisis" in d


def _match_ati_snead(d: str) -> bool:
    return "ati" in d and "snead" in d


def _match_ica(d: str) -> bool:
    return "ica" in d or "taka" in d


def _match_market(d: str) -> bool:
    return "market" in d or "república" in d or "republica" in d


def _match_prologo(d: str) -> bool:
    return "prologo" in d or "pro logo" in d


_POLLSTER_MATCHERS: tuple[tuple[Callable[[str], bool], str], ...] = (
    (_match_capli, "capli"),
    (_match_ati_snead, "ati_snead"),
    (_match_ica, "ica"),
    (lambda d: "grau" in d, "grau"),
    (lambda d: "ecodat" in d, "ecodat"),
    (_match_market, "market"),
    (_match_prologo, "prologo"),
    (lambda d: "exit" in d, "exit_consortium"),
)


def normalize_pollster_id(display: str) -> tuple[str, str]:
    d = display.lower().strip()
    for predicate, pollster_id in _POLLSTER_MATCHERS:
        if predicate(d):
            return (pollster_id, POLLSTER_BIAS_FAMILY[pollster_id])
    slug = "_".join(ch for ch in d if ch.isalnum() or ch == " ").replace(" ", "_")[:48]
    return (slug or "unknown", "default")
