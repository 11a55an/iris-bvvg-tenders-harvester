from app.database.repositories.signal_ingest_repository import UpsertSummary
from app.loaders.signal_ingest_loader import SignalIngestLoader
from app.transformers.signal_record import SignalRecord


class FakeRepository:
    def __init__(self):
        self.received_records: list[SignalRecord] = []

    def upsert_many(self, records: list[SignalRecord]) -> UpsertSummary:
        self.received_records = records
        return UpsertSummary(inserted=len(records), updated=0, unchanged=0)


def _record(source_id: str, domain_tags: list[str], location_precision: str, issues=None) -> SignalRecord:
    return SignalRecord(
        source_system="bvvg",
        source_id=source_id,
        source_url=f"https://www.bvvg.de/objekte/{source_id.lower()}/",
        title=f"Titel {source_id}",
        objektart_label=None,
        objektart_slug=None,
        domain_tags=domain_tags,
        bundesland=None,
        landkreis=None,
        gemeinde=None,
        gemarkung=None,
        size_hectares=None,
        marketing_type=None,
        price_raw=None,
        tender_end_at=None,
        location_point=None,
        location_precision=location_precision,
        location_note=None,
        attachment_urls=[],
        description=None,
        validation_issues=issues or [],
    )


def test_loader_persists_only_in_scope_records():
    repository = FakeRepository()
    loader = SignalIngestLoader(repository)
    records = [
        _record("A1", ["agricultural"], "approximate"),
        _record("B1", [], "unresolved"),
        _record("C1", ["forest"], "unresolved"),
    ]

    report = loader.load(records)

    assert report.total_candidates == 3
    assert report.in_scope == 2
    assert report.out_of_scope == 1
    assert report.unresolved_locations == 2
    assert {r.source_id for r in repository.received_records} == {"A1", "C1"}


def test_loader_reports_per_record_validation_issues():
    repository = FakeRepository()
    loader = SignalIngestLoader(repository)
    records = [
        _record("A1", ["agricultural"], "approximate", issues=["missing size_hectares"]),
    ]

    report = loader.load(records)

    assert report.per_record_issues == {"A1": ["missing size_hectares"]}


def test_loader_handles_empty_input():
    repository = FakeRepository()
    loader = SignalIngestLoader(repository)

    report = loader.load([])

    assert report.total_candidates == 0
    assert report.inserted == 0
