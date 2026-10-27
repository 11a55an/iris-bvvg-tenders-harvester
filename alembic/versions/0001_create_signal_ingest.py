"""create iris_staging.signal_ingest

Revision ID: 0001
Revises:
Create Date: 2026-10-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE SCHEMA IF NOT EXISTS iris_staging")

    op.create_table(
        "signal_ingest",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("source_system", sa.String(32), nullable=False),
        sa.Column("source_id", sa.String(128), nullable=False),
        sa.Column("source_url", sa.Text, nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("objektart_label", sa.String(128)),
        sa.Column("objektart_slug", sa.String(128)),
        sa.Column("domain_tags", sa.ARRAY(sa.String), nullable=False),
        sa.Column("bundesland", sa.String(64)),
        sa.Column("landkreis", sa.String(128)),
        sa.Column("gemeinde", sa.String(128)),
        sa.Column("gemarkung", sa.String(128)),
        sa.Column("size_hectares", sa.Numeric(12, 4)),
        sa.Column("marketing_type", sa.String(16)),
        sa.Column("price_raw", sa.String(128)),
        sa.Column("tender_end_at", sa.DateTime(timezone=True)),
        sa.Column("location_point", Geometry(geometry_type="POINT", srid=25832)),
        sa.Column("location_precision", sa.String(16), nullable=False),
        sa.Column("location_note", sa.Text),
        sa.Column("attachment_urls", sa.ARRAY(sa.Text), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("raw_fields", JSONB, nullable=False),
        sa.Column("validation_issues", sa.ARRAY(sa.Text), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "source_system", "source_id", name="uq_signal_ingest_source"
        ),
        schema="iris_staging",
    )

    op.create_index(
        "ix_signal_ingest_tender_end_at",
        "signal_ingest",
        ["tender_end_at"],
        schema="iris_staging",
    )
    op.create_index(
        "ix_signal_ingest_location_point",
        "signal_ingest",
        ["location_point"],
        schema="iris_staging",
        postgresql_using="gist",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_signal_ingest_location_point",
        table_name="signal_ingest",
        schema="iris_staging",
    )
    op.drop_index(
        "ix_signal_ingest_tender_end_at",
        table_name="signal_ingest",
        schema="iris_staging",
    )
    op.drop_table("signal_ingest", schema="iris_staging")
