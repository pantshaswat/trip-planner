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
NOMINATIM_REVERSE_URL = os.getenv(
    "NOMINATIM_REVERSE_URL", "https://nominatim.openstreetmap.org/reverse"
)
# Nominatim's usage policy requires a real, identifying User-Agent.
USER_AGENT = os.getenv("NOMINATIM_USER_AGENT", "trip-planner/1.0")
DEFAULT_TIMEOUT = float(os.getenv("HTTP_TIMEOUT_SECONDS", "10"))


@dataclass(frozen=True)
class Place:
    lat: float
    lon: float
    display_name: str           # full human-readable name from Nominatim
    short_name: str | None = None  # compact "City, ST" for log remarks


def _short_location(address: dict | None) -> str | None:
    """Build a compact "City, ST" string from a Nominatim address object."""
    if not address:
        return None
    city = (
        address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("hamlet")
        or address.get("county")
    )
    # Prefer the 2-letter state code from the ISO field (e.g. "US-IL" -> "IL").
    iso = address.get("ISO3166-2-lvl4", "")
    state = iso.split("-")[-1] if "-" in iso else address.get("state")
    parts = [p for p in (city, state) if p]
    return ", ".join(parts) if parts else None


def geocode(query: str, *, timeout: float = DEFAULT_TIMEOUT) -> Place:
    """Resolve a location string to a Place. Raises GeocodingError on failure."""
    query = (query or "").strip()
    if not query:
        raise GeocodingError("Empty location string.")

    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={"q": query, "format": "json", "limit": 1, "addressdetails": 1},
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
            short_name=_short_location(top.get("address")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise GeocodingError(
            f"Geocoding response missing coordinates for '{query}'."
        ) from exc


def reverse_geocode(lat: float, lon: float, *, timeout: float = DEFAULT_TIMEOUT) -> str | None:
    """Best-effort "City, ST" for a coordinate. Returns None on any failure.

    Used to label mid-route stops (fuel, break, rest) in log remarks. Because
    remarks are non-critical, this never raises — it just returns None.
    """
    try:
        resp = requests.get(
            NOMINATIM_REVERSE_URL,
            params={"lat": lat, "lon": lon, "format": "json",
                    "addressdetails": 1, "zoom": 10},
            headers={"User-Agent": USER_AGENT},
            timeout=timeout,
        )
        if resp.status_code != 200:
            return None
        return _short_location(resp.json().get("address"))
    except (requests.RequestException, ValueError):
        return None
