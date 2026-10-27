from sqlalchemy import text

from app.database.repositories.signal_ingest_repository import SignalIngestRepository
from app.parsers.bvvg_detail_parser import parse_detail_page
from app.parsers.bvvg_listing_parser import ListingStub
from app.transformers.signal_record import build_signal_record


def _real_record(detail_graeben_in_betzin_2_html):
    detail = parse_detail_page(detail_graeben_in_betzin_2_html)
    stub = ListingStub(
        source_id="BB68-1800-045626",
        title="Gräben in Betzin 2",
        detail_url="https://www.bvvg.de/objekte/graeben-in-betzin-2/",
        region_subtitle="Brandenburg, Ostprignitz-Ruppin",
    )
    return build_signal_record(stub, detail)


def test_upsert_many_inserts_once_and_is_idempotent_on_rerun(
    db_session, detail_graeben_in_betzin_2_html
):
    repository = SignalIngestRepository(db_session)
    record = _real_record(detail_graeben_in_betzin_2_html)

    first_summary = repository.upsert_many([record])
    db_session.commit()

    second_summary = repository.upsert_many([record])
    db_session.commit()

    row_count = db_session.execute(
        text("select count(*) from iris_staging.signal_ingest")
    ).scalar()

    assert first_summary.inserted == 1
    assert second_summary.unchanged == 1
    assert second_summary.inserted == 0
    assert row_count == 1


def test_upsert_many_updates_when_content_changes(db_session, detail_graeben_in_betzin_2_html):
    repository = SignalIngestRepository(db_session)
    record = _real_record(detail_graeben_in_betzin_2_html)

    repository.upsert_many([record])
    db_session.commit()

    changed_record = record.__class__(**{**record.__dict__, "price_raw": "150000 EUR"})
    summary = repository.upsert_many([changed_record])
    db_session.commit()

    stored_price = db_session.execute(
        text("select price_raw from iris_staging.signal_ingest where source_id = :sid"),
        {"sid": record.source_id},
    ).scalar()

    assert summary.updated == 1
    assert stored_price == "150000 EUR"


def test_upsert_many_persists_valid_point_geometry(db_session, detail_graeben_in_betzin_2_html):
    repository = SignalIngestRepository(db_session)
    record = _real_record(detail_graeben_in_betzin_2_html)

    repository.upsert_many([record])
    db_session.commit()

    srid = db_session.execute(
        text("select ST_SRID(location_point) from iris_staging.signal_ingest where source_id = :sid"),
        {"sid": record.source_id},
    ).scalar()

    assert srid == 25832
