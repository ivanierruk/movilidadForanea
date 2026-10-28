"""Tests for loading and validating the YAML configuration.

Each test writes a small temporary config file (via pytest's `tmp_path`
fixture, which provides a throwaway directory) and checks that load_config
parses it correctly. No browser, no network.
"""

from datetime import date
from pathlib import Path

import pytest

from movilidad_foranea.config import load_config

# A minimal, valid configuration reused across several tests.
VALID_YAML = """
output_dir: "./output"

mobility:
  headless: true
  start_date: "2026-11-01"
  n_days: 5
  routes:
    - [ "Ciudad de México, CDMX", "Acapulco" ]
    - [ "Ciudad de México, CDMX", "Puebla" ]

accommodation:
  headless: false
  checkin_date: "2026-12-24"
  stay_nights: 3
  cities:
    - "Cancún"
"""


def _write_config(tmp_path: Path, text: str) -> Path:
    """Helper: write `text` to a config.yaml inside the temp dir and return its path."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(text, encoding="utf-8")
    return config_file


def test_parses_output_dir(tmp_path):
    config = load_config(_write_config(tmp_path, VALID_YAML))
    assert config.output_dir == Path("./output")


def test_parses_mobility_fields(tmp_path):
    config = load_config(_write_config(tmp_path, VALID_YAML))
    assert config.mobility.start_date == date(2026, 11, 1)
    assert config.mobility.n_days == 5
    assert config.mobility.headless is True


def test_routes_become_tuples(tmp_path):
    """Each route in the YAML (a list) must become an (origin, destination) tuple."""
    config = load_config(_write_config(tmp_path, VALID_YAML))
    assert config.mobility.routes == [
        ("Ciudad de México, CDMX", "Acapulco"),
        ("Ciudad de México, CDMX", "Puebla"),
    ]


def test_parses_accommodation_fields(tmp_path):
    config = load_config(_write_config(tmp_path, VALID_YAML))
    assert config.accommodation.checkin_date == date(2026, 12, 24)
    assert config.accommodation.stay_nights == 3
    assert config.accommodation.cities == ["Cancún"]


def test_invalid_date_raises(tmp_path):
    """A malformed date should fail at load time with a clear ValueError."""
    bad_yaml = VALID_YAML.replace('"2026-11-01"', '"2026-13-99"')  # month 13, day 99
    with pytest.raises(ValueError):
        load_config(_write_config(tmp_path, bad_yaml))
