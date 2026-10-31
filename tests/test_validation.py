"""Tests for the output data-validation schemas.

Pure logic: these build small DataFrames in memory and check that valid data
passes, that genuinely corrupt data is rejected, and that legitimate source
gaps (empty values that come from the website, not from a scraper bug) are
allowed. No browser, no network.
"""

import numpy as np
import pandas as pd
import pytest
from pandera.errors import SchemaErrors

from movilidad_foranea.validation import validate_accommodation, validate_mobility


def _valid_mobility_df() -> pd.DataFrame:
    """A minimal, valid bus-route DataFrame with the common core columns."""
    return pd.DataFrame(
        {
            "Origin General": ["CDMX"],
            "Origin": ["CDMX Norte"],
            "Destination": ["Puebla"],
            "Departure Time": ["10:00"],
            "Arrival Time": ["12:00"],
            "Price": ["MXN 300"],
            "Travel Date": ["2026-11-01"],
            "Scraping Date": ["2026-10-29 10:00:00"],
            "id": ["AMAD_1a2b3c4d"],
        }
    )


def _valid_accommodation_df() -> pd.DataFrame:
    """A minimal, valid Booking DataFrame."""
    return pd.DataFrame(
        {
            "id": [4624045],
            "pageName": ["fairfield-cancun"],
            "address": ["Blvd Luis"],
            "countryCode": ["mx"],
            "longitude": [-86.8493],
            "latitude": [21.05105],
            "checkIn": ["2026-10-29"],
            "checkOut": ["2026-11-03"],
        }
    )


# --- Mobility: valid data


def test_valid_mobility_passes():
    validate_mobility(_valid_mobility_df())  # should not raise


def test_mobility_allows_extra_platform_columns():
    """ClickBus-style extra columns must not break validation (strict=False)."""
    df = _valid_mobility_df()
    df["Bus Company"] = ["ADO"]
    df["Seats Available"] = ["12"]
    validate_mobility(df)  # should not raise


def test_mobility_allows_empty_source_fields():
    """Empty source-derived fields (missing on the site) are legitimate."""
    df = _valid_mobility_df()
    df.loc[0, "Origin"] = np.nan  # missing terminal
    df.loc[0, "Departure Time"] = np.nan  # missing time
    validate_mobility(df)  # should not raise


# --- Mobility: corrupt / structural problems


def test_mobility_rejects_missing_structural_column():
    df = _valid_mobility_df().drop(columns=["Origin General"])
    with pytest.raises(SchemaErrors):
        validate_mobility(df)


def test_mobility_rejects_malformed_travel_date():
    df = _valid_mobility_df()
    df.loc[0, "Travel Date"] = "2026-13-99"  # impossible date
    with pytest.raises(SchemaErrors):
        validate_mobility(df)


def test_mobility_rejects_malformed_id():
    df = _valid_mobility_df()
    df.loc[0, "id"] = "XXX_nothex"  # wrong prefix/format
    with pytest.raises(SchemaErrors):
        validate_mobility(df)


# --- Accommodation: valid data


def test_valid_accommodation_passes():
    validate_accommodation(_valid_accommodation_df())  # should not raise


def test_accommodation_allows_missing_coordinate():
    """A rare missing coordinate is a source gap, not a corruption."""
    df = _valid_accommodation_df()
    df.loc[0, "latitude"] = np.nan
    validate_accommodation(df)  # should not raise


# --- Accommodation: corrupt values


def test_accommodation_rejects_out_of_range_latitude():
    df = _valid_accommodation_df()
    df.loc[0, "latitude"] = 200.0  # impossible latitude
    with pytest.raises(SchemaErrors):
        validate_accommodation(df)


def test_accommodation_rejects_out_of_range_longitude():
    df = _valid_accommodation_df()
    df.loc[0, "longitude"] = -500.0  # impossible longitude
    with pytest.raises(SchemaErrors):
        validate_accommodation(df)
