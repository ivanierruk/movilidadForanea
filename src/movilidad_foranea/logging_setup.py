"""Centralized per-platform file logging setup.

Each scraper writes warnings and errors to its own log file in the output
directory. This helper attaches the file handler to the scraper's own (named)
logger rather than the root logger, which fixes two problems in the original
per-scraper setup:

  * Attaching to the root logger meant that, in an "all" run, every platform's
    messages were written into every platform's log file (cross-contamination).
    The handler is now attached to the named logger, and propagation to the
    root logger is turned off, so each platform's messages stay in its own file.

  * The setup was not idempotent: calling it again added a duplicate handler, so
    every log line was written multiple times. It is now a no-op if a handler
    for the same file is already attached.
"""

from __future__ import annotations

import logging
from pathlib import Path

_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def setup_file_logging(logger_name: str, output_dir: Path, log_filename: str) -> None:
    """Attach a file handler for `logger_name`, writing to output_dir/log_filename.

    Parameters
    ----------
    logger_name:
        Name of the logger to attach the handler to (each scraper uses its class
        name, e.g. "ADOScraper").
    output_dir:
        Directory the log file is written into (created if needed).
    log_filename:
        Name of the log file, e.g. "scraping_errors_ADO.log".
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = (output_dir / log_filename).resolve()

    target = logging.getLogger(logger_name)
    target.setLevel(logging.WARNING)
    # Keep each platform's messages in its own file only.
    target.propagate = False

    # Idempotent: do nothing if a handler for this exact file already exists.
    for existing in target.handlers:
        if (
            isinstance(existing, logging.FileHandler)
            and Path(getattr(existing, "baseFilename", "")) == log_path
        ):
            return

    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    target.addHandler(handler)
