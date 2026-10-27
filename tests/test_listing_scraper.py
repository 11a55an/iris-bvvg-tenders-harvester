import responses

from app.config import ScraperSettings
from app.scrapers.bvvg.http_client import BvvgHttpClient
from app.scrapers.bvvg.listing_scraper import build_listing_page_url, iter_listing_stubs


def _settings(max_pages=None) -> ScraperSettings:
    return ScraperSettings(
        base_url="https://www.bvvg.de",
        listing_path="/objekte/",
        request_timeout_seconds=5,
        request_delay_seconds=0.0,
        max_retries=2,
        user_agent="test-agent",
        max_pages=max_pages,
    )


def test_build_listing_page_url_for_first_and_later_pages():
    settings = _settings()

    assert build_listing_page_url(settings, 1) == "https://www.bvvg.de/objekte/"
    assert build_listing_page_url(settings, 2) == "https://www.bvvg.de/objekte/page/2/"


@responses.activate
def test_iter_listing_stubs_stops_at_configured_max_pages(
    listing_page_1_html, tests_fixtures_dir
):
    page_2_html = (tests_fixtures_dir / "listing_page_2_minimal.html").read_text(
        encoding="utf-8"
    )

    responses.add(
        responses.GET, "https://www.bvvg.de/objekte/", body=listing_page_1_html, status=200
    )
    responses.add(
        responses.GET,
        "https://www.bvvg.de/objekte/page/2/",
        body=page_2_html,
        status=200,
    )

    client = BvvgHttpClient(_settings(max_pages=2))
    stubs = list(iter_listing_stubs(client, _settings(max_pages=2)))

    assert len(responses.calls) == 2
    assert len(stubs) == 21
    assert stubs[-1].source_id == "AA11-1800-000002"


@responses.activate
def test_iter_listing_stubs_stops_when_pagination_reports_single_page():
    responses.add(
        responses.GET,
        "https://www.bvvg.de/objekte/",
        body="<html><body>no listings, no paginator</body></html>",
        status=200,
    )

    client = BvvgHttpClient(_settings())
    stubs = list(iter_listing_stubs(client, _settings()))

    assert stubs == []
    assert len(responses.calls) == 1
