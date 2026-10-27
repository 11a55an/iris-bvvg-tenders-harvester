from dataclasses import dataclass

from geoalchemy2.shape import from_shape
from sqlalchemy import case, func, select, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.database.models.signal_ingest import SignalIngest
from app.transformers.signal_record import SignalRecord


@dataclass(frozen=True)
class UpsertSummary:
    inserted: int
    updated: int
    unchanged: int


class SignalIngestRepository:
    def __init__(self, session: Session):
        self._session = session

    def upsert_many(self, records: list[SignalRecord]) -> UpsertSummary:
        if not records:
            return UpsertSummary(inserted=0, updated=0, unchanged=0)

        keys = [(record.source_system, record.source_id) for record in records]
        existing_hashes = self._load_existing_hashes(keys)

        inserted = 0
        updated = 0
        unchanged = 0

        for record in records:
            key = (record.source_system, record.source_id)
            existing_hash = existing_hashes.get(key)
            if existing_hash is None:
                inserted += 1
            elif existing_hash != record.content_hash:
                updated += 1
            else:
                unchanged += 1

            self._upsert_one(record)

        return UpsertSummary(inserted=inserted, updated=updated, unchanged=unchanged)

    def _load_existing_hashes(self, keys: list[tuple[str, str]]) -> dict[tuple[str, str], str]:
        table = SignalIngest.__table__
        rows = self._session.execute(
            select(table.c.source_system, table.c.source_id, table.c.content_hash).where(
                tuple_(table.c.source_system, table.c.source_id).in_(keys)
            )
        ).all()
        return {(row.source_system, row.source_id): row.content_hash for row in rows}

    def _upsert_one(self, record: SignalRecord) -> None:
        table = SignalIngest.__table__
        values = _record_to_insert_values(record)

        statement = pg_insert(table).values(**values)
        update_set = {
            column: statement.excluded[column]
            for column in values
            if column not in ("source_system", "source_id")
        }
        update_set["last_seen_at"] = func.now()
        update_set["updated_at"] = case(
            (table.c.content_hash != statement.excluded.content_hash, func.now()),
            else_=table.c.updated_at,
        )

        statement = statement.on_conflict_do_update(
            index_elements=["source_system", "source_id"],
            set_=update_set,
        )
        self._session.execute(statement)


def _record_to_insert_values(record: SignalRecord) -> dict:
    location_point = None
    if record.location_point is not None:
        location_point = from_shape(record.location_point, srid=25832)

    return {
        "source_system": record.source_system,
        "source_id": record.source_id,
        "source_url": record.source_url,
        "title": record.title,
        "objektart_label": record.objektart_label,
        "objektart_slug": record.objektart_slug,
        "domain_tags": record.domain_tags,
        "bundesland": record.bundesland,
        "landkreis": record.landkreis,
        "gemeinde": record.gemeinde,
        "gemarkung": record.gemarkung,
        "size_hectares": record.size_hectares,
        "marketing_type": record.marketing_type,
        "price_raw": record.price_raw,
        "tender_end_at": record.tender_end_at,
        "location_point": location_point,
        "location_precision": record.location_precision,
        "location_note": record.location_note,
        "attachment_urls": record.attachment_urls,
        "description": record.description,
        "raw_fields": record.raw_fields,
        "validation_issues": record.validation_issues,
        "content_hash": record.content_hash,
    }
