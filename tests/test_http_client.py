import responses

from app.config import ScraperSettings
from app.scrapers.bvvg.http_client import BvvgHttpClient, PageFetchError


def _settings(**overrides) -> ScraperSettings:
    defaults = dict(
        base_url="https://www.bvvg.de",
        listing_path="/objekte/",
        request_timeout_seconds=5,
        request_delay_seconds=0.0,
        max_retries=3,
        user_agent="test-agent",
        max_pages=None,
    )
    defaults.update(overrides)
    return ScraperSettings(**defaults)


@responses.activate
def test_fetch_html_returns_body_on_success():
    responses.add(
        responses.GET,
        "https://www.bvvg.de/objekte/",
        body="<html>ok</html>",
        status=200,
    )
    client = BvvgHttpClient(_settings())

    html = client.fetch_html("https://www.bvvg.de/objekte/")

    assert html == "<html>ok</html>"


@responses.activate
def test_fetch_html_retries_after_transient_failure_then_succeeds():
    responses.add(responses.GET, "https://www.bvvg.de/objekte/", status=503)
    responses.add(
        responses.GET,
        "https://www.bvvg.de/objekte/",
        body="<html>recovered</html>",
        status=200,
    )
    client = BvvgHttpClient(_settings())

    html = client.fetch_html("https://www.bvvg.de/objekte/")

    assert html == "<html>recovered</html>"
    assert len(responses.calls) == 2


@responses.activate
def test_fetch_html_raises_after_exhausting_retries():
    for _ in range(3):
        responses.add(responses.GET, "https://www.bvvg.de/objekte/", status=500)
    client = BvvgHttpClient(_settings(max_retries=3))

    try:
        client.fetch_html("https://www.bvvg.de/objekte/")
        assert False, "expected PageFetchError"
    except PageFetchError as exc:
        assert exc.url == "https://www.bvvg.de/objekte/"

    assert len(responses.calls) == 3


@responses.activate
def test_fetch_html_treats_empty_body_as_failure():
    for _ in range(3):
        responses.add(responses.GET, "https://www.bvvg.de/objekte/", body="", status=200)
    client = BvvgHttpClient(_settings(max_retries=3))

    try:
        client.fetch_html("https://www.bvvg.de/objekte/")
        assert False, "expected PageFetchError"
    except PageFetchError:
        pass

    assert len(responses.calls) == 3
