import logging

from app.parsers.bvvg_detail_parser import DetailRecord, parse_detail_page
from app.scrapers.bvvg.http_client import BvvgHttpClient, PageFetchError

logger = logging.getLogger(__name__)


def fetch_detail_record(client: BvvgHttpClient, detail_url: str) -> DetailRecord:
    try:
        html = client.fetch_html(detail_url)
    except PageFetchError:
        logger.exception("Failed to fetch detail page %s", detail_url)
        raise

    return parse_detail_page(html)
