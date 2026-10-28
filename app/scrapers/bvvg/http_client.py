import logging
import time

import requests
from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import ScraperSettings

logger = logging.getLogger(__name__)


class PageFetchError(Exception):
    def __init__(self, url: str, reason: str):
        self.url = url
        self.reason = reason
        super().__init__(f"Failed to fetch {url}: {reason}")


class EmptyResponseError(Exception):
    pass


class BvvgHttpClient:
    def __init__(self, settings: ScraperSettings):
        self._settings = settings
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": settings.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
            }
        )
        self._retrying = Retrying(
            retry=retry_if_exception_type((requests.RequestException, EmptyResponseError)),
            stop=stop_after_attempt(settings.max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            reraise=True,
        )
        self._last_request_at: float | None = None

    def fetch_html(self, url: str) -> str:
        try:
            return self._retrying(self._get, url)
        except (requests.RequestException, EmptyResponseError) as exc:
            raise PageFetchError(url, str(exc)) from exc

    def _throttle(self) -> None:
        if self._last_request_at is None:
            return
        elapsed = time.monotonic() - self._last_request_at
        remaining = self._settings.request_delay_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def _get(self, url: str) -> str:
        self._throttle()
        try:
            response = self._session.get(
                url, timeout=self._settings.request_timeout_seconds
            )
        finally:
            self._last_request_at = time.monotonic()
        response.raise_for_status()
        if not response.text or not response.text.strip():
            raise EmptyResponseError(f"empty response body for {url}")
        return response.text

    def close(self) -> None:
        self._session.close()
