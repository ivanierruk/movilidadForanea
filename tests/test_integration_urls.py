"""Integration test: check that each platform's entry URL is still reachable.

Marked 'integration' because it needs network access; run it with:

    pytest -m integration

This check confirms that the domain resolves and the server responds, which catches a
platform URL that has disappeared entirely (dead domain, removed page).

It deliberately does NOT require an HTTP 200. Several of these sites return a
4xx status (for example, bot-protection 403s) to a plain request even though
they are perfectly alive and scrapable through a real browser.

A 5xx status is treated as the server being down. Whether the page's internal
structure still matches each scraper's selectors can only be confirmed by
running the scrapers themselves.
"""

import urllib.error
import urllib.request

import pytest

pytestmark = pytest.mark.integration

# These mirror each scraper's base_url. Kept here (rather than imported) so the
# test never has to instantiate a scraper (BookingScraper opens Chrome on init).
BASE_URLS = {
    "ado": "https://www.ado.com.mx/",
    "omnibus": "https://www.odm.com.mx/",
    "clickbus": "https://www.clickbus.com.mx/",
    "busbud": "https://www.busbud.com/es-mx/bt/billetes-de-autobus",
    "booking": "https://www.booking.com",
}

# A browser-like User-Agent; some servers reject the default urllib agent.
_USER_AGENT = "Mozilla/5.0 (compatible; movilidad-foranea-liveness-check/1.0)"


@pytest.mark.parametrize("platform,url", sorted(BASE_URLS.items()))
def test_platform_url_is_reachable(platform, url):
    """The platform domain should resolve and the server should respond."""
    request = urllib.request.Request(
        url, method="GET", headers={"User-Agent": _USER_AGENT}
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = response.status
    except urllib.error.HTTPError as exc:
        # The server answered with an error status: still reachable/alive.
        status = exc.code
    # A urllib.error.URLError (DNS failure, refused connection, timeout) is NOT
    # caught here on purpose: it propagates and fails the test, which is exactly
    # what "this URL is gone" should look like.

    # 5xx means the server itself is down; 2xx-4xx means it responded.
    assert status < 500, f"{platform} ({url}) returned HTTP {status}"
