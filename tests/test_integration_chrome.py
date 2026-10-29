"""Integration smoke test: verify Selenium can launch Chrome.

This test is marked 'integration' because it requires Google Chrome to be
installed and downloads ChromeDriver at runtime via webdriver-manager. It is
therefore NOT part of the stable unit-test suite that runs in continuous
integration (CI).

It does NOT visit any of the scraped websites: it loads a local, in-memory
blank page, so it checks only that the Selenium <-> Chrome wiring works on this
machine (the same wiring every scraper's open_browser() depends on).

Run it explicitly with:

    pytest -m integration

A plain `pytest` skips it (see the addopts setting in pyproject.toml).
"""

import pytest

# Applies the 'integration' marker to every test in this file.
pytestmark = pytest.mark.integration


def test_chrome_launches_and_loads_a_page():
    """Launch headless Chrome, load a trivial local page, and read its title."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    options = Options()
    options.add_argument("--headless=new")  # no visible window needed for the check

    driver = None
    try:
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options,
        )
        # A data: URL is an in-memory page; this touches no external website.
        driver.get("data:text/html,<title>ok</title>")
        assert driver.title == "ok"
    finally:
        # Always close the browser, even if the assertion fails.
        if driver is not None:
            driver.quit()
