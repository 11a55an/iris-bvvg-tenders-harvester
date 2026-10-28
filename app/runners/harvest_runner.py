import logging

from app.config import ScraperSettings, load_database_settings, load_scraper_settings
from app.database.repositories.signal_ingest_repository import SignalIngestRepository
from app.database.session import create_session_factory, session_scope
from app.loaders.signal_ingest_loader import QualityReport, SignalIngestLoader
from app.scrapers.bvvg.detail_scraper import fetch_detail_record
from app.scrapers.bvvg.http_client import BvvgHttpClient, PageFetchError
from app.scrapers.bvvg.listing_scraper import iter_listing_stubs
from app.transformers.signal_record import SignalRecord, TransformationError, build_signal_record

logger = logging.getLogger(__name__)


class HarvestSkips:
    def __init__(self) -> None:
        self.network_errors = 0
        self.malformed = 0
        self.duplicates_in_batch = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "network_errors": self.network_errors,
            "malformed": self.malformed,
            "duplicates_in_batch": self.duplicates_in_batch,
        }


def harvest_signal_records(
    client: BvvgHttpClient, settings: ScraperSettings
) -> tuple[list[SignalRecord], HarvestSkips]:
    records: list[SignalRecord] = []
    seen_source_ids: set[str] = set()
    skips = HarvestSkips()

    for stub in iter_listing_stubs(client, settings):
        if stub.source_id in seen_source_ids:
            logger.info("Skipping duplicate listing %s seen earlier in this run", stub.source_id)
            skips.duplicates_in_batch += 1
            continue

        logger.info("Fetching detail page for %s: %s", stub.source_id, stub.detail_url)
        try:
            detail = fetch_detail_record(client, stub.detail_url)
        except PageFetchError as exc:
            logger.warning("Skipping %s due to fetch error: %s", stub.source_id, exc)
            skips.network_errors += 1
            continue

        try:
            record = build_signal_record(stub, detail)
        except TransformationError as exc:
            logger.warning("Skipping %s due to transformation error: %s", stub.source_id, exc)
            skips.malformed += 1
            continue

        seen_source_ids.add(stub.source_id)
        records.append(record)

    return records, skips


def run() -> QualityReport:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    scraper_settings = load_scraper_settings()
    database_settings = load_database_settings()

    logger.info("Starting harvest run against %s", scraper_settings.base_url)

    client = BvvgHttpClient(scraper_settings)
    try:
        records, skips = harvest_signal_records(client, scraper_settings)
    finally:
        client.close()

    logger.info("Scraping done, built %s records, loading into database", len(records))

    session_factory = create_session_factory(database_settings)
    with session_scope(session_factory) as session:
        repository = SignalIngestRepository(session)
        loader = SignalIngestLoader(repository)
        report = loader.load(records)

    logger.info("Harvest complete: %s", report)
    logger.info("Skipped during scraping: %s", skips.as_dict())
    return report


if __name__ == "__main__":
    run()
