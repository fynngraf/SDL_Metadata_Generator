"""
coverage_lookup.py

Extracts and validates the optional "coverage" section from the README's
embedded yaml block, and converts it into the spatialCoverage/
temporalCoverage format expected by SDL's dataset API (pysdl
src/models.py to_dict()) - NOT the export/GeometryCollection format,
which SDL rejects when submitted ("must NOT have additional properties").

Two forms are supported:

1. Single shared coverage block (the default), attached to one dataset or
   to all of them:

    coverage:
      temporal: {start: <YYYY-MM-DD>, end: <YYYY-MM-DD>}
      spatial:
        centroid: {lat: <float>, lon: <float>}
        polygon: "POLYGON((lon lat, lon lat, ...))"   # optional
      target: <dataset file name> | "all"   # optional, default "all"

2. Per-dataset coverage, keyed by the exact dataset path (as it appears in
   the generated metadata, e.g. "J1/seissol_param/foo.par") - each entry
   gets its own, independent temporal/spatial coverage:

    coverage:
      "J1/seissol_param/foo.par":
        temporal: {start: ..., end: ...}
        spatial: {centroid: {lat: ..., lon: ...}}
      "J1/output/bar.h5":
        spatial: {point: [<lon>, <lat>], bbox: [<minLon>, <minLat>, <maxLon>, <maxLat>]}
      ...

   Which form is used is auto-detected: if "coverage" has "temporal",
   "spatial" or "target" as a direct key, it's form 1; otherwise every key
   is treated as a dataset path (form 2) - see is_per_dataset_coverage().
   A dataset path with no matching generated dataset logs a warning and is
   skipped, same philosophy as an unmatched "target" in form 1.

"temporal" and "spatial" are both optional on any single coverage entry
(one, both, or neither may be given); "coverage" itself is entirely
optional - if absent, this module contributes nothing and the generator
behaves exactly as before.

Spatial coordinates accept either "centroid"/"polygon" or "point"/"bbox":
"point" is [lon, lat] (same order as "centroid.coordinates" in the API
format), and "bbox" is [minLon, minLat, maxLon, maxLat], converted into a
closed 4-point rectangle for the "geometry" field. Any other extra keys
on a coverage entry (e.g. "place") are ignored - only "temporal" and
"spatial" are read.

Temporal values accept either a plain ISO date (YYYY-MM-DD) or a full ISO
datetime (e.g. "2011-03-11T05:46:24Z") - only the date part is kept,
since SDL's temporalCoverage API only takes dates.

Coordinate order: centroid.coordinates in the API format is [lon, lat]
(SDL's "sdlctl -ct" flag uses the opposite order, lat lon - do not confuse
the two). SDL only accepts coverage on a dataset entry, never on the
experiment or version level.
"""

import re
from datetime import date

DEFAULT_TARGET = "all"

WKT_POLYGON_PATTERN = re.compile(r"^POLYGON\s*\(\((.+)\)\)$", re.IGNORECASE)


def extract_coverage(data: dict) -> dict | None:
    """
    Returns the raw "coverage" section from the parsed README yaml, or
    None if no such section is present (coverage is entirely optional).
    """
    return data.get("coverage")


def get_coverage_target(coverage: dict) -> str:
    """Name of the dataset file the coverage should be attached to, or the
        literal string "all" (the default) to attach it to every generated
        dataset entry
    """
    return coverage.get("target", DEFAULT_TARGET)


def is_per_dataset_coverage(coverage: dict) -> bool:
    """
    True if "coverage" maps dataset paths to individual coverage entries
    (form 2) rather than being the single shared coverage block (form 1,
    which has "temporal", "spatial" or "target" directly as its own keys).
    """
    return not ({"temporal", "spatial", "target"} & coverage.keys())


def build_per_dataset_coverage(coverage: dict) -> dict:
    """
    Converts a per-dataset-path coverage mapping (form 2) into
    {dataset_path: api_coverage_dict}, via build_api_coverage() for each
    entry. Raises ValueError on invalid data (same as build_api_coverage).
    """
    result = {}
    for dataset_path, entry in coverage.items():
        if not isinstance(entry, dict):
            raise ValueError(
                f"coverage[{dataset_path!r}] must be a mapping with 'temporal' and/or 'spatial'"
            )
        result[dataset_path] = build_api_coverage(entry)
    return result


def _validate_date(value, field: str) -> date:
    # Accepts a plain ISO date (YYYY-MM-DD) or a full ISO datetime (e.g.
    # "2011-03-11T05:46:24Z") - only the date part is kept either way.
    text = str(value)[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise ValueError(
            f"coverage.temporal.{field} is not a valid ISO date (YYYY-MM-DD) or ISO datetime: {value!r}"
        )


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


def _bbox_to_polygon(bbox) -> list:
    """
    Converts a GeoJSON-style [minLon, minLat, maxLon, maxLat] bbox into a
    closed 4-point rectangle [[lon, lat], ...], same shape as
    _parse_wkt_polygon()'s result.
    """
    if len(bbox) != 4:
        raise ValueError(f"coverage.spatial.bbox must be [minLon, minLat, maxLon, maxLat]: {bbox!r}")
    min_lon, min_lat, max_lon, max_lat = (float(v) for v in bbox)
    _validate_lat_lon(min_lat, min_lon)
    _validate_lat_lon(max_lat, max_lon)
    if min_lon > max_lon or min_lat > max_lat:
        raise ValueError(f"coverage.spatial.bbox has min > max: {bbox!r}")
    return [
        [min_lon, min_lat],
        [max_lon, min_lat],
        [max_lon, max_lat],
        [min_lon, max_lat],
        [min_lon, min_lat],
    ]


def _build_spatial_coverage(spatial: dict) -> dict:
    # Optional geometry: "polygon: <WKT>" or "bbox: [minLon, minLat, maxLon, maxLat]"
    geometry_coordinates = []
    if "polygon" in spatial:
        geometry_coordinates = _parse_wkt_polygon(spatial["polygon"])
    elif "bbox" in spatial:
        geometry_coordinates = _bbox_to_polygon(spatial["bbox"])

    # Centroid point: "centroid: {lat, lon}" or "point: [lon, lat]"; if
    # neither is given but a "bbox" is, the centroid defaults to the
    # bbox's midpoint.
    if "centroid" in spatial:
        centroid = spatial["centroid"]
        lat, lon = float(centroid["lat"]), float(centroid["lon"])
    elif "point" in spatial:
        point = spatial["point"]
        if len(point) != 2:
            raise ValueError(f"coverage.spatial.point must be [lon, lat]: {point!r}")
        lon, lat = float(point[0]), float(point[1])
    elif "bbox" in spatial:
        # bbox ring from _bbox_to_polygon() is [minLon,minLat], [maxLon,minLat],
        # [maxLon,maxLat], [minLon,maxLat], [minLon,minLat] (closed) - use the
        # first and third point to get both corners.
        min_lon, min_lat = geometry_coordinates[0]
        max_lon, max_lat = geometry_coordinates[2]
        lon, lat = (min_lon + max_lon) / 2, (min_lat + max_lat) / 2
    else:
        raise ValueError(
            "coverage.spatial is missing required 'centroid'/'point' (or a 'bbox' to derive one from)"
        )
    _validate_lat_lon(lat, lon)

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