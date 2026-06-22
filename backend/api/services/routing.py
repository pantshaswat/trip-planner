"""Routing via OSRM: two coordinates -> road geometry + distance.

OSRM's public server is free and key-less. We ask for the full-overview
GeoJSON geometry and the driving distance. NOTE: we deliberately ignore OSRM's
`duration` (a car estimate) — the HOS engine derives driving time from distance
at the truck's assumed speed instead.

Coordinate convention:
    Internally and on the wire to callers we use (lat, lon).
    OSRM wants lon,lat in the URL and returns geometry as [lon, lat] pairs,
    which we flip to [lat, lon] so the frontend (Leaflet) can use them directly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import requests

from .errors import RoutingError

OSRM_URL = os.getenv("OSRM_URL", "https://router.project-osrm.org")
DEFAULT_TIMEOUT = float(os.getenv("HTTP_TIMEOUT_SECONDS", "10"))

_METERS_PER_MILE = 1609.344


@dataclass(frozen=True)
class Coord:
    lat: float
    lon: float


@dataclass
class RouteLeg:
    distance_miles: float
    geometry: list[list[float]]  # ordered [lat, lon] points along the route


def route(start: Coord, end: Coord, *, timeout: float = DEFAULT_TIMEOUT) -> RouteLeg:
    """Compute the driving route from start to end. Raises RoutingError on failure."""
    coords = f"{start.lon},{start.lat};{end.lon},{end.lat}"
    url = f"{OSRM_URL}/route/v1/driving/{coords}"

    try:
        resp = requests.get(
            url,
            params={"overview": "full", "geometries": "geojson"},
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise RoutingError(f"Routing request failed: {exc}") from exc

    if resp.status_code != 200:
        raise RoutingError(f"Routing service returned HTTP {resp.status_code}.")

    try:
        data = resp.json()
    except ValueError as exc:
        raise RoutingError("Routing returned invalid JSON.") from exc

    if data.get("code") != "Ok" or not data.get("routes"):
        raise RoutingError(
            f"No route found (OSRM code: {data.get('code', 'unknown')})."
        )

    top = data["routes"][0]
    try:
        distance_m = float(top["distance"])
        raw_geometry = top["geometry"]["coordinates"]
    except (KeyError, TypeError, ValueError) as exc:
        raise RoutingError("Routing response missing distance/geometry.") from exc

    # OSRM gives [lon, lat]; flip to [lat, lon] for the frontend.
    geometry = [[float(lat), float(lon)] for lon, lat in raw_geometry]

    return RouteLeg(
        distance_miles=distance_m / _METERS_PER_MILE,
        geometry=geometry,
    )
