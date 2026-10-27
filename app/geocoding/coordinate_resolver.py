import math
from dataclasses import dataclass
from typing import Literal

from pyproj import Transformer
from shapely.geometry import Point

from app.parsers.bvvg_detail_parser import DetailRecord

SOURCE_CRS = "EPSG:4326"
TARGET_CRS = "EPSG:25832"

GERMANY_LATITUDE_RANGE = (47.0, 55.5)
GERMANY_LONGITUDE_RANGE = (5.5, 15.5)
GERMANY_EASTING_RANGE = (100_000.0, 900_000.0)
GERMANY_NORTHING_RANGE = (5_200_000.0, 6_100_000.0)

_transformer = Transformer.from_crs(SOURCE_CRS, TARGET_CRS, always_xy=True)

LocationPrecision = Literal["approximate", "unresolved"]


@dataclass(frozen=True)
class GeocodingResult:
    point: Point | None
    precision: LocationPrecision
    reason: str | None


def _unresolved(reason: str) -> GeocodingResult:
    return GeocodingResult(point=None, precision="unresolved", reason=reason)


def resolve_location(detail: DetailRecord) -> GeocodingResult:
    coordinate = detail.coordinate
    if coordinate is None:
        return _unresolved("source page did not expose a map coordinate")

    latitude = coordinate.latitude
    longitude = coordinate.longitude

    if not (GERMANY_LATITUDE_RANGE[0] <= latitude <= GERMANY_LATITUDE_RANGE[1]):
        return _unresolved(f"latitude {latitude} outside plausible Germany range")

    if not (GERMANY_LONGITUDE_RANGE[0] <= longitude <= GERMANY_LONGITUDE_RANGE[1]):
        return _unresolved(f"longitude {longitude} outside plausible Germany range")

    easting, northing = _transformer.transform(longitude, latitude)

    if not (math.isfinite(easting) and math.isfinite(northing)):
        return _unresolved("coordinate transform produced non finite result")

    if not (GERMANY_EASTING_RANGE[0] <= easting <= GERMANY_EASTING_RANGE[1]):
        return _unresolved(f"transformed easting {easting} outside plausible Germany range")

    if not (GERMANY_NORTHING_RANGE[0] <= northing <= GERMANY_NORTHING_RANGE[1]):
        return _unresolved(f"transformed northing {northing} outside plausible Germany range")

    return GeocodingResult(
        point=Point(easting, northing),
        precision="approximate",
        reason="source map position is explicitly marked as approximate",
    )
