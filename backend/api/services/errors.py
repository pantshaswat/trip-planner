"""Typed errors for the external-service wrappers.

Callers (the B3 API view) catch these to return clean 4xx/5xx responses
instead of leaking raw network exceptions.
"""


class ServiceError(Exception):
    """Base class for any geocoding/routing failure."""


class GeocodingError(ServiceError):
    """A location string could not be turned into coordinates."""


class RoutingError(ServiceError):
    """A route between two coordinates could not be computed."""
