"""External-service wrappers: geocoding (Nominatim) and routing (OSRM).

These talk to free, no-key public APIs over HTTP. They are intentionally
Django-free (config comes from os.environ) so they can be unit-tested with
mocked HTTP responses, and reused outside the web layer if needed.
"""

from .errors import GeocodingError, RoutingError, ServiceError
from .geocoding import Place, geocode
from .routing import Coord, RouteLeg, route

__all__ = [
    "ServiceError",
    "GeocodingError",
    "RoutingError",
    "Place",
    "geocode",
    "Coord",
    "RouteLeg",
    "route",
]
