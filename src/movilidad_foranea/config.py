"""Loading and validation of the configuration for an extraction run.

This module is the bridge between the config.yaml file (edited by the user)
and the rest of the package (which receives already-validated Python objects).
No other part of the package needs to know the configuration came from YAML.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml  # provided by the pyyaml package


@dataclass
class MobilityConfig:
    """Parameters for the bus-route extraction."""

    start_date: date  # first travel date to query
    n_days: int = 7  # number of consecutive days to query
    headless: bool = False  # True = run Chrome without a visible window
    routes: list[tuple[str, str]] = field(
        default_factory=list
    )  # (origin, destination) pairs


@dataclass
class AccommodationConfig:
    """Parameters for the hotel extraction (Booking)."""

    checkin_date: date  # check-in date
    stay_nights: int = 5  # length of stay, in nights
    headless: bool = False
    cities: list[str] = field(default_factory=list)  # cities to query


@dataclass
class Config:
    """Full configuration: groups everything defined in a config.yaml."""

    output_dir: Path
    mobility: MobilityConfig
    accommodation: AccommodationConfig


def load_config(path: str | Path) -> Config:
    """Read a config.yaml file and turn it into a Config object.

    'date.fromisoformat' converts the text "2026-11-01" into a real Python
    date, so a mistyped date fails here, up front, instead of halfway through
    the extraction.
    """
    path = Path(path)
    with path.open("r", encoding="utf-8") as config_file:
        data = yaml.safe_load(
            config_file
        )  # safe_load reads data only; it never executes code

    mobility_raw = data.get("mobility", {})
    accommodation_raw = data.get("accommodation", {})

    mobility = MobilityConfig(
        start_date=date.fromisoformat(mobility_raw["start_date"]),
        n_days=mobility_raw.get("n_days", 7),
        headless=mobility_raw.get("headless", False),
        # each route in the YAML is a list [origin, destination]; convert it
        # to a tuple
        routes=[tuple(pair) for pair in mobility_raw.get("routes", [])],
    )

    accommodation = AccommodationConfig(
        checkin_date=date.fromisoformat(accommodation_raw["checkin_date"]),
        stay_nights=accommodation_raw.get("stay_nights", 5),
        headless=accommodation_raw.get("headless", False),
        cities=accommodation_raw.get("cities", []),
    )

    return Config(
        output_dir=Path(data["output_dir"]),
        mobility=mobility,
        accommodation=accommodation,
    )
