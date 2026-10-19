"""
coverage_lookup.py

Extracts and validates the optional "coverage" section from the README's
embedded yaml block, and converts it into the spatialCoverage/
temporalCoverage format expected by SDL's dataset API (pysdl
src/models.py to_dict()) - NOT the export/GeometryCollection format,
which SDL rejects when submitted ("must NOT have additional properties").

Expected structure:

    coverage:
      temporal: {start: <YYYY-MM-DD>, end: <YYYY-MM-DD>}
      spatial:
        centroid: {lat: <float>, lon: <float>}
        polygon: "POLYGON((lon lat, lon lat, ...))"   # optional
      target: <dataset file name>   # optional, default "README.md"

"temporal" and "spatial" are both optional (one, both, or neither may be
given); "coverage" itself is entirely optional - if absent, this module
contributes nothing and the generator behaves exactly as before.

Coordinate order: centroid.coordinates in the API format is [lon, lat]
(SDL's "sdlctl -ct" flag uses the opposite order, lat lon - do not confuse
the two). SDL only accepts coverage on a dataset entry, never on the
experiment or version level.
"""

import re
from datetime import date

DEFAULT_TARGET = "README.md"

WKT_POLYGON_PATTERN = re.compile(r"^POLYGON\s*\(\((.+)\)\)$", re.IGNORECASE)


def extract_coverage(data: dict) -> dict | None:
    """
    Returns the raw "coverage" section from the parsed README yaml, or
    None if no such section is present (coverage is entirely optional).
    """
    return data.get("coverage")


def get_coverage_target(coverage: dict) -> str:
    """Name of the dataset file the coverage should be attached to."""
    return coverage.get("target", DEFAULT_TARGET)


def _validate_date(value, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise ValueError(f"coverage.temporal.{field} is not a valid ISO date (YYYY-MM-DD): {value!r}")


def _build_temporal_coverage(temporal: dict) -> dict:
    if "start" not in temporal or "end" not in temporal:
        raise ValueError("coverage.temporal requires both 'start' and 'end'")
    start = _validate_date(temporal["start"], "start")
    end = _validate_date(temporal["end"], "end")
    if start > end:
        raise ValueError(f"coverage.temporal.start ({start}) is after coverage.temporal.end ({end})")
    return {"startDate": start.isoformat(), "endDate": end.isoformat()}


def _validate_lat_lon(lat: float, lon: float) -> None:
    if not (-90 <= lat <= 90):
        raise ValueError(f"coverage latitude out of range [-90, 90]: {lat}")
    if not (-180 <= lon <= 180):
        raise ValueError(f"coverage longitude out of range [-180, 180]: {lon}")


def _parse_wkt_polygon(wkt: str) -> list:
    """
    Parses a WKT "POLYGON((lon lat, lon lat, ...))" string into a list of
    [lon, lat] points, closing the ring (repeating the first point as the
    last) if the input didn't already close it itself - matches pysdl's
    helpers.polygon_to_dict().
    """
    match = WKT_POLYGON_PATTERN.match(wkt.strip())
    if not match:
        raise ValueError(f"coverage.spatial.polygon is not a valid WKT POLYGON(...): {wkt!r}")

    points = []
    for pair in match.group(1).split(","):
        parts = pair.strip().split()
        if len(parts) != 2:
            raise ValueError(f"coverage.spatial.polygon has an invalid coordinate pair: {pair!r}")
        lon, lat = float(parts[0]), float(parts[1])
        _validate_lat_lon(lat, lon)
        points.append([lon, lat])

    if len(points) < 3:
        raise ValueError("coverage.spatial.polygon needs at least 3 points")
    if points[0] != points[-1]:
        points.append(points[0])

    return points


def _build_spatial_coverage(spatial: dict) -> dict:
    if "centroid" not in spatial:
        raise ValueError("coverage.spatial is missing required 'centroid'")

    centroid = spatial["centroid"]
    lat, lon = float(centroid["lat"]), float(centroid["lon"])
    _validate_lat_lon(lat, lon)

    geometry_coordinates = []
    if "polygon" in spatial:
        geometry_coordinates = _parse_wkt_polygon(spatial["polygon"])

    return {
        "geometry": {"coordinates": geometry_coordinates},
        "centroid": {"coordinates": [lon, lat]},
    }


def build_api_coverage(coverage: dict) -> dict:
    """
    Converts the README's "coverage" section into the SDL dataset API
    format (spatialCoverage / temporalCoverage keys, present only if the
    corresponding section was given). Raises ValueError on invalid data.
    """
    result = {}
    if "temporal" in coverage:
        result["temporalCoverage"] = _build_temporal_coverage(coverage["temporal"])
    if "spatial" in coverage:
        result["spatialCoverage"] = _build_spatial_coverage(coverage["spatial"])
    return result