import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError

from app.config import load_database_settings
from app.database.session import create_session_factory


@pytest.fixture
def db_session():
    settings = load_database_settings()
    factory = create_session_factory(settings)

    try:
        session = factory()
        session.execute(text("select 1"))
    except OperationalError:
        pytest.skip(
            "no reachable database configured via BVVG_DB_* env vars, "
            "start it with: docker compose up -d db"
        )
        return

    try:
        session.execute(text("select 1 from iris_staging.signal_ingest limit 1"))
    except ProgrammingError:
        session.rollback()
        session.close()
        pytest.skip(
            "iris_staging.signal_ingest does not exist yet, "
            "run: alembic upgrade head"
        )
        return

    session.execute(text("truncate table iris_staging.signal_ingest"))
    session.commit()

    yield session

    session.rollback()
    session.close()
