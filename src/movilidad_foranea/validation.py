"""Output data validation using pandera.

After a scraper builds its results DataFrame (in memory, right after scraping
and before export), these schemas check that the data has the expected shape and
sane values. Validation is pure logic (no browser, no network), so it is fully
unit-testable.

Design principle: distinguish two kinds of columns.

  * Code-generated / structural fields — always present and well-formed. A
    problem here is a real bug, so these are validated strictly (non-null, and
    with a format check where applicable): Origin General, Travel Date,
    Scraping Date, id.

  * Source-derived fields — scraped from the page, which may legitimately omit
    them. An empty value here is NOT a scraper error; it reflects the source, so
    these are allowed to be null: Origin, Destination, Departure Time, Arrival
    Time, Price (and the platform-specific extras).

strict=False also lets each platform add its own extra columns (Day Offset,
Bus Company, Duration, Seats Available, query_date, destination, ...).
"""

from __future__ import annotations

# pandera >= 0.20 recommends the pandas submodule; fall back for older versions.
try:
    import pandera.pandas as pa
except ImportError:  # pragma: no cover - depends on installed pandera version
    import pandera as pa

import pandas as pd

# Format/pattern for the code-generated trip id, e.g. AMAD_1a2b3c4d
# (ADO/OMB/CB/BB prefix + 8 hex characters).
_TRIP_ID_RE = r"^AM[A-Z]{2}_[0-9a-f]{8}$"


def _valid_date_check(fmt: str) -> pa.Check:
    """A pandera Check that passes only for values parseable as a date in `fmt`.

    Unlike a plain regex (which would accept an impossible date such as
    '2026-13-99'), this actually parses the value, so a well-formatted but
    non-existent date is rejected too. It also enforces the format, since a
    value in the wrong format fails to parse.
    """
    return pa.Check(
        lambda s: pd.to_datetime(s, format=fmt, errors="coerce").notna(),
        error=f"must be a valid date/time in format {fmt}",
    )


# --- Bus routes (mobility)
MOBILITY_SCHEMA = pa.DataFrameSchema(
    {
        # --- Structural fields: always present (and well-formed)
        "Origin General": pa.Column(str, nullable=False),
        "Travel Date": pa.Column(str, _valid_date_check("%Y-%m-%d"), nullable=False),
        "Scraping Date": pa.Column(
            str, _valid_date_check("%Y-%m-%d %H:%M:%S"), nullable=False
        ),
        # Uniqueness is guaranteed by the pipeline's de-duplication step
        # (drop_duplicates on id), so it is a transformation concern, not a
        # validation one. Validating it per batch would raise false alarms on
        # legitimate pre-dedup duplicates, so it is not checked here.
        "id": pa.Column(str, pa.Check.str_matches(_TRIP_ID_RE), nullable=False),
        # --- Source-derived fields: may legitimately be empty from the site
        "Origin": pa.Column(str, nullable=True),
        "Destination": pa.Column(str, nullable=True),
        "Departure Time": pa.Column(str, nullable=True),
        "Arrival Time": pa.Column(str, nullable=True),
    },
    strict=False,  # allow extra, platform-specific columns
    coerce=True,  # coerce values to the declared dtype where possible
)


# --- Hotels (accommodation / Booking) ---------------------------------------
ACCOMMODATION_SCHEMA = pa.DataFrameSchema(
    {
        # --- Structural fields ---
        # id comes from the Booking JSON (int or str); always present.
        # (Uniqueness is handled by the pipeline's de-duplication, as above.)
        "id": pa.Column(nullable=False),
        "checkIn": pa.Column(nullable=False),
        "checkOut": pa.Column(nullable=False),
        # --- Source-derived fields ---
        "pageName": pa.Column(str, nullable=True),
        "address": pa.Column(str, nullable=True),
        "countryCode": pa.Column(str, nullable=True),
        # Coordinates may be missing for a given property (a source gap), but any
        # value that IS present must be geographically valid. With nullable=True,
        # the range check applies only to non-null values, so a rare missing
        # coordinate passes while a corrupt one (e.g. latitude 200) fails.
        "latitude": pa.Column(
            float, pa.Check.in_range(-90.0, 90.0), nullable=True, coerce=True
        ),
        "longitude": pa.Column(
            float, pa.Check.in_range(-180.0, 180.0), nullable=True, coerce=True
        ),
    },
    strict=False,
    coerce=True,
)


def validate_mobility(df: pd.DataFrame) -> pd.DataFrame:
    """Validate a bus-route DataFrame against MOBILITY_SCHEMA.

    Returns the validated DataFrame. Raises pandera.errors.SchemaErrors
    (lazy=True collects every problem, not just the first one) if validation
    fails.
    """
    return MOBILITY_SCHEMA.validate(df, lazy=True)


def validate_accommodation(df: pd.DataFrame) -> pd.DataFrame:
    """Validate a Booking DataFrame against ACCOMMODATION_SCHEMA.

    Returns the validated DataFrame. Raises pandera.errors.SchemaErrors if
    validation fails.
    """
    return ACCOMMODATION_SCHEMA.validate(df, lazy=True)
