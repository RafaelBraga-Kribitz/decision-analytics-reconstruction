"""Canonical pollster_id and bias_family tags for synthetic / fixture rows."""

from __future__ import annotations

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


def normalize_pollster_id(display: str) -> tuple[str, str]:
    d = display.lower().strip()
    if "capli" in d or "first análisis" in d or "first analisis" in d:
        return ("capli", POLLSTER_BIAS_FAMILY["capli"])
    if "ati" in d and "snead" in d:
        return ("ati_snead", POLLSTER_BIAS_FAMILY["ati_snead"])
    if "ica" in d or "taka" in d:
        return ("ica", POLLSTER_BIAS_FAMILY["ica"])
    if "grau" in d:
        return ("grau", POLLSTER_BIAS_FAMILY["grau"])
    if "ecodat" in d:
        return ("ecodat", POLLSTER_BIAS_FAMILY["ecodat"])
    if "market" in d or "república" in d or "republica" in d:
        return ("market", POLLSTER_BIAS_FAMILY["market"])
    if "prologo" in d or "pro logo" in d:
        return ("prologo", POLLSTER_BIAS_FAMILY["prologo"])
    if "exit" in d:
        return ("exit_consortium", POLLSTER_BIAS_FAMILY["exit_consortium"])
    slug = "_".join(ch for ch in d if ch.isalnum() or ch == " ").replace(" ", "_")[:48]
    return (slug or "unknown", "default")
