"""
Shared date helpers for the mobility (bus) scrapers.
"""

from __future__ import annotations
from datetime import date, timedelta


def build_travel_dates(start: date, n_days: int) -> list[date]:
    """Return a list of `n_days` consecutive dates starting at `start`.

    Parameters
    ----------
    start:
        The first travel date to include.
    n_days:
        How many consecutive days to generate (including `start`).

    Returns
    -------
    list[date]
        Dates from `start` to `start + (n_days - 1)` days, in order.
        An `n_days` of 0 (or negative) yields an empty list.

    This is a pure function (no browser, no network), which is exactly what
    makes it straightforward to test.
    """
    return [start + timedelta(days=offset) for offset in range(n_days)]
