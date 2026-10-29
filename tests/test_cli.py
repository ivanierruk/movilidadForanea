"""Tests for the command-line interface.

These tests exercise argument parsing and the per-platform output-directory
logic. They never open Chrome and never run a real scraper: they only check
the plumbing of the CLI.
"""

from pathlib import Path

import pytest

from movilidad_foranea import cli
from movilidad_foranea.config import load_config


def _make_config(tmp_path: Path):
    """Write a small config.yaml inside tmp_path and load it.

    output_dir points inside the temporary directory so the subdirectory tests
    create folders there, not in the current working directory.
    """
    out = tmp_path / "out"
    text = f"""
        output_dir: "{out}"
        mobility:
          headless: true
          start_date: "2026-11-01"
          n_days: 2
          routes:
            - [ "A", "B" ]
        accommodation:
          headless: true
          checkin_date: "2026-11-01"
          stay_nights: 3
          cities:
            - "C"
    """
    config_file = tmp_path / "config.yaml"
    config_file.write_text(text, encoding="utf-8")
    return load_config(config_file)


# --- Argument parsing -------------------------------------------------------


def test_parser_accepts_all_command():
    args = cli.build_parser().parse_args(["all", "--config", "config.yaml"])
    assert args.command == "all"


def test_parser_accepts_mobility_with_platform():
    args = cli.build_parser().parse_args(
        ["mobility", "--platform", "ado", "--config", "config.yaml"]
    )
    assert args.command == "mobility"
    assert args.platform == "ado"


def test_parser_mobility_platform_defaults_to_none():
    """Without --platform, mobility should run all four (platform is None)."""
    args = cli.build_parser().parse_args(["mobility", "--config", "config.yaml"])
    assert args.platform is None


def test_parser_rejects_unknown_platform():
    """An invalid --platform value should make argparse exit (SystemExit)."""
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(
            ["mobility", "--platform", "does-not-exist", "--config", "config.yaml"]
        )


def test_parser_requires_config():
    """Every subcommand requires --config; omitting it should exit."""
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["all"])


# --- Per-platform output directory -----------------------------------------


def test_config_for_platform_points_to_subdirectory(tmp_path):
    config = _make_config(tmp_path)
    sub = cli._config_for_platform(config, "ado")
    assert sub.output_dir == config.output_dir / "ado"


def test_config_for_platform_creates_the_directory(tmp_path):
    config = _make_config(tmp_path)
    sub = cli._config_for_platform(config, "booking")
    assert sub.output_dir.is_dir()


def test_config_for_platform_preserves_other_fields(tmp_path):
    """Only output_dir should change; routes, dates, etc. stay the same."""
    config = _make_config(tmp_path)
    sub = cli._config_for_platform(config, "ado")
    assert sub.mobility == config.mobility
    assert sub.accommodation == config.accommodation


# --- Platform registries ----------------------------------------------------


def test_all_mobility_platforms_are_registered():
    assert set(cli.MOBILITY_SCRAPERS) == {"ado", "omnibus", "clickbus", "busbud"}


def test_booking_is_registered():
    assert "booking" in cli.ACCOMMODATION_SCRAPERS
