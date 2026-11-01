# Architecture

This document describes how the package is organized, for reviewers and for
anyone who wants to extend it.

## Package layout

```
src/movilidad_foranea/
├── __init__.py
├── config.py            # loads and validates config.yaml into dataclasses
├── cli.py               # the `movilidad-foranea` command (all / mobility / hotels)
├── cleaning.py          # normalize_missing(): one consistent NaN for missing values
├── validation.py        # pandera schemas for bus and hotel output
├── logging_setup.py     # per-platform file logging (attached to the named logger)
├── retry_config.py      # tenacity retry policy for transient Selenium failures
├── mobility/
│   ├── _dates.py        # build_travel_dates(): shared date helper
│   ├── ado.py
│   ├── omnibus.py
│   ├── clickbus.py
│   └── busbud.py
└── accommodation/
    └── booking.py
```

## How the pieces fit together

A run flows like this:

1. **`cli.py`** parses the command, loads the configuration with **`config.py`**,
   and dispatches to the selected scraper(s). For each platform it hands the
   scraper a copy of the configuration whose `output_dir` points to that
   platform's subfolder, so results never mix between platforms.

2. Each **scraper** (`mobility/*`, `accommodation/booking.py`) drives Chrome with
   Selenium to perform one query per (route/city, date). The per-query attempt is
   wrapped by the **`retry_config.py`** policy: on a transient Selenium error it
   is retried a few times with exponential backoff, each attempt starting from a
   fresh browser.

3. When results are read, the scraper first waits for the results to render; if
   none appear, it logs a warning (via **`logging_setup.py`**) instead of
   silently reporting an empty result.

4. Before a batch is written, the DataFrame is passed through
   **`cleaning.py`** (missing values → NaN) and **`validation.py`** (schema
   check). Validation issues are logged, not fatal.

5. Per-query files are written as `.xlsx`; the consolidated, de-duplicated result
   is written as both `.xlsx` and `.csv`.

## Cross-cutting concerns

- **Configuration** is external (YAML) and never requires editing source code.
- **Logging** is per-platform: each scraper's logger writes only to its own file.
- **Retries** apply at the whole-query level, not per interaction step, so a
  retry resets browser state cleanly.
- **Validation** separates two concerns: structural/format checks (done here) and
  de-duplication (a pipeline transformation, done by `drop_duplicates`).

## Adding a new platform

A new bus platform typically requires:

1. A new module under `mobility/` with a scraper class and a `scrape_<name>()`
   function, following the structure of the existing ones (open browser, enter
   origin/destination/date, submit, read results, export).
2. Registering it in `cli.py` by adding an entry to `MOBILITY_SCRAPERS`
   (or `ACCOMMODATION_SCRAPERS` for a lodging platform). The CLI then exposes it
   automatically, including as a `--platform` choice.
3. Reusing the shared helpers: `build_travel_dates`, `normalize_missing`,
   `validate_mobility` / `validate_accommodation`, `setup_file_logging`, and
   `build_retryer`.

## Tests

- **Unit tests** (run by default with `pytest`) cover the pure logic: date
  generation, configuration loading, the CLI wiring, trip-id generation,
  missing-value normalization, the validation schemas, logging setup and the
  retry policy. They need no browser or network.
- **Integration tests** (marked `integration`, run with `pytest -m integration`)
  check that Chrome launches and that each platform URL is reachable. They need a
  browser and network and are excluded from the default run.
