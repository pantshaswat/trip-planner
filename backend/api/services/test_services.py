"""Unit tests for the geocoding/routing wrappers.

HTTP is fully mocked — these tests never touch the network.
Run from backend/:
    uv run python -m unittest api.services.test_services
"""

import unittest
from unittest.mock import patch

import requests

from . import geocoding, routing
from .errors import GeocodingError, RoutingError


class FakeResponse:
    def __init__(self, *, status_code=200, json_data=None, raise_json=False):
        self.status_code = status_code
        self._json = json_data
        self._raise_json = raise_json

    def json(self):
        if self._raise_json:
            raise ValueError("not json")
        return self._json


class GeocodingTests(unittest.TestCase):
    @patch("api.services.geocoding.requests.get")
    def test_success(self, mock_get):
        mock_get.return_value = FakeResponse(
            json_data=[{"lat": "41.88", "lon": "-87.62", "display_name": "Chicago, IL"}]
        )
        place = geocoding.geocode("Chicago, IL")
        self.assertAlmostEqual(place.lat, 41.88)
        self.assertAlmostEqual(place.lon, -87.62)
        self.assertEqual(place.display_name, "Chicago, IL")
        # Nominatim requires an identifying User-Agent.
        self.assertIn("User-Agent", mock_get.call_args.kwargs["headers"])

    def test_empty_query_rejected(self):
        with self.assertRaises(GeocodingError):
            geocoding.geocode("   ")

    @patch("api.services.geocoding.requests.get")
    def test_no_results(self, mock_get):
        mock_get.return_value = FakeResponse(json_data=[])
        with self.assertRaises(GeocodingError):
            geocoding.geocode("asdfghjkl nowhere")

    @patch("api.services.geocoding.requests.get")
    def test_http_error(self, mock_get):
        mock_get.return_value = FakeResponse(status_code=503)
        with self.assertRaises(GeocodingError):
            geocoding.geocode("Chicago")

    @patch("api.services.geocoding.requests.get")
    def test_timeout_wrapped(self, mock_get):
        mock_get.side_effect = requests.Timeout("timed out")
        with self.assertRaises(GeocodingError):
            geocoding.geocode("Chicago")

    @patch("api.services.geocoding.requests.get")
    def test_bad_json(self, mock_get):
        mock_get.return_value = FakeResponse(raise_json=True)
        with self.assertRaises(GeocodingError):
            geocoding.geocode("Chicago")


class RoutingTests(unittest.TestCase):
    @patch("api.services.routing.requests.get")
    def test_success_distance_and_geometry_flip(self, mock_get):
        # 1609.344 m == exactly 1 mile. Geometry comes back as [lon, lat].
        mock_get.return_value = FakeResponse(
            json_data={
                "code": "Ok",
                "routes": [{
                    "distance": 1609.344,
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[-87.63, 41.88], [-90.20, 38.63]],
                    },
                }],
            }
        )
        leg = routing.route(routing.Coord(41.88, -87.63), routing.Coord(38.63, -90.20))
        self.assertAlmostEqual(leg.distance_miles, 1.0, places=6)
        # Flipped to [lat, lon].
        self.assertEqual(leg.geometry[0], [41.88, -87.63])
        self.assertEqual(leg.geometry[1], [38.63, -90.20])

    @patch("api.services.routing.requests.get")
    def test_url_uses_lon_lat_order(self, mock_get):
        mock_get.return_value = FakeResponse(
            json_data={"code": "Ok", "routes": [{
                "distance": 100.0,
                "geometry": {"coordinates": [[0, 0]]},
            }]}
        )
        routing.route(routing.Coord(41.88, -87.63), routing.Coord(38.63, -90.20))
        url = mock_get.call_args.args[0]
        # OSRM expects lon,lat;lon,lat.
        self.assertIn("-87.63,41.88;-90.2,38.63", url)

    @patch("api.services.routing.requests.get")
    def test_no_route(self, mock_get):
        mock_get.return_value = FakeResponse(json_data={"code": "NoRoute", "routes": []})
        with self.assertRaises(RoutingError):
            routing.route(routing.Coord(0, 0), routing.Coord(1, 1))

    @patch("api.services.routing.requests.get")
    def test_http_error(self, mock_get):
        mock_get.return_value = FakeResponse(status_code=500)
        with self.assertRaises(RoutingError):
            routing.route(routing.Coord(0, 0), routing.Coord(1, 1))

    @patch("api.services.routing.requests.get")
    def test_connection_error_wrapped(self, mock_get):
        mock_get.side_effect = requests.ConnectionError("boom")
        with self.assertRaises(RoutingError):
            routing.route(routing.Coord(0, 0), routing.Coord(1, 1))


if __name__ == "__main__":
    unittest.main()
