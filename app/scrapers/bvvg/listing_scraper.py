import logging
from collections.abc import Iterator

from app.config import ScraperSettings
from app.parsers.bvvg_listing_parser import ListingStub, parse_listing_stubs, parse_pagination
from app.scrapers.bvvg.http_client import BvvgHttpClient, PageFetchError

logger = logging.getLogger(__name__)


def build_listing_page_url(settings: ScraperSettings, page_number: int) -> str:
    base = settings.base_url.rstrip("/")
    path = settings.listing_path.strip("/")
    if page_number <= 1:
        return f"{base}/{path}/"
    return f"{base}/{path}/page/{page_number}/"


def iter_listing_stubs(
    client: BvvgHttpClient, settings: ScraperSettings
) -> Iterator[ListingStub]:
    page_number = 1
    total_pages = 1

    while page_number <= total_pages:
        if settings.max_pages is not None and page_number > settings.max_pages:
            logger.info("Stopping at configured max_pages=%s", settings.max_pages)
            break

        url = build_listing_page_url(settings, page_number)
        try:
            html = client.fetch_html(url)
        except PageFetchError:
            logger.exception("Failed to fetch listing page %s", url)
            raise

        pagination = parse_pagination(html, page_number)
        total_pages = pagination.total_pages

        yield from parse_listing_stubs(html)

        page_number += 1
