"""Load dirty poll rows from CSV / Parquet."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_raw_polls_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["publication_date"] = pd.to_datetime(df["publication_date"]).dt.date
    return df
