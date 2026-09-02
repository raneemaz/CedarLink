"""Coordinate validation and great-circle distance.

Pure geo math — no store or address knowledge. ``store_service`` builds the
distance search on top of this. See
docs/decisions/0018-location-and-distance-search.md.
"""

import math

LAT_BOUNDS = (-90.0, 90.0)
LNG_BOUNDS = (-180.0, 180.0)

# Mean km per degree of latitude. One degree of LONGITUDE is
# 111.045 km × cos(latitude), not 111.045 — using the flat value for both
# makes an east–west bounding box too narrow and silently drops results.
KM_PER_DEG_LAT = 111.045

EARTH_RADIUS_KM = 6371.0088


class CoordinateError(ValueError):
    """Invalid latitude / longitude input — a route returns it as 400."""


def _coerce(value, bounds, name):
    if isinstance(value, bool):
        raise CoordinateError(f"{name} must be a number")
    try:
        num = float(value)
    except (TypeError, ValueError):
        raise CoordinateError(f"{name} must be a number")
    if not math.isfinite(num):
        raise CoordinateError(f"{name} must be a number")

    low, high = bounds
    if not low <= num <= high:
        raise CoordinateError(f"{name} must be between {low:g} and {high:g}")
    return num


def validate_coords(latitude, longitude):
    """Return ``(lat, lng)`` as floats, or ``(None, None)`` when both are
    absent. Raises :class:`CoordinateError` on a partial pair or an
    out-of-range value.
    """
    lat_given = latitude is not None
    lng_given = longitude is not None

    if lat_given != lng_given:
        raise CoordinateError(
            "latitude and longitude must be provided together"
        )
    if not lat_given:
        return None, None

    return (
        _coerce(latitude, LAT_BOUNDS, "latitude"),
        _coerce(longitude, LNG_BOUNDS, "longitude"),
    )


def haversine_km(lat1, lng1, lat2, lng2):
    """Great-circle (straight-line) distance in km between two points."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))
