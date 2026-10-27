import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

from shapely.geometry import Point

from app.geocoding.coordinate_resolver import resolve_location
from app.parsers.bvvg_detail_parser import DetailRecord
from app.parsers.bvvg_listing_parser import ListingStub
from app.transformers.land_type_classifier import classify_domain

SOURCE_SYSTEM = "bvvg"
SOURCE_TIMEZONE = ZoneInfo("Europe/Berlin")


class TransformationError(Exception):
    pass


@dataclass(frozen=True)
class SignalRecord:
    source_system: str
    source_id: str
    source_url: str
    title: str
    objektart_label: str | None
    objektart_slug: str | None
    domain_tags: list[str]
    bundesland: str | None
    landkreis: str | None
    gemeinde: str | None
    gemarkung: str | None
    size_hectares: float | None
    marketing_type: str | None
    price_raw: str | None
    tender_end_at: datetime | None
    location_point: Point | None
    location_precision: str
    location_note: str | None
    attachment_urls: list[str]
    description: str | None
    raw_fields: dict = field(default_factory=dict)
    validation_issues: list[str] = field(default_factory=list)

    @property
    def content_hash(self) -> str:
        payload = {
            "title": self.title,
            "objektart_label": self.objektart_label,
            "domain_tags": self.domain_tags,
            "bundesland": self.bundesland,
            "landkreis": self.landkreis,
            "gemeinde": self.gemeinde,
            "gemarkung": self.gemarkung,
            "size_hectares": self.size_hectares,
            "marketing_type": self.marketing_type,
            "price_raw": self.price_raw,
            "tender_end_at": self.tender_end_at.isoformat() if self.tender_end_at else None,
            "location_wkt": self.location_point.wkt if self.location_point else None,
            "location_precision": self.location_precision,
            "attachment_urls": self.attachment_urls,
            "description": self.description,
        }
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _parse_size_hectares(raw: str | None, issues: list[str]) -> float | None:
    if not raw:
        issues.append("missing size_hectares")
        return None

    numeric_part = raw.replace("ha", "").strip().replace(".", "").replace(",", ".")
    try:
        return float(numeric_part)
    except ValueError:
        issues.append(f"unparsable size_hectares value: {raw!r}")
        return None


def _parse_tender_end_at(detail: DetailRecord, issues: list[str]) -> datetime | None:
    fields = (
        detail.tender_end_year,
        detail.tender_end_month,
        detail.tender_end_day,
        detail.tender_end_hour,
        detail.tender_end_minute,
    )
    if any(value is None for value in fields):
        issues.append("missing or unparsable tender_end_at")
        return None

    year, month, day, hour, minute = fields
    try:
        local_dt = datetime(year, month, day, hour, minute, tzinfo=SOURCE_TIMEZONE)
    except ValueError:
        issues.append(f"invalid tender_end_at date components: {fields}")
        return None

    return local_dt.astimezone(ZoneInfo("UTC"))


def build_signal_record(stub: ListingStub, detail: DetailRecord) -> SignalRecord:
    source_id = detail.source_id or stub.source_id
    if not source_id:
        raise TransformationError("cannot build signal record without a source_id")

    source_url = detail.canonical_url or stub.detail_url
    if not source_url:
        raise TransformationError(f"cannot build signal record for {source_id} without a source_url")

    title = detail.title or stub.title
    if not title:
        raise TransformationError(f"cannot build signal record for {source_id} without a title")

    issues: list[str] = []

    size_hectares = _parse_size_hectares(detail.size_hectares_raw, issues)
    tender_end_at = _parse_tender_end_at(detail, issues)

    classification = classify_domain(detail.objektart_label, title, detail.description)
    if not classification.in_scope:
        issues.append("listing does not match agricultural, forest or peatland scope")

    geocoding = resolve_location(detail)
    if geocoding.precision == "unresolved":
        issues.append(f"location unresolved: {geocoding.reason}")

    return SignalRecord(
        source_system=SOURCE_SYSTEM,
        source_id=source_id,
        source_url=source_url,
        title=title,
        objektart_label=detail.objektart_label,
        objektart_slug=classification.objektart_slug,
        domain_tags=classification.domain_tags,
        bundesland=detail.bundesland,
        landkreis=detail.kreis,
        gemeinde=detail.gemeinde,
        gemarkung=detail.gemarkung,
        size_hectares=size_hectares,
        marketing_type=detail.marketing_type_label,
        price_raw=detail.price_raw,
        tender_end_at=tender_end_at,
        location_point=geocoding.point,
        location_precision=geocoding.precision,
        location_note=geocoding.reason,
        attachment_urls=detail.attachment_urls,
        description=detail.description,
        raw_fields={
            "listing_region_subtitle": stub.region_subtitle,
            "objektart_label": detail.objektart_label,
            "size_hectares_raw": detail.size_hectares_raw,
            "price_raw": detail.price_raw,
            "marketing_type_label": detail.marketing_type_label,
        },
        validation_issues=issues,
    )
