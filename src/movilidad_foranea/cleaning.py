"""Consistent handling of missing values across scrapers.

Scrapers historically recorded a missing field in several ways: an empty string
"", a whitespace-only string, or the sentinel "N/A". normalize_missing replaces
all of them with a true null (NaN), so downstream code and the validation
schemas see a single, unambiguous 'missing' marker instead of a mix.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def normalize_missing(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of `df` with missing values normalized to NaN.

    Replaces empty strings, whitespace-only strings and the legacy "N/A"
    sentinel with NaN. Numeric columns (e.g. latitude/longitude) are left
    untouched, because the string patterns never match numeric values.
    """
    # future.no_silent_downcasting keeps the (object) columns as object with
    # NaN instead of silently changing their dtype, and avoids a pandas
    # FutureWarning about that deprecated downcasting behavior.
    with pd.option_context("future.no_silent_downcasting", True):
        df = df.replace(r"^\s*$", np.nan, regex=True)  # "" or whitespace-only -> NaN
        df = df.replace("N/A", np.nan)  # legacy sentinel -> NaN
    return df
