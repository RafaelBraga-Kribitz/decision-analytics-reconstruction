"""Synthesize a dirty Module B input batch.

Simulates the realistic ingestion environment a 2018 PY campaign team would
face: mixed locales (es-PY, es-AR, en-US), inconsistent currency markers
(``USD``, ``US$``, ``$``, ``Gs.``, ``₲``, ``PYG``), thousands-vs-decimal
separator collisions, accent stripping, free-text channel names, and stray
NULL/sentinel rows.

Outputs three CSVs to ``out_dir``:

* ``budget_lines_raw.csv`` — vendor invoice line items (mixed currencies).
* ``volunteer_logs_raw.csv`` — per-event volunteer activity logs.
* ``media_buy_sheet_raw.csv`` — broadcast media buy sheet.

The companion :mod:`module_b_resource_allocation.data.cleaner` ingests these
files and produces the harmonized layer consumed by every downstream Module B
feature builder and the LP/MILP allocator.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from module_b_resource_allocation.constants import (
    CHANNEL_TYPES,
    WEEK_COUNT,
    WEEK_LABELS,
)

# Free-text variants the field team used in the wild — the cleaner must
# canonicalize each to a CHANNEL_NAMES value.
CHANNEL_ALIASES: dict[str, str] = {
    "WhatsApp Chatbot": "whatsapp_chatbot",
    "whatsapp_bot": "whatsapp_chatbot",
    "WPP": "whatsapp_chatbot",
    "WhatsApp": "whatsapp_chatbot",
    "Messenger bot": "messenger_chatbot",
    "MSG bot": "messenger_chatbot",
    "FB Ads": "facebook_ads",
    "Facebook Ads": "facebook_ads",
    "Facebook ads": "facebook_ads",
    "SMS": "sms",
    "sms blast": "sms",
    "Email": "email",
    "email blast": "email",
    "TV Spot": "tv_spots",
    "tv": "tv_spots",
    "tv spots": "tv_spots",
    "FTA TV": "tv_spots",
    "Radio": "radio_spots",
    "radio_ad": "radio_spots",
    "radio spots": "radio_spots",
    "Cuña Radio": "radio_spots",
    "Cuna Radio": "radio_spots",
    "Vallas": "billboards",
    "valla": "billboards",
    "billboard": "billboards",
    "BillBoard": "billboards",
    "Mitin": "rallies_events",
    "rally": "rallies_events",
    "rallies": "rallies_events",
    "Acto Politico": "rallies_events",
    "Puerta a puerta": "canvassing",
    "Canvas": "canvassing",
    "Door-to-door": "canvassing",
    "Auto parlante": "sound_cars",
    "sound car": "sound_cars",
    "Perifoneo": "sound_cars",
}

DEPARTMENT_ALIASES: dict[str, str] = {
    "Ñeembucú": "Neembucu",
    "Neembucu": "Neembucu",
    "NEEMBUCU": "Neembucu",
    "Concepción": "Concepcion",
    "Itapúa": "Itapua",
    "Itapua": "Itapua",
    "Guairá": "Guaira",
    "Caazapá": "Caazapa",
    "Caaguazú": "Caaguazu",
    "Asunción": "Asuncion",
    "Asuncion": "Asuncion",
    "Presidente Hayes": "Presidente Hayes",
    "Pte Hayes": "Presidente Hayes",
    "Boquerón": "Boqueron",
    "Boqueron": "Boqueron",
    "Alto Paraná": "Alto Parana",
    "Alto Parana": "Alto Parana",
    "Alto Paraguay": "Alto Paraguay",
    "San Pedro": "San Pedro",
    "San pedro": "San Pedro",
    "Cordillera": "Cordillera",
    "Misiones": "Misiones",
    "Paraguari": "Paraguari",
    "Paraguarí": "Paraguari",
    "Central": "Central",
    "Amambay": "Amambay",
    "Canindeyu": "Canindeyu",
    "Canindeyú": "Canindeyu",
}


@dataclass(frozen=True)
class DirtyGenConfig:
    n_budget_rows: int = 2_500
    n_volunteer_rows: int = 3_500
    n_media_rows: int = 1_200
    seed: int = 20180422
    null_rate: float = 0.03
    duplicate_rate: float = 0.02
    locale_swap_rate: float = 0.25
    currency_swap_rate: float = 0.35


def _maybe_swap_locale(value: float, rng: np.random.Generator, rate: float) -> str:
    """Render a numeric value as either '1,234.56' (en) or '1.234,56' (es)."""
    if rng.random() < rate:
        s = f"{value:,.2f}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{value:,.2f}"


def _maybe_with_noise(text: str, rng: np.random.Generator, p: float) -> str:
    if rng.random() < p:
        if rng.random() < 0.5:
            return f"  {text}  "
        return text.upper()
    return text


def _pick(items: Iterable, rng: np.random.Generator):
    seq = list(items)
    idx = int(rng.integers(0, len(seq)))
    return seq[idx]


def generate_budget_lines(cfg: DirtyGenConfig, out_path: Path, rng: np.random.Generator) -> Path:
    """Synthesize a noisy ``budget_lines_raw.csv`` fixture for cleaner tests.

    Args:
        cfg: Row counts, corruption rates, and RNG controls.
        out_path: Destination CSV path (parent directories must exist or be created by caller).
        rng: Seeded NumPy generator for deterministic dirty data.

    Returns:
        ``out_path`` after the CSV is written.

    Raises:
        OSError: If ``out_path`` cannot be opened for writing.

    Example:
        From ``generate_all``::

            generate_budget_lines(cfg, out_dir / "budget_lines_raw.csv", rng)
    """
    channel_alias_keys = list(CHANNEL_ALIASES.keys())
    dept_alias_keys = list(DEPARTMENT_ALIASES.keys())
    currency_pairs = [
        ("USD", 1.0),
        ("US$", 1.0),
        ("$", 1.0),
        ("PYG", 1.0),
        ("Gs.", 1.0),
        ("₲", 1.0),
    ]
    rows = []
    for i in range(cfg.n_budget_rows):
        channel_alias = _pick(channel_alias_keys, rng)
        canonical_channel = CHANNEL_ALIASES[channel_alias]
        # Choose currency: bilateral/digital channels lean USD, in-person lean PYG.
        ch_type = CHANNEL_TYPES[canonical_channel]
        if ch_type in {"bilateral", "broadcast"} and rng.random() < 0.55:
            currency_pool = [c for c in currency_pairs if c[0] in {"USD", "US$", "$"}]
        else:
            currency_pool = [c for c in currency_pairs if c[0] in {"PYG", "Gs.", "₲"}]
        currency, _ = currency_pool[int(rng.integers(0, len(currency_pool)))]
        if rng.random() < cfg.currency_swap_rate:
            currency, _ = currency_pairs[int(rng.integers(0, len(currency_pairs)))]

        amount_native = float(rng.gamma(2.5, 3500.0)) + 200.0
        if currency in {"PYG", "Gs.", "₲"}:
            amount_native *= 5600.0

        amount_str = _maybe_swap_locale(amount_native, rng, cfg.locale_swap_rate)
        dept_alias = _pick(dept_alias_keys, rng)
        week_label = WEEK_LABELS[int(rng.integers(0, WEEK_COUNT))]

        row = {
            "row_id": f"BUD-{i:05d}",
            "vendor": f"V{int(rng.integers(0, 80)):03d}",
            "channel_text": _maybe_with_noise(channel_alias, rng, 0.15),
            "department_text": _maybe_with_noise(dept_alias, rng, 0.10),
            "week_label": week_label,
            "currency": currency,
            "amount_text": amount_str,
            "fx_tier_hint": "REF" if rng.random() < 0.55 else "RETAIL",
            "notes": "",
        }
        rows.append(row)

    # Inject NULLs and duplicates.
    for r in rows:
        if rng.random() < cfg.null_rate:
            field = _pick(("channel_text", "department_text", "amount_text"), rng)
            r[field] = ""
        if rng.random() < cfg.null_rate / 2:
            r["amount_text"] = "NULL"

    dup_targets = rng.choice(len(rows), size=int(len(rows) * cfg.duplicate_rate), replace=False)
    rows_with_dups = rows + [dict(rows[i]) for i in dup_targets]

    fieldnames = list(rows[0].keys())
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_with_dups)
    return out_path


def generate_volunteer_logs(cfg: DirtyGenConfig, out_path: Path, rng: np.random.Generator) -> Path:
    """Synthesize ``volunteer_logs_raw.csv`` with field-noise and locale quirks.

    Args:
        cfg: Row counts and corruption knobs.
        out_path: Destination CSV path.
        rng: Seeded NumPy generator.

    Returns:
        ``out_path`` after writing.

    Raises:
        OSError: If ``out_path`` cannot be written.

    Example:
        ``generate_volunteer_logs(cfg, out_dir / \"volunteer_logs_raw.csv\", rng)``.
    """
    dept_alias_keys = list(DEPARTMENT_ALIASES.keys())
    canvas_channels = ("Puerta a puerta", "Canvas", "Door-to-door", "Mitin", "Auto parlante")

    rows = []
    for i in range(cfg.n_volunteer_rows):
        dept_alias = _pick(dept_alias_keys, rng)
        ch_alias = _pick(canvas_channels, rng)
        contacts = int(rng.poisson(40.0)) + 5
        hours = float(rng.gamma(2.0, 1.5)) + 0.5
        cost = contacts * float(rng.uniform(450.0, 950.0))  # PYG
        cost_str = _maybe_swap_locale(cost, rng, cfg.locale_swap_rate)
        row = {
            "row_id": f"VOL-{i:05d}",
            "team_lead": f"L{int(rng.integers(0, 40)):03d}",
            "channel_text": _maybe_with_noise(ch_alias, rng, 0.10),
            "department_text": _maybe_with_noise(dept_alias, rng, 0.10),
            "week_label": WEEK_LABELS[int(rng.integers(0, WEEK_COUNT))],
            "contacts_text": str(contacts) if rng.random() < 0.8 else f"{contacts:,d}",
            "hours_text": f"{hours:.1f}".replace(".", "," if rng.random() < 0.4 else "."),
            "cost_pyg_text": cost_str,
            "notes": "",
        }
        if rng.random() < cfg.null_rate:
            row["contacts_text"] = ""
        rows.append(row)

    fieldnames = list(rows[0].keys())
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return out_path


def generate_media_buy_sheet(cfg: DirtyGenConfig, out_path: Path, rng: np.random.Generator) -> Path:
    """Synthesize ``media_buy_sheet_raw.csv`` with mixed currencies and aliases.

    Args:
        cfg: Row counts and corruption knobs.
        out_path: Destination CSV path.
        rng: Seeded NumPy generator.

    Returns:
        ``out_path`` after writing.

    Raises:
        OSError: If ``out_path`` cannot be written.

    Example:
        ``generate_media_buy_sheet(cfg, out_dir / \"media_buy_sheet_raw.csv\", rng)``.
    """
    dept_alias_keys = list(DEPARTMENT_ALIASES.keys())
    broadcast_channels = ("TV Spot", "FTA TV", "Radio", "Cuña Radio", "Vallas", "FB Ads")

    rows = []
    for i in range(cfg.n_media_rows):
        dept_alias = _pick(dept_alias_keys, rng)
        ch_alias = _pick(broadcast_channels, rng)
        impressions = int(rng.gamma(2.0, 8000.0)) + 1000
        # Vendors quote in mixed currencies.
        if rng.random() < 0.6:
            currency = "USD"
            amount_native = float(rng.gamma(2.0, 1800.0)) + 100.0
        else:
            currency = "Gs."
            amount_native = float(rng.gamma(2.0, 1800.0) * 5600.0) + 500_000.0
        row = {
            "row_id": f"MED-{i:05d}",
            "vendor": f"V{int(rng.integers(0, 25)):03d}",
            "channel_text": _maybe_with_noise(ch_alias, rng, 0.20),
            "department_text": _maybe_with_noise(dept_alias, rng, 0.10),
            "week_label": WEEK_LABELS[int(rng.integers(0, WEEK_COUNT))],
            "impressions_text": _maybe_swap_locale(float(impressions), rng, cfg.locale_swap_rate),
            "currency": currency,
            "amount_text": _maybe_swap_locale(amount_native, rng, cfg.locale_swap_rate),
            "fx_tier_hint": "REF" if rng.random() < 0.6 else "RETAIL",
        }
        if rng.random() < cfg.null_rate:
            row["impressions_text"] = ""
        rows.append(row)

    fieldnames = list(rows[0].keys())
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return out_path


def generate_all(cfg: DirtyGenConfig, out_dir: Path) -> dict[str, Path]:
    """Generate the full trio of dirty CSV fixtures under ``out_dir``.

    Args:
        cfg: Shared configuration for row counts and corruption rates.
        out_dir: Output directory (created if missing).

    Returns:
        Dict mapping logical names to written CSV paths.

    Raises:
        OSError: If any CSV cannot be written.

    Example:
        ``generate_all(cfg, Path(\"data/raw/module_b_synth\"))`` before cleaner tests.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(cfg.seed)
    return {
        "budget_lines_raw": generate_budget_lines(cfg, out_dir / "budget_lines_raw.csv", rng),
        "volunteer_logs_raw": generate_volunteer_logs(cfg, out_dir / "volunteer_logs_raw.csv", rng),
        "media_buy_sheet_raw": generate_media_buy_sheet(
            cfg, out_dir / "media_buy_sheet_raw.csv", rng
        ),
    }
