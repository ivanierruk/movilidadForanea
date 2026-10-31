"""Tests for the shared retry policy. Pure logic: no browser, no network.

A no-wait retryer is used so the tests run instantly.
"""

import logging

import pytest
from selenium.common.exceptions import TimeoutException, WebDriverException
from tenacity import wait_none

from movilidad_foranea.retry_config import build_retryer, MAX_ATTEMPTS

_LOGGER = logging.getLogger("test-retry")


def _fast_retryer():
    return build_retryer(_LOGGER, wait=wait_none())


def test_retries_then_succeeds():
    """A call that fails once with a Selenium error should be retried and succeed."""
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 2:
            raise TimeoutException("not ready yet")
        return "ok"

    assert _fast_retryer()(flaky) == "ok"
    assert calls["n"] == 2


def test_gives_up_after_max_attempts():
    """Persistent Selenium failures should exhaust the attempts and re-raise."""
    calls = {"n": 0}

    def always_fails():
        calls["n"] += 1
        raise WebDriverException("still broken")

    with pytest.raises(WebDriverException):
        _fast_retryer()(always_fails)
    assert calls["n"] == MAX_ATTEMPTS


def test_does_not_retry_non_selenium_errors():
    """A non-Selenium error should propagate immediately, without retrying."""
    calls = {"n": 0}

    def value_error():
        calls["n"] += 1
        raise ValueError("a different kind of error")

    with pytest.raises(ValueError):
        _fast_retryer()(value_error)
    assert calls["n"] == 1
