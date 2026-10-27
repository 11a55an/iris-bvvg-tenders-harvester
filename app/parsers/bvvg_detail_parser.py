import base64
import re
from dataclasses import dataclass

from bs4 import BeautifulSoup

MAP_IFRAME_COORDINATE_PATTERN = re.compile(r"[?&](?:amp;)?q=(-?\d+\.\d+),(-?\d+\.\d+)")
TENDER_END_PATTERN = re.compile(
    r"Ausschreibung endet am\s+(\d{2})\.(\d{2})\.(\d{4}),\s*um\s+(\d{2}):(\d{2})\s*Uhr"
)


@dataclass(frozen=True)
class RawCoordinate:
    latitude: float
    longitude: float
    is_approximate: bool


@dataclass(frozen=True)
class DetailRecord:
    source_id: str | None
    title: str | None
    canonical_url: str | None
    bundesland: str | None
    kreis: str | None
    gemeinde: str | None
    gemarkung: str | None
    objektart_label: str | None
    size_hectares_raw: str | None
    marketing_type_label: str | None
    price_raw: str | None
    tender_end_day: int | None
    tender_end_month: int | None
    tender_end_year: int | None
    tender_end_hour: int | None
    tender_end_minute: int | None
    description: str | None
    coordinate: RawCoordinate | None
    attachment_urls: list[str]


class DetailPageParseError(Exception):
    pass


def _extract_object_data_fields(soup: BeautifulSoup) -> dict[str, str]:
    fields: dict[str, str] = {}
    for item in soup.select("div.property-details .list-group .list-group-item"):
        label = item.select_one(".dt")
        value = item.select_one(".dd")
        if label and value:
            fields[label.get_text(strip=True)] = value.get_text(strip=True)
    return fields


def _extract_coordinate(soup: BeautifulSoup) -> RawCoordinate | None:
    for script in soup.select('script[type="text/template"]'):
        encoded = script.get_text(strip=True)
        if not encoded:
            continue
        try:
            decoded = base64.b64decode(encoded).decode("utf-8", errors="ignore")
        except (ValueError, UnicodeDecodeError):
            continue

        match = MAP_IFRAME_COORDINATE_PATTERN.search(decoded)
        if match:
            return RawCoordinate(
                latitude=float(match.group(1)),
                longitude=float(match.group(2)),
                is_approximate=True,
            )
    return None


def _extract_tender_end(soup: BeautifulSoup) -> tuple[int | None, ...]:
    text = soup.get_text(" ", strip=True)
    match = TENDER_END_PATTERN.search(text)
    if not match:
        return (None, None, None, None, None)
    day, month, year, hour, minute = match.groups()
    return (int(day), int(month), int(year), int(hour), int(minute))


def parse_detail_page(html: str) -> DetailRecord:
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.select_one("h1.property-title")
    canonical_tag = soup.select_one("link[rel='canonical']")
    description_tag = soup.select_one(".property-description .panel-body")

    fields = _extract_object_data_fields(soup)
    tender_end_day, tender_end_month, tender_end_year, tender_end_hour, tender_end_minute = (
        _extract_tender_end(soup)
    )

    price_raw = None
    marketing_type_label = None
    for label, value in fields.items():
        if label.startswith("Orientierungswert"):
            price_raw = value
            marketing_match = re.search(r"\((Kauf|Pacht)\)", label)
            if marketing_match:
                marketing_type_label = marketing_match.group(1)
            break

    attachment_urls = [
        a["href"]
        for a in soup.select("a[href*='/attachments/']")
        if a.get("href", "").lower().endswith(".pdf")
    ]

    return DetailRecord(
        source_id=fields.get("Objekt-Nr."),
        title=title_tag.get_text(strip=True) if title_tag else None,
        canonical_url=canonical_tag["href"] if canonical_tag else None,
        bundesland=fields.get("Bundesland"),
        kreis=fields.get("Kreis"),
        gemeinde=fields.get("Gemeinde"),
        gemarkung=fields.get("Gemarkung"),
        objektart_label=fields.get("Objektart"),
        size_hectares_raw=fields.get("Größe"),
        marketing_type_label=marketing_type_label,
        price_raw=price_raw,
        tender_end_day=tender_end_day,
        tender_end_month=tender_end_month,
        tender_end_year=tender_end_year,
        tender_end_hour=tender_end_hour,
        tender_end_minute=tender_end_minute,
        description=description_tag.get_text(" ", strip=True) if description_tag else None,
        coordinate=_extract_coordinate(soup),
        attachment_urls=sorted(set(attachment_urls)),
    )
