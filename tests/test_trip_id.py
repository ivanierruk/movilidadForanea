"""Tests for the trip-ID hashing used by the bus scrapers.

generate_trip_id does not touch the browser), so it can be tested by instantiating a scraper without opening Chrome. ADOScraper is used as the representative case; the other bus scrapers share the same logic, differing only in the platform prefix.
"""

from movilidad_foranea.mobility.ado import ADOScraper

# A fixed set of trip attributes reused across tests.
TRIP = dict(
    origin="Ciudad de México, CDMX",
    destination="Puebla",
    departure_time="10:00",
    arrival_time="12:00",
    travel_date="2026-11-01",
    scraping_date="2026-10-29 10:00:00",
)


def _trip_id(scraper, **overrides):
    """Call generate_trip_id with TRIP, allowing individual fields to be overridden."""
    args = {**TRIP, **overrides}
    return scraper.generate_trip_id(
        args["origin"],
        args["destination"],
        args["departure_time"],
        args["arrival_time"],
        args["travel_date"],
        args["scraping_date"],
    )


def test_id_is_deterministic():
    """The same inputs must always produce the same id."""
    scraper = ADOScraper()  # does NOT open Chrome; __init__ only sets options
    assert _trip_id(scraper) == _trip_id(scraper)


def test_id_has_platform_prefix():
    """ADO ids must start with the 'AMAD_' prefix."""
    scraper = ADOScraper()
    assert _trip_id(scraper).startswith("AMAD_")


def test_id_changes_when_an_attribute_changes():
    """A different destination must yield a different id."""
    scraper = ADOScraper()
    assert _trip_id(scraper) != _trip_id(scraper, destination="Cancún")


def test_id_has_expected_length():
    """Prefix 'AMAD_' (5 chars) plus an 8-character hash = 13 characters."""
    scraper = ADOScraper()
    assert len(_trip_id(scraper)) == len("AMAD_") + 8
