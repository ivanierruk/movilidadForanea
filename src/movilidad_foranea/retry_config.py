"""Shared retry policy for fragile Selenium operations.

Web scraping fails transiently: a page loads slowly, an element is not ready
yet, a request is dropped. tenacity retries the operation a few times with
exponential backoff before giving up, which makes a run more robust without
hiding genuine, persistent failures: after the attempts are exhausted the last
exception is re-raised.

Only Selenium's WebDriverException (and its subclasses, such as
TimeoutException) triggers a retry; any other error propagates immediately.
"""

from __future__ import annotations

import logging

from selenium.common.exceptions import WebDriverException
from tenacity import (
    Retrying,
    before_sleep_log,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

MAX_ATTEMPTS = 3


def build_retryer(
    logger: logging.Logger, *, max_attempts: int = MAX_ATTEMPTS, wait=None
) -> Retrying:
    """Return a tenacity Retrying configured for Selenium operations.

    Retries up to `max_attempts` times on WebDriverException, waiting 2, 4, 8…
    seconds (capped at 15) between attempts, logs a warning before each retry,
    and re-raises the last exception if all attempts fail.

    `max_attempts` and `wait` are parameters mainly so tests can run fast (with
    no wait); production code uses the defaults.
    """
    return Retrying(
        retry=retry_if_exception_type(WebDriverException),
        stop=stop_after_attempt(max_attempts),
        wait=(
            wait if wait is not None else wait_exponential(multiplier=2, min=2, max=15)
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
