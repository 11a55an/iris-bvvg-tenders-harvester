import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class DatabaseSettings:
    host: str
    port: int
    name: str
    user: str
    password: str
    schema: str

    @property
    def sqlalchemy_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )


@dataclass(frozen=True)
class ScraperSettings:
    base_url: str
    listing_path: str
    request_timeout_seconds: int
    request_delay_seconds: float
    max_retries: int
    user_agent: str
    max_pages: int | None


def load_database_settings() -> DatabaseSettings:
    return DatabaseSettings(
        host=os.environ.get("BVVG_DB_HOST", "localhost"),
        port=int(os.environ.get("BVVG_DB_PORT", "5432")),
        name=os.environ.get("BVVG_DB_NAME", "iris"),
        user=os.environ.get("BVVG_DB_USER", "iris"),
        password=os.environ.get("BVVG_DB_PASSWORD", ""),
        schema=os.environ.get("BVVG_DB_SCHEMA", "iris_staging"),
    )


def load_scraper_settings() -> ScraperSettings:
    max_pages_raw = os.environ.get("BVVG_MAX_PAGES")
    return ScraperSettings(
        base_url=os.environ.get("BVVG_BASE_URL", "https://www.bvvg.de"),
        listing_path=os.environ.get("BVVG_LISTING_PATH", "/objekte/"),
        request_timeout_seconds=int(os.environ.get("BVVG_REQUEST_TIMEOUT", "30")),
        request_delay_seconds=float(os.environ.get("BVVG_REQUEST_DELAY", "1.0")),
        max_retries=int(os.environ.get("BVVG_MAX_RETRIES", "3")),
        user_agent=os.environ.get(
            "BVVG_USER_AGENT",
            "IrisBvvgTendersHarvester/0.1 (+contact: set BVVG_USER_AGENT env var)",
        ),
        max_pages=int(max_pages_raw) if max_pages_raw else None,
    )
