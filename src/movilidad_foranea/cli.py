"""Command-line interface for movilidad-foranea.

This module is the single entry point that ties the five independent scrapers
together. It is registered in pyproject.toml under [project.scripts] as:

    movilidad-foranea = "movilidad_foranea.cli:main"

so that installing the package creates a `movilidad-foranea` command.

Usage examples
--------------
    movilidad-foranea all      --config config.yaml   # run all five scrapers
    movilidad-foranea mobility --config config.yaml   # run the four bus platforms
    movilidad-foranea mobility --platform ado --config config.yaml   # one platform
    movilidad-foranea hotels   --config config.yaml   # run only Booking

Design notes
------------
- Scrapers run SEQUENTIALLY, never in parallel. Each one drives its own Chrome
  session, and running several at once would hammer the target sites (against
  the ethical-scraping stance of this project) and risk being blocked.
- Each platform writes into its OWN subdirectory of the configured output_dir
  (output/ado, output/booking, ...), so results never mix between platforms.
  This is done by handing each scraper a copy of the Config whose output_dir
  points to that subfolder; the scraper code itself is untouched.
"""

from __future__ import annotations

import argparse
import dataclasses
import sys
from pathlib import Path

from .accommodation import booking
from .config import Config, load_config
from .mobility import ado, busbud, clickbus, omnibus

# Maps each bus platform name to the function that scrapes it.
# Adding a new platform here is all it takes for the CLI to know about it.
MOBILITY_SCRAPERS = {
    "ado": ado.scrape_ado,
    "omnibus": omnibus.scrape_omnibus,
    "clickbus": clickbus.scrape_clickbus,
    "busbud": busbud.scrape_busbud,
}

# Accommodation (hotel) platforms.
ACCOMMODATION_SCRAPERS = {
    "booking": booking.scrape_booking,
}


def _config_for_platform(config: Config, platform: str) -> Config:
    """
    Return a copy of `config` whose output_dir points to output_dir/<platform>.
    """
    platform_dir = config.output_dir / platform
    platform_dir.mkdir(parents=True, exist_ok=True)
    return dataclasses.replace(config, output_dir=platform_dir)


def _run_mobility(config: Config, platform: str | None) -> None:
    """Run one bus platform (if `platform` is given) or all four in sequence."""
    if platform is not None:
        if platform not in MOBILITY_SCRAPERS:
            available = ", ".join(MOBILITY_SCRAPERS)
            raise SystemExit(
                f"Unknown mobility platform '{platform}'. Choose one of: {available}"
            )
        selected = {platform: MOBILITY_SCRAPERS[platform]}
    else:
        selected = MOBILITY_SCRAPERS

    for name, scrape_fn in selected.items():
        print(f"\n=== Running mobility scraper: {name} ===")
        scrape_fn(_config_for_platform(config, name))


def _run_hotels(config: Config) -> None:
    """Run all accommodation (hotel) scrapers in sequence."""
    for name, scrape_fn in ACCOMMODATION_SCRAPERS.items():
        print(f"\n=== Running accommodation scraper: {name} ===")
        scrape_fn(_config_for_platform(config, name))


def build_parser() -> argparse.ArgumentParser:
    """Define the command-line grammar (subcommands and options)."""
    parser = argparse.ArgumentParser(
        prog="movilidad-foranea",
        description="Reproducible extraction of intercity bus routes and hotel geolocation in Mexico.",
    )
    # `required=True` forces the user to pick a subcommand (all / mobility / hotels).
    subcommands = parser.add_subparsers(dest="command", required=True)

    # Every subcommand needs --config,
    config_parent = argparse.ArgumentParser(add_help=False)
    config_parent.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to the config.yaml file with routes, cities and dates.",
    )

    subcommands.add_parser(
        "all",
        parents=[config_parent],
        help="Run every scraper (the four bus platforms and Booking).",
    )

    mobility_cmd = subcommands.add_parser(
        "mobility",
        parents=[config_parent],
        help="Run the bus-route scrapers.",
    )
    mobility_cmd.add_argument(
        "--platform",
        choices=sorted(MOBILITY_SCRAPERS),
        default=None,
        help="Run only this bus platform. If omitted, all four are run in sequence.",
    )

    subcommands.add_parser(
        "hotels",
        parents=[config_parent],
        help="Run the hotel (Booking) scraper.",
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    """Entry point. Parses arguments, loads the config and dispatches the run.

    `argv` defaults to the real command-line arguments; it is a parameter so
    the CLI can also be driven from tests.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    config = load_config(args.config)

    if args.command == "all":
        _run_mobility(config, platform=None)
        _run_hotels(config)
    elif args.command == "mobility":
        _run_mobility(config, platform=args.platform)
    elif args.command == "hotels":
        _run_hotels(config)
    else:
        # argparse's required=True should prevent reaching this branch.
        parser.error(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
