"""Tests for the shared travel-date helper.

These tests are pure logic: no browser, no network, so they
are safe to run in continuous integration (CI).
"""

from datetime import date

from movilidad_foranea.mobility._dates import build_travel_dates


def test_returns_requested_number_of_dates():
    """n_days=3 should yield exactly three dates."""
    result = build_travel_dates(date(2026, 11, 1), n_days=3)
    assert len(result) == 3


def test_dates_are_consecutive_starting_at_start():
    """The dates should be consecutive, beginning at `start`."""
    result = build_travel_dates(date(2026, 11, 1), n_days=3)
    assert result == [date(2026, 11, 1), date(2026, 11, 2), date(2026, 11, 3)]


def test_crosses_month_boundary_correctly():
    """The helper should roll over into the next month without error."""
    result = build_travel_dates(date(2026, 1, 31), n_days=2)
    assert result == [date(2026, 1, 31), date(2026, 2, 1)]


def test_zero_days_yields_empty_list():
    """n_days=0 is an edge case that should produce no dates, not an error."""
    assert build_travel_dates(date(2026, 11, 1), n_days=0) == []
