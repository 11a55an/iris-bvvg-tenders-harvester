import uuid

from geoalchemy2 import Geometry
from sqlalchemy import ARRAY, DateTime, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class SignalIngest(Base):
    __tablename__ = "signal_ingest"
    __table_args__ = (
        UniqueConstraint("source_system", "source_id", name="uq_signal_ingest_source"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_system: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    objektart_label: Mapped[str | None] = mapped_column(String(128))
    objektart_slug: Mapped[str | None] = mapped_column(String(128))
    domain_tags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    bundesland: Mapped[str | None] = mapped_column(String(64))
    landkreis: Mapped[str | None] = mapped_column(String(128))
    gemeinde: Mapped[str | None] = mapped_column(String(128))
    gemarkung: Mapped[str | None] = mapped_column(String(128))
    size_hectares: Mapped[float | None] = mapped_column(Numeric(12, 4))
    marketing_type: Mapped[str | None] = mapped_column(String(16))
    price_raw: Mapped[str | None] = mapped_column(String(128))
    tender_end_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    location_point = mapped_column(Geometry(geometry_type="POINT", srid=25832), nullable=True)
    location_precision: Mapped[str] = mapped_column(String(16), nullable=False)
    location_note: Mapped[str | None] = mapped_column(Text)
    attachment_urls: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    raw_fields: Mapped[dict] = mapped_column(JSONB, nullable=False)
    validation_issues: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    first_seen_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
