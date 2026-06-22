"""Geocoding via Nominatim (OpenStreetMap): location string -> coordinates.

Nominatim is free and key-less but requires a descriptive User-Agent and asks
that clients stay under ~1 request/second. We make one request per location.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import requests

from .errors import GeocodingError

# Config (env-overridable; Django-free on purpose).
NOMINATIM_URL = os.getenv(
    "NOMINATIM_URL", "https://nominatim.openstreetmap.org/search"
)
# Nominatim's usage policy requires a real, identifying User-Agent.
USER_AGENT = os.getenv("NOMINATIM_USER_AGENT", "trip-planner/1.0")
DEFAULT_TIMEOUT = float(os.getenv("HTTP_TIMEOUT_SECONDS", "10"))


@dataclass(frozen=True)
class Place:
    lat: float
    lon: float
    display_name: str  # human-readable resolved name from Nominatim


def geocode(query: str, *, timeout: float = DEFAULT_TIMEOUT) -> Place:
    """Resolve a location string to a Place. Raises GeocodingError on failure."""
    query = (query or "").strip()
    if not query:
        raise GeocodingError("Empty location string.")

    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": USER_AGENT},
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise GeocodingError(f"Geocoding request failed for '{query}': {exc}") from exc

    if resp.status_code != 200:
        raise GeocodingError(
            f"Geocoding service returned HTTP {resp.status_code} for '{query}'."
        )

    try:
        results = resp.json()
    except ValueError as exc:
        raise GeocodingError(f"Geocoding returned invalid JSON for '{query}'.") from exc

    if not results:
        raise GeocodingError(f"No location found for '{query}'.")

    top = results[0]
    try:
        return Place(
            lat=float(top["lat"]),
            lon=float(top["lon"]),
            display_name=top.get("display_name", query),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise GeocodingError(
            f"Geocoding response missing coordinates for '{query}'."
        ) from exc
