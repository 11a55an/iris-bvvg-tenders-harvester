from app.geocoding.coordinate_resolver import resolve_location
from app.parsers.bvvg_detail_parser import DetailRecord, RawCoordinate


def _detail_with_coordinate(coordinate: RawCoordinate | None) -> DetailRecord:
    return DetailRecord(
        source_id="TEST-1",
        title="Test",
        canonical_url="https://www.bvvg.de/objekte/test/",
        bundesland=None,
        kreis=None,
        gemeinde=None,
        gemarkung=None,
        objektart_label=None,
        size_hectares_raw=None,
        marketing_type_label=None,
        price_raw=None,
        tender_end_day=None,
        tender_end_month=None,
        tender_end_year=None,
        tender_end_hour=None,
        tender_end_minute=None,
        description=None,
        coordinate=coordinate,
        attachment_urls=[],
    )


def test_resolve_location_transforms_valid_coordinate_to_epsg_25832():
    detail = _detail_with_coordinate(RawCoordinate(52.7368, 12.7287, is_approximate=True))

    result = resolve_location(detail)

    assert result.precision == "approximate"
    assert result.point is not None
    assert 700_000 < result.point.x < 800_000
    assert 5_800_000 < result.point.y < 5_900_000


def test_resolve_location_returns_unresolved_when_no_coordinate_present():
    detail = _detail_with_coordinate(None)

    result = resolve_location(detail)

    assert result.precision == "unresolved"
    assert result.point is None
    assert "coordinate" in result.reason


def test_resolve_location_rejects_coordinate_outside_germany():
    detail = _detail_with_coordinate(RawCoordinate(0.0, 0.0, is_approximate=True))

    result = resolve_location(detail)

    assert result.precision == "unresolved"
    assert result.point is None
    assert "outside plausible Germany range" in result.reason


def test_resolve_location_rejects_swapped_lat_lon_outside_germany():
    detail = _detail_with_coordinate(RawCoordinate(12.7287, 52.7368, is_approximate=True))

    result = resolve_location(detail)

    assert result.precision == "unresolved"
