"""Tests for the centralized file-logging setup. No network, no browser."""

import logging

from movilidad_foranea.logging_setup import setup_file_logging


def _reset(logger_name: str) -> logging.Logger:
    """Return a clean logger: close and remove any existing handlers first."""
    logger = logging.getLogger(logger_name)
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)
    return logger


def test_adds_a_single_file_handler(tmp_path):
    logger = _reset("TestScraperA")
    setup_file_logging("TestScraperA", tmp_path, "a.log")
    file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
    assert len(file_handlers) == 1


def test_is_idempotent(tmp_path):
    """Calling it twice for the same file must not add a duplicate handler."""
    logger = _reset("TestScraperB")
    setup_file_logging("TestScraperB", tmp_path, "b.log")
    setup_file_logging("TestScraperB", tmp_path, "b.log")
    file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
    assert len(file_handlers) == 1


def test_does_not_touch_the_root_logger(tmp_path):
    _reset("TestScraperC")
    root_handlers_before = len(logging.getLogger().handlers)
    setup_file_logging("TestScraperC", tmp_path, "c.log")
    assert len(logging.getLogger().handlers) == root_handlers_before


def test_creates_the_output_directory(tmp_path):
    _reset("TestScraperD")
    nested = tmp_path / "nested" / "logs"
    setup_file_logging("TestScraperD", nested, "d.log")
    assert nested.is_dir()
